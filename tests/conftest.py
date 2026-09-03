"""Shared Pytest configuration and fixtures for Step 1.2 test suite."""

import asyncio
import os
from collections.abc import Generator

import pytest

from src.services.http_transport import (
    close_shared_http_client,
    is_shared_http_client_initialized,
)


@pytest.fixture(autouse=True, scope="session")
def setup_test_environment() -> None:
    """Configures default environment variables for test execution."""
    os.environ.setdefault("AGRISTACK_PEPPER_SECRET", "test_default_conftest_pepper_key")
    os.environ.setdefault("RATE_LIMIT_PER_MINUTE", "60")
    os.environ.setdefault("RATE_LIMIT_CAPACITY", "10")


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
def auto_cleanup_shared_http_client(
    event_loop: asyncio.AbstractEventLoop,
) -> Generator[None, None, None]:
    """Automatically cleans up the shared HTTP client pool after each test."""
    yield
    if is_shared_http_client_initialized():
        event_loop.run_until_complete(close_shared_http_client())


