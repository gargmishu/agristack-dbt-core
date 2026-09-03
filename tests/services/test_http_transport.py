"""Unit tests for the persistent shared HTTP client connection pool and transport."""

import httpx
import pytest

from src.errors.service_errors import (
    ServiceAuthenticationError,
    ServiceConfigurationError,
    ServiceRequestPayloadError,
    ServiceResponsePayloadError,
    ServiceUnavailableError,
)
from src.services.http_transport import (
    ServiceHttpTransport,
    ServiceTransportConfig,
    close_shared_http_client,
    get_shared_http_client,
    http_client_lifespan,
    is_shared_http_client_initialized,
)


@pytest.mark.asyncio
async def test_shared_http_client_singleton_and_lifecycle() -> None:
    await close_shared_http_client()
    assert not is_shared_http_client_initialized()

    client1 = get_shared_http_client()
    client2 = get_shared_http_client()

    assert client1 is client2
    assert not client1.is_closed
    assert is_shared_http_client_initialized()

    await close_shared_http_client()
    assert client1.is_closed
    assert not is_shared_http_client_initialized()

    client3 = get_shared_http_client()
    assert client3 is not client1
    assert not client3.is_closed
    assert is_shared_http_client_initialized()
    await close_shared_http_client()


@pytest.mark.asyncio
async def test_http_client_lifespan_context_manager() -> None:
    async with http_client_lifespan() as client:
        assert not client.is_closed
        assert client is get_shared_http_client()

    assert client.is_closed


@pytest.mark.asyncio
async def test_service_http_transport_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("Authorization") == "Bearer secret_token"
        assert request.headers.get("Content-Type") == "application/json"
        return httpx.Response(200, json={"status": "verified"})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    transport = ServiceHttpTransport(
        http_client=client,
        api_key="secret_token",
        config=ServiceTransportConfig(
            service_name="test_svc",
            service_title="Test Service",
            timeout_seconds=2.0,
        ),
        base_url="https://api.example.com",
    )
    result = await transport.post_json(
        path="https://api.example.com/verify",
        payload={"id": "123"},
    )
    assert result == {"status": "verified"}


@pytest.mark.asyncio
async def test_service_http_transport_relative_path_resolution() -> None:
    recorded_urls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        recorded_urls.append(str(request.url))
        return httpx.Response(200, json={"status": "ok"})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    transport = ServiceHttpTransport(
        http_client=client,
        api_key="secret_token",
        config=ServiceTransportConfig(
            service_name="test_svc",
            service_title="Test Service",
            timeout_seconds=2.0,
        ),
        base_url="https://api.example.com/base/",
    )
    assert transport.base_url == "https://api.example.com/base"

    # Leading slash in relative path
    await transport.post_json(
        path="/v1/action",
        payload={"foo": "bar"},
    )
    assert recorded_urls[-1] == "https://api.example.com/base/v1/action"

    # No leading slash in relative path
    await transport.post_json(
        path="v1/action",
        payload={"foo": "bar"},
    )
    assert recorded_urls[-1] == "https://api.example.com/base/v1/action"

    # Full absolute URL ignores base_url
    await transport.post_json(
        path="https://override.example.com/v2/action",
        payload={"foo": "bar"},
    )
    assert recorded_urls[-1] == "https://override.example.com/v2/action"


def test_service_http_transport_missing_base_url_error() -> None:
    client = httpx.AsyncClient()
    with pytest.raises(ServiceConfigurationError, match="endpoint URL is required"):
        ServiceHttpTransport(
            http_client=client,
            api_key="secret_token",
            config=ServiceTransportConfig(
                service_name="test_svc",
                service_title="Test Service",
                timeout_seconds=2.0,
            ),
            base_url="",
        )


def test_service_http_transport_missing_api_key_error() -> None:
    client = httpx.AsyncClient()
    with pytest.raises(ServiceConfigurationError, match="API key is required"):
        ServiceHttpTransport(
            http_client=client,
            api_key="",
            config=ServiceTransportConfig(
                service_name="test_svc",
                service_title="Test Service",
                timeout_seconds=2.0,
            ),
            base_url="https://api.test.gov.in",
        )


def test_service_http_transport_empty_path_error() -> None:
    client = httpx.AsyncClient()
    transport = ServiceHttpTransport(
        http_client=client,
        api_key="secret_token",
        config=ServiceTransportConfig(
            service_name="test_svc",
            service_title="Test Service",
            timeout_seconds=2.0,
        ),
        base_url="https://api.test.gov.in",
    )
    with pytest.raises(ServiceConfigurationError, match="path for Test Service cannot be empty"):
        transport.resolve_url("   ")


def test_service_http_transport_invalid_path_scheme_error() -> None:
    client = httpx.AsyncClient()
    transport = ServiceHttpTransport(
        http_client=client,
        api_key="secret_token",
        config=ServiceTransportConfig(
            service_name="test_svc",
            service_title="Test Service",
            timeout_seconds=2.0,
        ),
        base_url="https://api.test.gov.in",
    )
    with pytest.raises(ServiceConfigurationError, match="must start with 'http://' or 'https://'"):
        transport.resolve_url("ftp://malicious.endpoint.gov.in/action")


