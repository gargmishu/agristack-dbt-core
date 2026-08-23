"""Shared Pytest configuration and fixtures for Step 1.2 test suite."""

import asyncio
import os
from collections.abc import Generator

import pytest


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
