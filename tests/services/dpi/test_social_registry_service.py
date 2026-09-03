from datetime import UTC, datetime

import httpx
import pytest

from src.data_models.caseworker import CaseworkerCaseReviewPayload
from src.data_models.common import ApplicationIntent, EscalationReasonCode
from src.errors.service_errors import (
    ServiceAuthenticationError,
    ServiceConfigurationError,
    ServiceRequestPayloadError,
    ServiceResponsePayloadError,
    ServiceUnavailableError,
)
from src.services.dpi import (
    LiveSocialRegistryService,
    MockSocialRegistryService,
    create_social_registry_service,
)
from src.services.dpi.dpi_mock_fixtures import (
    MOCK_CASE_REJECT_PREFIX,
    UNVERIFIED_IDENTITY_PREFIX,
)


@pytest.mark.asyncio
async def test_mock_social_registry_verify_incident_ticket_eligibility() -> None:
    service = MockSocialRegistryService()
    payload = CaseworkerCaseReviewPayload(
        escalation_case_id="SPP-CASE-2026-100200",
        session_id="sess_12345678",
        payload_id="ext_12345678",
        tokenized_citizen_id="a1b2c3d4e5f60718293a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e",
        application_intent=ApplicationIntent.APPLY_SUBSIDY,
        unprocessed_input_content="Fasal kharab ho gayi hai",
        escalation_reason=EscalationReasonCode.LOW_AI_CONFIDENCE,
        staged_at=datetime.now(UTC),
    )
    synced = await service.verify_incident_ticket_eligibility(payload)
    assert synced is True


@pytest.mark.asyncio
async def test_mock_social_registry_verify_incident_ticket_eligibility_rejection_prefix() -> None:
    service = MockSocialRegistryService()
    payload = CaseworkerCaseReviewPayload(
        escalation_case_id=f"{MOCK_CASE_REJECT_PREFIX}-CASE-2026-100200",
        session_id="sess_12345678",
        payload_id="ext_12345678",
        tokenized_citizen_id="a1b2c3d4e5f60718293a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e",
        application_intent=ApplicationIntent.APPLY_SUBSIDY,
        unprocessed_input_content="Fasal kharab ho gayi hai",
        escalation_reason=EscalationReasonCode.LOW_AI_CONFIDENCE,
        staged_at=datetime.now(UTC),
    )
    synced = await service.verify_incident_ticket_eligibility(payload)
    assert synced is True


@pytest.mark.asyncio
async def test_mock_social_registry_query_beneficiary_eligibility() -> None:
    service = MockSocialRegistryService()
    valid_hmac = "a1b2c3d4e5f60718293a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e"
    zero_hmac = "0000000000000000000000000000000000000000000000000000000000000000"
    unverified_hmac = UNVERIFIED_IDENTITY_PREFIX + "a" * (64 - len(UNVERIFIED_IDENTITY_PREFIX))

    assert await service.query_beneficiary_eligibility(valid_hmac, "PM_KISAN") is True
    assert await service.query_beneficiary_eligibility(zero_hmac, "PM_KISAN") is False
    assert await service.query_beneficiary_eligibility(unverified_hmac, "PM_KISAN") is False
    assert await service.query_beneficiary_eligibility(valid_hmac, "   ") is False


@pytest.mark.asyncio
async def test_live_social_registry_endpoint_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("Authorization") == "Bearer openspp_key"
        assert str(request.url) == "https://openspp.gov.in/v1/social/eligibility"
        return httpx.Response(200, json={"is_eligible": True, "scheme_id": "PM_KISAN"})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    service = LiveSocialRegistryService(
        endpoint_url="https://openspp.gov.in",
        api_key="openspp_key",
        http_client=client,
    )
    is_eligible = await service.query_beneficiary_eligibility("a" * 64, "PM_KISAN")
    assert is_eligible is True

    payload = CaseworkerCaseReviewPayload(
        escalation_case_id="SPP-CASE-2026-100200",
        session_id="sess_12345678",
        payload_id="ext_12345678",
        tokenized_citizen_id="a" * 64,
        application_intent=ApplicationIntent.APPLY_SUBSIDY,
        unprocessed_input_content="Fasal kharab ho gayi hai",
        escalation_reason=EscalationReasonCode.LOW_AI_CONFIDENCE,
        staged_at=datetime.now(UTC),
    )
    assert await service.verify_incident_ticket_eligibility(payload) is True


@pytest.mark.asyncio
async def test_live_social_registry_constructor_validation() -> None:
    client = httpx.AsyncClient()
    with pytest.raises(ServiceConfigurationError, match="endpoint URL is required"):
        LiveSocialRegistryService(endpoint_url="", api_key="valid_key", http_client=client)

    with pytest.raises(ServiceConfigurationError, match="must start with 'http://' or 'https://'"):
        LiveSocialRegistryService(
            endpoint_url="openspp.gov.in", api_key="valid_key", http_client=client
        )

    with pytest.raises(ServiceConfigurationError, match="API key is required"):
        LiveSocialRegistryService(
            endpoint_url="https://openspp.gov.in", api_key="", http_client=client
        )


