"""Persistent async HTTP client connection pool for live sovereign service adapters.

Why use a persistent HTTP client connection pool?
In high-throughput sovereign Direct Benefit Transfer (DBT) environments processing millions
of farmer transactions, instantiating ephemeral HTTP clients per request exhausts operating
system socket file descriptors (leaving tens of thousands of sockets in TIME_WAIT status) and
adds 50-100ms of TLS handshake latency per request. This module provides a managed singleton
httpx.AsyncClient with explicit connection pool limits and keep-alive recycling.

See: decisions/step3.6_live_service_integration.md (Section 2: Production Invariant 3)
"""

from typing import Final

import httpx

_DEFAULT_MAX_CONNECTIONS: Final[int] = 100
_DEFAULT_MAX_KEEPALIVE_CONNECTIONS: Final[int] = 20
_DEFAULT_KEEPALIVE_EXPIRY_SECONDS: Final[float] = 30.0


class HttpClientPool:
    """Manages process-wide persistent HTTP connection pool singleton."""

    _instance: httpx.AsyncClient | None = None

    @classmethod
    def get_client(cls) -> httpx.AsyncClient:
        """Returns the process-wide shared persistent HTTP client singleton."""
        if cls._instance is None or cls._instance.is_closed:
            limits = httpx.Limits(
                max_connections=_DEFAULT_MAX_CONNECTIONS,
                max_keepalive_connections=_DEFAULT_MAX_KEEPALIVE_CONNECTIONS,
                keepalive_expiry=_DEFAULT_KEEPALIVE_EXPIRY_SECONDS,
            )
            cls._instance = httpx.AsyncClient(limits=limits)
        return cls._instance

    @classmethod
    async def close_client(cls) -> None:
        """Closes the persistent HTTP client pool and releases network sockets."""
        if cls._instance is not None and not cls._instance.is_closed:
            await cls._instance.aclose()
            cls._instance = None


def get_shared_http_client() -> httpx.AsyncClient:
    """Returns the process-wide shared persistent HTTP client singleton.

    Returns:
        Persistent httpx.AsyncClient instance.
    """
    return HttpClientPool.get_client()


async def close_shared_http_client() -> None:
    """Closes the shared HTTP client pool and releases underlying network sockets.

    Intended for graceful application shutdown hooks and test teardown fixtures.
    """
    await HttpClientPool.close_client()
