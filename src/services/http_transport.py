"""Persistent async HTTP client connection pool and standardized request transport.

Why use a persistent HTTP client connection pool?
In high-throughput sovereign Direct Benefit Transfer (DBT) environments processing millions
of farmer transactions, instantiating ephemeral HTTP clients per request exhausts operating
system socket file descriptors (leaving tens of thousands of sockets in TIME_WAIT status) and
adds 50-100ms of TLS handshake latency per request. This module provides a managed singleton
AsyncClient with explicit connection pool limits and keep-alive recycling.

Additionally, this module provides standardized, resilient HTTP JSON transport logic
(ServiceHttpTransport) that handles timeouts, Bearer authentication, HTTP status-code triage,
and domain exception mapping across all sovereign DPI and AI service adapters.

See: decisions/step3.6_live_service_integration.md (Section 2: Production Invariant 3)
"""

import asyncio
import atexit
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from http import HTTPStatus
from typing import Any, Final

from httpx import AsyncClient, Limits

from src.errors.service_errors import (
    ServiceAuthenticationError,
    ServiceConfigurationError,
    ServiceRequestPayloadError,
    ServiceResponsePayloadError,
    ServiceUnavailableError,
)

logger = logging.getLogger(__name__)

__all__ = [
    "ServiceHttpTransport",
    "ServiceTransportConfig",
    "close_shared_http_client",
    "get_shared_http_client",
    "http_client_lifespan",
    "is_shared_http_client_initialized",
]

_DEFAULT_MAX_CONNECTIONS: Final[int] = 100
_DEFAULT_MAX_KEEPALIVE_CONNECTIONS: Final[int] = 20
_DEFAULT_KEEPALIVE_EXPIRY_SECONDS: Final[float] = 30.0

_CLIENT_ERROR_STATUSES: Final[tuple[HTTPStatus, ...]] = (
    HTTPStatus.BAD_REQUEST,
    HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
    HTTPStatus.UNPROCESSABLE_ENTITY,
)


@dataclass
class _ClientPoolState:
    client: AsyncClient | None = None


_pool_state = _ClientPoolState()


def is_shared_http_client_initialized() -> bool:
    """Returns True if the shared persistent HTTP client singleton is currently allocated."""
    return _pool_state.client is not None and not _pool_state.client.is_closed


def get_shared_http_client() -> AsyncClient:
    """Returns the process-wide shared persistent HTTP client singleton.

    Returns:
        Persistent AsyncClient instance with configured connection pooling.
    """
    if _pool_state.client is None or _pool_state.client.is_closed:
        limits = Limits(
            max_connections=_DEFAULT_MAX_CONNECTIONS,
            max_keepalive_connections=_DEFAULT_MAX_KEEPALIVE_CONNECTIONS,
            keepalive_expiry=_DEFAULT_KEEPALIVE_EXPIRY_SECONDS,
        )
        _pool_state.client = AsyncClient(limits=limits)
    return _pool_state.client


async def close_shared_http_client() -> None:
    """Closes the shared HTTP client pool and releases underlying network sockets.

    Intended for graceful application shutdown hooks and test teardown fixtures.
    """
    if _pool_state.client is not None:
        client = _pool_state.client
        _pool_state.client = None
        if not client.is_closed:
            await client.aclose()


@asynccontextmanager
async def http_client_lifespan() -> AsyncIterator[AsyncClient]:
    """Async context manager managing the lifecycle of the shared HTTP client pool.

    Yields:
        The shared persistent AsyncClient instance.

    Guarantees that underlying TCP sockets and keep-alive connections are
    gracefully closed upon context exit. Can be used directly or integrated
    into ASGI framework lifespan hooks (e.g., FastAPI, Starlette).
    """
    client = get_shared_http_client()
    try:
        yield client
    finally:
        await close_shared_http_client()


def _sync_close_client() -> None:
    """Best-effort process exit cleanup for unclosed HTTP client instances."""
    if _pool_state.client is not None:
        client = _pool_state.client
        _pool_state.client = None
        if not client.is_closed:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(client.aclose())
                else:
                    loop.run_until_complete(client.aclose())
            except Exception as error:
                logger.debug("Failed to gracefully close HTTP client at process exit: %s", error)


atexit.register(_sync_close_client)


@dataclass(frozen=True, slots=True)
class ServiceTransportConfig:
    """Configuration descriptor for service HTTP transport client.

    Attributes:
        service_name: Internal identifier for RFC 7807 problem details (e.g. 'agristack').
        service_title: Human-readable service name for error logs and diagnostics.
        timeout_seconds: Network read/connect timeout in seconds.
    """

    service_name: str
    service_title: str
    timeout_seconds: float

    def __post_init__(self) -> None:
        if not self.service_name or not self.service_name.strip():
            raise ServiceConfigurationError(
                "Service name identifier is required.",
                service_name="transport",
            )
        if not self.service_title or not self.service_title.strip():
            raise ServiceConfigurationError(
                "Service title is required.",
                service_name=self.service_name,
            )
        if self.timeout_seconds <= 0.0:
            raise ServiceConfigurationError(
                f"Timeout for {self.service_title} must be positive, got {self.timeout_seconds}s.",
                service_name=self.service_name,
            )


