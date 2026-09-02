"""Unit tests for the persistent shared HTTP client connection pool."""

import pytest

from src.services.http_client_pool import (
    close_shared_http_client,
    get_shared_http_client,
    http_client_lifespan,
)


@pytest.mark.asyncio
async def test_shared_http_client_singleton_and_lifecycle() -> None:
    client1 = get_shared_http_client()
    client2 = get_shared_http_client()

    assert client1 is client2
    assert not client1.is_closed

    await close_shared_http_client()
    assert client1.is_closed

    client3 = get_shared_http_client()
    assert client3 is not client1
    assert not client3.is_closed
    await close_shared_http_client()


@pytest.mark.asyncio
async def test_http_client_lifespan_context_manager() -> None:
    async with http_client_lifespan() as client:
        assert not client.is_closed
        assert client is get_shared_http_client()

    assert client.is_closed

