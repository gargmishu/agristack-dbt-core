import json
from http import HTTPStatus

import httpx
import pytest

from src.errors.service_errors import (
    ServiceAuthenticationError,
    ServiceConfigurationError,
    ServiceRequestPayloadError,
    ServiceResponsePayloadError,
    ServiceUnavailableError,
)
from src.services.dpi import (
    LiveSchemePolicyService,
    MockSchemePolicyService,
    create_scheme_policy_service,
)
from src.services.dpi.dpi_mock_fixtures import EXCLUDED_POLICY_PREFIX


@pytest.mark.asyncio
async def test_mock_scheme_policy_service() -> None:
    service = MockSchemePolicyService()
    assert await service.verify_scheme_policy_coverage("Nashik", "Onion", "KHARIF-2026") is True
    assert (
        await service.verify_scheme_policy_coverage(
            f"{EXCLUDED_POLICY_PREFIX}_DISTRICT", "Onion", "KHARIF-2026"
        )
        is False
    )
    assert (
        await service.verify_scheme_policy_coverage(
            "Nashik", f"{EXCLUDED_POLICY_PREFIX}_CROP", "KHARIF-2026"
        )
        is False
    )
    assert await service.verify_scheme_policy_coverage("   ", "Onion", "KHARIF-2026") is False


@pytest.mark.asyncio
async def test_live_scheme_policy_mcp_tools_and_coverage() -> None:
    def mcp_handler(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("Authorization") == "Bearer dhara_key"
        assert str(request.url) == "https://datadhara.ekstep.org/mcp"
        body = json.loads(request.content.decode("utf-8"))
        assert body["jsonrpc"] == "2.0"
        assert body["method"] == "tools/call"
        tool_name = body["params"]["name"]
        args = body["params"]["arguments"]

        if tool_name == "get_table":
            assert args["dataset_id"] == "KHARIF-2026"
            assert args["column"] == "district"
            if args["equals"] == "Nashik":
                table_data = {
                    "dataset_id": "KHARIF-2026",
                    "title": "Maharashtra Hailstorm & Unseasonal Rain Notification",
                    "total": 1,
                    "rows": [
                        {
                            "sl_no": 1,
                            "row_index": 0,
                            "data": {
                                "district": "Nashik",
                                "crop_name": "Onion",
                                "active_season": "KHARIF-2026",
                            },
                        }
                    ],
                }
            else:
                table_data = {"dataset_id": "KHARIF-2026", "total": 0, "rows": []}
            return httpx.Response(
                HTTPStatus.OK,
                json={
                    "jsonrpc": "2.0",
                    "id": body["id"],
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(table_data)}],
                        "isError": False,
                    },
                },
            )

        if tool_name == "search_datasets":
            return httpx.Response(
                HTTPStatus.OK,
                json={
                    "jsonrpc": "2.0",
                    "id": body["id"],
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(
                                    {"total": 1, "datasets": [{"id": "KHARIF-2026"}]}
                                ),
                            }
                        ],
                        "isError": False,
                    },
                },
            )

        if tool_name == "get_metadata":
            return httpx.Response(
                HTTPStatus.OK,
                json={
                    "jsonrpc": "2.0",
                    "id": body["id"],
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(
                                    {
                                        "dataset": {
                                            "id": args["dataset_id"],
                                            "metadata_standard": "NMDS 2.0",
                                        }
                                    }
                                ),
                            }
                        ],
                        "isError": False,
                    },
                },
            )

        return httpx.Response(HTTPStatus.BAD_REQUEST)

    client = httpx.AsyncClient(transport=httpx.MockTransport(mcp_handler))
    service = LiveSchemePolicyService(
        endpoint_url="https://datadhara.ekstep.org",
        api_key="dhara_key",
        http_client=client,
    )
    assert await service.verify_scheme_policy_coverage("Nashik", "Onion", "KHARIF-2026") is True
    assert (
        await service.verify_scheme_policy_coverage("Nashik", "Dragonfruit", "KHARIF-2026") is False
    )
    assert await service.verify_scheme_policy_coverage("Pune", "Onion", "KHARIF-2026") is False

    datasets_res = await service.search_datasets(q="KHARIF-2026")
    assert datasets_res["total"] == 1
    meta_res = await service.get_metadata("KHARIF-2026")
    assert meta_res["dataset"]["metadata_standard"] == "NMDS 2.0"


