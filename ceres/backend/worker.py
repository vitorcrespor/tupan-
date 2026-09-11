"""Run the minimal Tupan PostgreSQL background worker.

Usage:
    python -m backend.worker
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Awaitable, Callable

from backend.observability import configure_logging, job_id_context, log_event
from backend.repositories.job_queue import ClaimedJob, JobQueueRepository, JobResult
from backend.repositories.tenant_data import TenantContext
from backend.services.errors import DomainValidationError, ServiceError


logger = logging.getLogger(__name__)


class UnsupportedJobTypeError(RuntimeError):
    pass


@dataclass(frozen=True)
class WorkerSettings:
    concurrency: int = 2
    poll_seconds: float = 1.0
    stale_after_seconds: int = 900

    @classmethod
    def from_environment(cls) -> "WorkerSettings":
        return cls(
            concurrency=_bounded_int("WORKER_CONCURRENCY", 2, minimum=1, maximum=8),
            poll_seconds=_bounded_float("WORKER_POLL_SECONDS", 1.0, minimum=0.1, maximum=30.0),
            stale_after_seconds=_bounded_int("WORKER_STALE_AFTER_SECONDS", 900, minimum=60, maximum=86_400),
        )


class BackgroundWorker:
    """Single process, bounded concurrency, PostgreSQL `SKIP LOCKED` claims."""

    def __init__(self, queue: JobQueueRepository, *, settings: WorkerSettings | None = None) -> None:
        self._queue = queue
        self._settings = settings or WorkerSettings.from_environment()
        self._stop = asyncio.Event()
        self._handlers: dict[str, Callable[[JobQueueRepository, TenantContext, ClaimedJob], Awaitable[JobResult]]] = {}

    async def run(self) -> None:
        await self._queue.start(max_connections=self._settings.concurrency + 1)
        recovered = await self._queue.requeue_stale_running(stale_after_seconds=self._settings.stale_after_seconds)
        if recovered:
            log_event(logger, "worker_stale_jobs_recovered", level=logging.WARNING, operation="worker.recovery", recovered_count=recovered)
        in_flight: set[asyncio.Task[None]] = set()
        try:
            while not self._stop.is_set():
                while len(in_flight) < self._settings.concurrency and not self._stop.is_set():
                    job = await self._queue.claim_next()
                    if job is None:
                        break
                    queue_latency_ms = _queue_latency_ms(job)
                    log_event(logger, "job_claimed", operation=f"job.{job.job_type}", job_id=job.job_id, queue_latency_ms=queue_latency_ms, attempt=job.attempt_count)
                    task = asyncio.create_task(self._execute(job), name=f"job:{job.job_id}")
                    in_flight.add(task)
                    task.add_done_callback(in_flight.discard)
                if in_flight:
                    await asyncio.wait(in_flight, timeout=self._settings.poll_seconds, return_when=asyncio.FIRST_COMPLETED)
                else:
                    try:
                        await asyncio.wait_for(self._stop.wait(), timeout=self._settings.poll_seconds)
                    except TimeoutError:
                        pass
        finally:
            # Stop claiming immediately, then allow currently executing durable
            # operations to record state. A forced stop is recovered at startup.
            if in_flight:
                await asyncio.gather(*in_flight, return_exceptions=True)
            await self._queue.close()
            log_event(logger, "worker_stopped", operation="worker.shutdown", status="success")

    def stop(self) -> None:
        self._stop.set()

    async def _execute(self, job: ClaimedJob) -> None:
        token = job_id_context.set(job.job_id)
        started = time.perf_counter()
        context = TenantContext(
            organization_id=job.organization_id,
            user_id=job.user_id or "background-worker",
            role="background-worker",
        )
        handler = self._handlers.get(job.job_type)
        try:
            if handler is None:
                await self._queue.retry_or_fail(
                    context,
                    job,
                    error={"code": "unsupported_job_type", "message": f"No worker handles {job.job_type!r}."},
                    retryable=False,
                )
                log_event(logger, "job_completed", level=logging.ERROR, operation=f"job.{job.job_type}", status="failed", execution_ms=round((time.perf_counter() - started) * 1_000, 2), retryable=False, error_code="unsupported_job_type")
                return
            try:
                result = await handler(self._queue, context, job)
            except asyncio.CancelledError:
                # Leave RUNNING intact. Startup recovery applies bounded retries.
                raise
            except Exception as exc:
                retryable = _is_retryable(exc)
                error = {
                    "code": exc.code if isinstance(exc, ServiceError) else "job_execution_failed",
                    "message": str(exc) or type(exc).__name__,
                    "error_type": type(exc).__name__,
                    "attempt": job.attempt_count,
                }
                await self._queue.retry_or_fail(context, job, error=error, retryable=retryable)
                log_event(logger, "job_completed", level=logging.ERROR, operation=f"job.{job.job_type}", status="retrying" if retryable and job.attempt_count < job.max_attempts else "failed", execution_ms=round((time.perf_counter() - started) * 1_000, 2), retryable=retryable, attempt=job.attempt_count, error_code=error["code"], error_type=type(exc).__name__)
                return
            await self._queue.mark_succeeded(context, job, result)
            log_event(logger, "job_completed", operation=f"job.{job.job_type}", status="succeeded", execution_ms=round((time.perf_counter() - started) * 1_000, 2), attempt=job.attempt_count)
        finally:
            job_id_context.reset(token)


def _queue_latency_ms(job: ClaimedJob) -> float | None:
    if job.created_at is None:
        return None
    created_at = job.created_at if job.created_at.tzinfo else job.created_at.replace(tzinfo=timezone.utc)
    return max(0.0, (datetime.now(timezone.utc) - created_at).total_seconds() * 1_000)


def _is_retryable(exc: Exception) -> bool:
    if isinstance(exc, DomainValidationError):
        return False
    if isinstance(exc, (ValueError, TypeError, UnsupportedJobTypeError)):
        return False
    return True


def _bounded_int(name: str, default: int, *, minimum: int, maximum: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError:
        return default
    return min(maximum, max(minimum, value))


def _bounded_float(name: str, default: float, *, minimum: float, maximum: float) -> float:
    try:
        value = float(os.getenv(name, str(default)))
    except ValueError:
        return default
    return min(maximum, max(minimum, value))


async def _main() -> None:
    configure_logging(level=os.getenv("WORKER_LOG_LEVEL", os.getenv("LOG_LEVEL", "INFO")))
    worker = BackgroundWorker(JobQueueRepository())
    loop = asyncio.get_running_loop()
    for signum in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(signum, worker.stop)
        except NotImplementedError:
            # Windows event loops do not expose add_signal_handler.
            pass
    await worker.run()


if __name__ == "__main__":
    asyncio.run(_main())