def test_service_http_transport_invalid_base_url_scheme() -> None:
    client = httpx.AsyncClient()
    with pytest.raises(ServiceConfigurationError, match="must start with 'http://' or 'https://'"):
        ServiceHttpTransport(
            http_client=client,
            api_key="secret_token",
            config=ServiceTransportConfig(
                service_name="test_svc",
                service_title="Test Service",
                timeout_seconds=2.0,
            ),
            base_url="invalid.endpoint.gov.in",
        )


@pytest.mark.asyncio
async def test_service_http_transport_auth_failure() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, text="Unauthorized")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    transport = ServiceHttpTransport(
        http_client=client,
        api_key="bad_token",
        config=ServiceTransportConfig(
            service_name="test_svc",
            service_title="Test Service",
            timeout_seconds=2.0,
        ),
        base_url="https://api.example.com",
    )
    with pytest.raises(ServiceAuthenticationError, match="Test Service authentication failed"):
        await transport.post_json(
            path="https://api.example.com/verify",
            payload={"id": "123"},
        )


@pytest.mark.asyncio
async def test_service_http_transport_client_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(422, text="Invalid payload syntax")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    transport = ServiceHttpTransport(
        http_client=client,
        api_key="secret_token",
        config=ServiceTransportConfig(
            service_name="test_svc",
            service_title="Test Service",
            timeout_seconds=2.0,
        ),
        base_url="https://api.example.com",
    )
    with pytest.raises(ServiceRequestPayloadError, match="Invalid payload syntax"):
        await transport.post_json(
            path="https://api.example.com/verify",
            payload={"id": "123"},
        )


@pytest.mark.asyncio
async def test_service_http_transport_server_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="Internal Gateway Error")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    transport = ServiceHttpTransport(
        http_client=client,
        api_key="secret_token",
        config=ServiceTransportConfig(
            service_name="test_svc",
            service_title="Test Service",
            timeout_seconds=2.0,
        ),
        base_url="https://api.example.com",
    )
    with pytest.raises(ServiceUnavailableError, match="status=500"):
        await transport.post_json(
            path="https://api.example.com/verify",
            payload={"id": "123"},
        )


@pytest.mark.asyncio
async def test_service_http_transport_network_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Connection refused")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    transport = ServiceHttpTransport(
        http_client=client,
        api_key="secret_token",
        config=ServiceTransportConfig(
            service_name="test_svc",
            service_title="Test Service",
            timeout_seconds=2.0,
        ),
        base_url="https://api.example.com",
    )
    with pytest.raises(ServiceUnavailableError, match="Connection refused"):
        await transport.post_json(
            path="https://api.example.com/verify",
            payload={"id": "123"},
            context_label="test_context",
        )


@pytest.mark.asyncio
async def test_service_http_transport_invalid_json() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="not-valid-json")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    transport = ServiceHttpTransport(
        http_client=client,
        api_key="secret_token",
        config=ServiceTransportConfig(
            service_name="test_svc",
            service_title="Test Service",
            timeout_seconds=2.0,
        ),
        base_url="https://api.example.com",
    )
    with pytest.raises(ServiceResponsePayloadError, match="violated schema"):
        await transport.post_json(
            path="https://api.example.com/verify",
            payload={"id": "123"},
        )


def test_service_transport_config_attributes() -> None:
    expected_timeout = 3.0
    config = ServiceTransportConfig(
        service_name="agristack",
        service_title="AgriStack",
        timeout_seconds=expected_timeout,
    )
    assert config.service_name == "agristack"
    assert config.service_title == "AgriStack"
    assert config.timeout_seconds == expected_timeout


def test_service_transport_config_validation() -> None:
    with pytest.raises(ServiceConfigurationError, match="Service name identifier is required"):
        ServiceTransportConfig(
            service_name="",
            service_title="AgriStack",
            timeout_seconds=3.0,
        )

    with pytest.raises(ServiceConfigurationError, match="Service title is required"):
        ServiceTransportConfig(
            service_name="agristack",
            service_title="   ",
            timeout_seconds=3.0,
        )

    with pytest.raises(ServiceConfigurationError, match="must be positive"):
        ServiceTransportConfig(
            service_name="agristack",
            service_title="AgriStack",
            timeout_seconds=0.0,
        )


@pytest.mark.asyncio
async def test_service_http_transport_created_and_accepted_statuses() -> None:
    for code in (201, 202):

        def handler(request: httpx.Request, status_code: int = code) -> httpx.Response:
            return httpx.Response(status_code, json={"status": "accepted_or_created"})

        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        transport = ServiceHttpTransport(
            http_client=client,
            api_key="secret_token",
            config=ServiceTransportConfig(
                service_name="test_svc",
                service_title="Test Service",
                timeout_seconds=2.0,
            ),
            base_url="https://api.test.gov.in",
        )
        result = await transport.post_json(path="/v1/action", payload={"key": "val"})
        assert result == {"status": "accepted_or_created"}