@pytest.mark.asyncio
async def test_live_social_registry_fail_closed_on_500() -> None:
    def error_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="OpenSPP Outage")

    client = httpx.AsyncClient(transport=httpx.MockTransport(error_handler))
    service = LiveSocialRegistryService(
        endpoint_url="https://openspp.gov.in",
        api_key="valid_key",
        http_client=client,
    )
    with pytest.raises(ServiceUnavailableError, match="status=500"):
        await service.query_beneficiary_eligibility("a" * 64, "PM_KISAN")


@pytest.mark.asyncio
async def test_live_social_registry_fail_closed_on_auth_failure() -> None:
    def auth_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, text="Forbidden")

    client = httpx.AsyncClient(transport=httpx.MockTransport(auth_handler))
    service = LiveSocialRegistryService(
        endpoint_url="https://openspp.gov.in",
        api_key="invalid_key",
        http_client=client,
    )
    with pytest.raises(ServiceAuthenticationError, match="OpenSPP authentication failed"):
        await service.query_beneficiary_eligibility("a" * 64, "PM_KISAN")


@pytest.mark.asyncio
async def test_live_social_registry_malformed_payload_error() -> None:
    def bad_request_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(422, text="Unprocessable social scheme identifier")

    client = httpx.AsyncClient(transport=httpx.MockTransport(bad_request_handler))
    service = LiveSocialRegistryService(
        endpoint_url="https://openspp.gov.in",
        api_key="valid_key",
        http_client=client,
    )
    with pytest.raises(ServiceRequestPayloadError, match="Unprocessable social scheme identifier"):
        await service.query_beneficiary_eligibility("a" * 64, "INVALID_SCHEME")


@pytest.mark.asyncio
async def test_live_social_registry_response_payload_contract_violation() -> None:
    def invalid_schema_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"status": "ok"})  # missing 'is_eligible'

    client = httpx.AsyncClient(transport=httpx.MockTransport(invalid_schema_handler))
    service = LiveSocialRegistryService(
        endpoint_url="https://openspp.gov.in",
        api_key="valid_key",
        http_client=client,
    )
    with pytest.raises(ServiceResponsePayloadError, match="invalid schema"):
        await service.query_beneficiary_eligibility("a" * 64, "PM-KISAN")


@pytest.mark.asyncio
async def test_live_social_registry_non_dict_json_response() -> None:
    def list_json_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=["unexpected", "array"])

    client = httpx.AsyncClient(transport=httpx.MockTransport(list_json_handler))
    service = LiveSocialRegistryService(
        endpoint_url="https://openspp.gov.in",
        api_key="valid_key",
        http_client=client,
    )
    with pytest.raises(ServiceResponsePayloadError, match="non-dictionary JSON"):
        await service.query_beneficiary_eligibility("a" * 64, "PM-KISAN")


@pytest.mark.asyncio
async def test_live_social_registry_service_from_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OPENSPP_API_ENDPOINT", raising=False)
    monkeypatch.delenv("OPENSPP_API_KEY", raising=False)

    with pytest.raises(ServiceConfigurationError, match="endpoint URL is required"):
        LiveSocialRegistryService.from_env()

    with pytest.raises(ServiceConfigurationError, match="API key is required"):
        LiveSocialRegistryService.from_env(endpoint_url="https://openspp.gov.in")

    # From explicit parameters
    service = LiveSocialRegistryService.from_env(
        endpoint_url="https://openspp.gov.in", api_key="valid_key"
    )
    assert isinstance(service, LiveSocialRegistryService)

    # From environment variables
    monkeypatch.setenv("OPENSPP_API_ENDPOINT", "https://openspp.gov.in")
    monkeypatch.setenv("OPENSPP_API_KEY", "valid_key")
    service_env = LiveSocialRegistryService.from_env()
    assert isinstance(service_env, LiveSocialRegistryService)


@pytest.mark.asyncio
async def test_create_social_registry_service_factory(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.delenv("OPENSPP_API_ENDPOINT", raising=False)
    monkeypatch.delenv("OPENSPP_API_KEY", raising=False)

    service = create_social_registry_service()
    assert isinstance(service, MockSocialRegistryService)

    monkeypatch.setenv("ENVIRONMENT", "production")
    with pytest.raises(ServiceConfigurationError, match="OPENSPP_API_ENDPOINT"):
        create_social_registry_service()

    monkeypatch.setenv("OPENSPP_API_ENDPOINT", "https://openspp.gov.in")
    monkeypatch.setenv("OPENSPP_API_KEY", "prod_token")
    live_service = create_social_registry_service()
    assert isinstance(live_service, LiveSocialRegistryService)
