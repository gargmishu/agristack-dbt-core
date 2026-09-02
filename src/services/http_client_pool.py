"""Persistent async HTTP client connection pool for live sovereign service adapters.

Why use a persistent HTTP client connection pool?
In high-throughput sovereign Direct Benefit Transfer (DBT) environments processing millions
of farmer transactions, instantiating ephemeral HTTP clients per request exhausts operating
system socket file descriptors (leaving tens of thousands of sockets in TIME_WAIT status) and
adds 50-100ms of TLS handshake latency per request. This module provides a managed singleton
httpx.AsyncClient with explicit connection pool limits and keep-alive recycling.

See: decisions/step3.6_live_service_integration.md (Section 2: Production Invariant 3)
"""

import asyncio
import atexit
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Final

from httpx import AsyncClient, Limits

logger = logging.getLogger(__name__)

_DEFAULT_MAX_CONNECTIONS: Final[int] = 100
_DEFAULT_MAX_KEEPALIVE_CONNECTIONS: Final[int] = 20
_DEFAULT_KEEPALIVE_EXPIRY_SECONDS: Final[float] = 30.0


class HttpClientPool:
    """Namespace holder for the process-wide persistent HTTP connection pool singleton."""

    _instance: AsyncClient | None = None


def get_shared_http_client() -> AsyncClient:
    """Returns the process-wide shared persistent HTTP client singleton.

    Returns:
        Persistent AsyncClient instance with configured connection pooling.
    """
    if HttpClientPool._instance is None or HttpClientPool._instance.is_closed:
        limits = Limits(
            max_connections=_DEFAULT_MAX_CONNECTIONS,
            max_keepalive_connections=_DEFAULT_MAX_KEEPALIVE_CONNECTIONS,
            keepalive_expiry=_DEFAULT_KEEPALIVE_EXPIRY_SECONDS,
        )
        HttpClientPool._instance = AsyncClient(limits=limits)
    return HttpClientPool._instance


async def close_shared_http_client() -> None:
    """Closes the shared HTTP client pool and releases underlying network sockets.

    Intended for graceful application shutdown hooks and test teardown fixtures.
    """
    if HttpClientPool._instance is not None:
        client = HttpClientPool._instance
        HttpClientPool._instance = None
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
    if HttpClientPool._instance is not None:
        client = HttpClientPool._instance
        HttpClientPool._instance = None
        if not client.is_closed:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                try:
                    loop = asyncio.get_event_loop_policy().get_event_loop()
                except Exception:
                    loop = None

            if loop is not None and not loop.is_closed():
                try:
                    if loop.is_running():
                        loop.create_task(client.aclose())
                    else:
                        loop.run_until_complete(client.aclose())
                except Exception as err:
                    logger.debug("Process exit socket cleanup encountered error: %s", err)


atexit.register(_sync_close_client)
