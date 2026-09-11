"""Tenant-scoped AI interpretation services.

The package deliberately exposes no database connections, filesystem handles,
or provider credentials to callers.  Deterministic application services build
the evidence; the LLM can only interpret the bounded evidence supplied here.
"""

from backend.services.ai.orchestrator import AiOrchestrator, AiOrchestrationSettings

__all__ = ["AiOrchestrator", "AiOrchestrationSettings"]