class ServiceHttpTransport:
    """Encapsulates authenticated HTTP transport and resilient JSON dispatch for a service."""

    def __init__(
        self,
        http_client: AsyncClient,
        api_key: str,
        config: ServiceTransportConfig,
        base_url: str,
    ) -> None:
        if not base_url or not base_url.strip():
            raise ServiceConfigurationError(
                f"Live {config.service_title} endpoint URL is required.",
                service_name=config.service_name,
            )
        clean_url = base_url.strip().rstrip("/")
        if not clean_url.startswith(("http://", "https://")):
            raise ServiceConfigurationError(
                f"Live {config.service_title} endpoint URL '{clean_url}' "
                "must start with 'http://' or 'https://'.",
                service_name=config.service_name,
            )
        if not api_key or not api_key.strip():
            raise ServiceConfigurationError(
                f"Live {config.service_title} API key is required.",
                service_name=config.service_name,
            )
        self._http_client = http_client
        self._api_key = api_key.strip()
        self._config = config
        self._base_url = clean_url

    @property
    def base_url(self) -> str:
        """Returns the configured base endpoint URL."""
        return self._base_url

    def resolve_url(self, path: str) -> str:
        """Resolves target endpoint URL from a relative path or absolute URL."""
        clean_path = path.strip()
        if not clean_path:
            raise ServiceConfigurationError(
                f"Endpoint path for {self._config.service_title} cannot be empty.",
                service_name=self._config.service_name,
            )
        if clean_path.startswith(("http://", "https://")):
            return clean_path
        if "://" in clean_path:
            raise ServiceConfigurationError(
                f"Live {self._config.service_title} endpoint path '{clean_path}' "
                "must start with 'http://' or 'https://'.",
                service_name=self._config.service_name,
            )
        return f"{self._base_url}/{clean_path.lstrip('/')}"

    async def post_json(
        self,
        path: str,
        payload: dict[str, Any],
        context_label: str = "",
    ) -> dict[str, Any]:
        """Executes resilient async POST request with timeout, authentication, and error typing.

        Args:
            path: Relative endpoint path (appended to base_url) or fully qualified URL.
            payload: JSON-serializable request dictionary.
            context_label: Contextual identifier for diagnostics logging (e.g. record ID or token).

        Returns:
            Decoded JSON dictionary from the upstream service.

        Raises:
            ServiceAuthenticationError: If the service returns 401 Unauthorized or 403 Forbidden.
            ServiceRequestPayloadError: If the service returns 400, 415, or 422 client error.
            ServiceResponsePayloadError: If the upstream response is not a valid JSON dictionary.
            ServiceUnavailableError: If the service fails, times out, or returns a 5xx error.
            ServiceConfigurationError: If path or transport configuration is invalid.
        """
        url = self.resolve_url(path)
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._api_key}",
        }

        try:
            response = await self._http_client.post(
                url, json=payload, headers=headers, timeout=self._config.timeout_seconds
            )
            if response.status_code in (
                HTTPStatus.OK,
                HTTPStatus.CREATED,
                HTTPStatus.ACCEPTED,
            ):
                try:
                    result = response.json()
                    if isinstance(result, dict):
                        return result
                except Exception as error:
                    raise ServiceResponsePayloadError(
                        f"Live {self._config.service_title} response from {url} "
                        f"violated schema: {error}",
                        service_name=self._config.service_name,
                    ) from error
                raise ServiceResponsePayloadError(
                    f"Live {self._config.service_title} response from {url} "
                    "returned non-dictionary JSON.",
                    service_name=self._config.service_name,
                )

            if response.status_code in (HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN):
                raise ServiceAuthenticationError(
                    f"{self._config.service_title} authentication failed "
                    f"with status={response.status_code}",
                    service_name=self._config.service_name,
                    status_code=response.status_code,
                )

            if response.status_code in _CLIENT_ERROR_STATUSES:
                raise ServiceRequestPayloadError(
                    f"{self._config.service_title} rejected payload with "
                    f"status={response.status_code}: {response.text}",
                    service_name=self._config.service_name,
                    status_code=response.status_code,
                )

            raise ServiceUnavailableError(
                f"Live {self._config.service_title} call to {url} failed with "
                f"status={response.status_code}: {response.text}",
                service_name=self._config.service_name,
                status_code=response.status_code,
            )

        except (
            ServiceAuthenticationError,
            ServiceConfigurationError,
            ServiceRequestPayloadError,
            ServiceResponsePayloadError,
            ServiceUnavailableError,
        ):
            raise
        except Exception as error:
            logger.warning(
                "Live %s call failed for %s: %s",
                self._config.service_name,
                context_label,
                error,
            )
            raise ServiceUnavailableError(
                f"Live {self._config.service_title} call failed for '{context_label}': {error}",
                service_name=self._config.service_name,
            ) from error