@pytest.mark.asyncio
async def test_live_scheme_policy_direct_boolean_and_invalid_schemas() -> None:
    def direct_boolean_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            HTTPStatus.OK,
            json={"result": {"is_policy_covered": True}},
        )

    direct_client = httpx.AsyncClient(transport=httpx.MockTransport(direct_boolean_handler))
    direct_service = LiveSchemePolicyService(
        endpoint_url="https://datadhara.ekstep.org",
        api_key="dhara_key",
        http_client=direct_client,
    )
    assert (
        await direct_service.verify_scheme_policy_coverage("Nashik", "Onion", "KHARIF-2026") is True
    )

    def invalid_policy_schema_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(HTTPStatus.OK, json={"status": "ok"})

    bad_client = httpx.AsyncClient(transport=httpx.MockTransport(invalid_policy_schema_handler))
    bad_service = LiveSchemePolicyService(
        endpoint_url="https://datadhara.ekstep.org",
        api_key="dhara_key",
        http_client=bad_client,
    )
    with pytest.raises(ServiceResponsePayloadError, match="invalid schema"):
        await bad_service.verify_scheme_policy_coverage("Nashik", "Onion", "KHARIF-2026")

    def mcp_error_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            HTTPStatus.OK,
            json={"jsonrpc": "2.0", "result": {"isError": True, "content": []}},
        )

    mcp_error_client = httpx.AsyncClient(transport=httpx.MockTransport(mcp_error_handler))
    mcp_error_service = LiveSchemePolicyService(
        endpoint_url="https://datadhara.ekstep.org",
        api_key="dhara_key",
        http_client=mcp_error_client,
    )
    with pytest.raises(ServiceResponsePayloadError, match="MCP tool execution failed"):
        await mcp_error_service.verify_scheme_policy_coverage("Nashik", "Onion", "KHARIF-2026")


@pytest.mark.asyncio
async def test_live_scheme_policy_error_handling() -> None:
    def error_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(HTTPStatus.INTERNAL_SERVER_ERROR, text="Policy Gateway Outage")

    client = httpx.AsyncClient(transport=httpx.MockTransport(error_handler))
    service = LiveSchemePolicyService(
        endpoint_url="https://datadhara.ekstep.org",
        api_key="valid_key",
        http_client=client,
    )
    with pytest.raises(ServiceUnavailableError, match="status=500"):
        await service.verify_scheme_policy_coverage("Nashik", "Onion", "KHARIF-2026")

    def auth_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(HTTPStatus.FORBIDDEN, text="Forbidden")

    auth_client = httpx.AsyncClient(transport=httpx.MockTransport(auth_handler))
    auth_service = LiveSchemePolicyService(
        endpoint_url="https://datadhara.ekstep.org",
        api_key="invalid_key",
        http_client=auth_client,
    )
    with pytest.raises(
        ServiceAuthenticationError, match="Scheme Policy Metadata authentication failed"
    ):
        await auth_service.verify_scheme_policy_coverage("Nashik", "Onion", "KHARIF-2026")

    def bad_request_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(HTTPStatus.UNPROCESSABLE_ENTITY, text="Invalid LGD district code")

    bad_req_client = httpx.AsyncClient(transport=httpx.MockTransport(bad_request_handler))
    bad_req_service = LiveSchemePolicyService(
        endpoint_url="https://datadhara.ekstep.org",
        api_key="valid_key",
        http_client=bad_req_client,
    )
    with pytest.raises(ServiceRequestPayloadError, match="Invalid LGD district code"):
        await bad_req_service.verify_scheme_policy_coverage("INVALID", "Onion", "KHARIF-2026")


@pytest.mark.asyncio
async def test_create_scheme_policy_service_factory(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.delenv("SCHEME_POLICY_API_ENDPOINT", raising=False)
    monkeypatch.delenv("SCHEME_POLICY_API_KEY", raising=False)

    service = create_scheme_policy_service()
    assert isinstance(service, MockSchemePolicyService)

    explicit_live = create_scheme_policy_service(
        endpoint_url="https://datadhara.ekstep.org",
        api_key="explicit_key",
    )
    assert isinstance(explicit_live, LiveSchemePolicyService)

    monkeypatch.setenv("ENVIRONMENT", "production")
    with pytest.raises(ServiceConfigurationError, match="SCHEME_POLICY_API_ENDPOINT"):
        create_scheme_policy_service()

    monkeypatch.setenv("SCHEME_POLICY_API_ENDPOINT", "https://datadhara.ekstep.org")
    monkeypatch.setenv("SCHEME_POLICY_API_KEY", "prod_token")
    live_service = create_scheme_policy_service()
    assert isinstance(live_service, LiveSchemePolicyService)
