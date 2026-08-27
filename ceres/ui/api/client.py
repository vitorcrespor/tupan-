from __future__ import annotations

import json
import mimetypes
from pathlib import Path
from uuid import uuid4
from functools import lru_cache
from typing import Any, Mapping, TypeVar
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen

from ui.api.config import ApiConfig
from ui.api.errors import ApiError


ResponseT = TypeVar("ResponseT")


class ApiClient:
    """The only frontend HTTP primitive; feature modules only name paths and DTOs."""

    def __init__(self, config: ApiConfig) -> None:
        self._base_url = f"{config.base_url}/"
        self._timeout_seconds = config.timeout_seconds

    def get(self, path: str, *, query: Mapping[str, Any] | None = None, timeout_seconds: float | None = None) -> Any:
        return self.request("GET", path, query=query, timeout_seconds=timeout_seconds)

    def post(self, path: str, *, body: Mapping[str, Any] | None = None, timeout_seconds: float | None = None) -> Any:
        return self.request("POST", path, body=body, timeout_seconds=timeout_seconds)

    def patch(self, path: str, *, body: Mapping[str, Any] | None = None, timeout_seconds: float | None = None) -> Any:
        return self.request("PATCH", path, body=body, timeout_seconds=timeout_seconds)

    def delete(self, path: str, *, body: Mapping[str, Any] | None = None, timeout_seconds: float | None = None) -> Any:
        return self.request("DELETE", path, body=body, timeout_seconds=timeout_seconds)

    def post_file(
        self,
        path: str,
        *,
        file_path: str | Path,
        field_name: str = "file",
        query: Mapping[str, Any] | None = None,
        timeout_seconds: float | None = None,
    ) -> Any:
        """Upload a file through the same centralized client for multipart API endpoints."""
        file = Path(file_path)
        boundary = uuid4().hex
        mime_type = mimetypes.guess_type(file.name)[0] or "application/octet-stream"
        body = b"".join(
            (
                f"--{boundary}\r\n".encode(),
                f'Content-Disposition: form-data; name="{field_name}"; filename="{file.name}"\r\n'.encode(),
                f"Content-Type: {mime_type}\r\n\r\n".encode(),
                file.read_bytes(),
                f"\r\n--{boundary}--\r\n".encode(),
            )
        )
        request = Request(
            self._url(path, query),
            data=body,
            method="POST",
            headers={"Accept": "application/json", "Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        return self._execute(request, timeout_seconds=timeout_seconds)

    def request(
        self,
        method: str,
        path: str,
        *,
        query: Mapping[str, Any] | None = None,
        body: Mapping[str, Any] | None = None,
        timeout_seconds: float | None = None,
    ) -> Any:
        url = self._url(path, query)
        body_bytes = json.dumps(body, ensure_ascii=False, default=self._json_default).encode("utf-8") if body is not None else None
        request = Request(
            url,
            data=body_bytes,
            method=method.upper(),
            headers={"Accept": "application/json", **({"Content-Type": "application/json"} if body_bytes else {})},
        )
        return self._execute(request, timeout_seconds=timeout_seconds)

    def _execute(self, request: Request, *, timeout_seconds: float | None) -> Any:
        try:
            with urlopen(request, timeout=timeout_seconds or self._timeout_seconds) as response:
                raw_body = response.read()
                if not raw_body:
                    return None
                return self._decode_json(raw_body, status_code=response.status)
        except HTTPError as exc:
            payload = self._decode_error_payload(exc)
            raise ApiError(
                message=str(payload.get("message") or exc.reason or "The API rejected the request."),
                code=str(payload.get("code") or "http_error"),
                status_code=exc.code,
                details=payload.get("details") if isinstance(payload.get("details"), dict) else None,
                request_id=payload.get("request_id"),
            ) from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise ApiError("The API could not be reached.", code="network_error", details={"reason": str(exc)}) from exc

    def _url(self, path: str, query: Mapping[str, Any] | None) -> str:
        if path.startswith(("http://", "https://")):
            raise ValueError("API paths must be relative to the configured base URL.")
        normalized_path = path.lstrip("/")
        url = urljoin(self._base_url, normalized_path)
        if query:
            values = {key: value for key, value in query.items() if value is not None}
            if values:
                url = f"{url}?{urlencode(values, doseq=True)}"
        return url

    @staticmethod
    def _decode_json(raw_body: bytes, *, status_code: int) -> Any:
        try:
            return json.loads(raw_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ApiError(
                "The API returned an invalid JSON response.",
                code="invalid_response",
                status_code=status_code,
            ) from exc

    @staticmethod
    def _decode_error_payload(error: HTTPError) -> dict[str, Any]:
        try:
            decoded = json.loads(error.read().decode("utf-8"))
            return decoded if isinstance(decoded, dict) else {}
        except (UnicodeDecodeError, json.JSONDecodeError):
            return {}

    @staticmethod
    def _json_default(value: Any) -> Any:
        if hasattr(value, "isoformat"):
            return value.isoformat()
        if hasattr(value, "value"):
            return value.value
        if hasattr(value, "model_dump"):
            return value.model_dump(mode="json", exclude_none=True)
        raise TypeError(f"{type(value).__name__} is not JSON serializable")


@lru_cache
def get_api_client() -> ApiClient:
    return ApiClient(ApiConfig.from_environment())
