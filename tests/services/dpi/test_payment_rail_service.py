from datetime import UTC, datetime

import httpx
import pytest

from src.data_models.common import (
    DisbursementStatus,
    EligibilityStatus,
    GovernanceAction,
    RejectionReasonCode,
)
from src.data_models.governance import GovernanceOutcomePayload
from src.errors.service_errors import (
    ServiceAuthenticationError,
    ServiceConfigurationError,
    ServiceRequestPayloadError,
    ServiceResponsePayloadError,
    ServiceUnavailableError,
)
from src.services.dpi import (
    LivePaymentRailService,
    MockPaymentRailService,
    create_payment_rail_service,
)


@pytest.mark.asyncio
async def test_mock_payment_rail_initiate_disbursement() -> None:
    service = MockPaymentRailService()
    outcome = GovernanceOutcomePayload(
        session_id="sess_12345678",
        payload_id="ext_12345678",
        ai_confidence_score=0.96,
        eligibility_status=EligibilityStatus.ELIGIBLE,
        governance_action=GovernanceAction.AUTO_APPROVE,
        disbursement_txn_id="TXN-2026-987654",
        disbursement_status=DisbursementStatus.PENDING,
        evaluated_at=datetime.now(UTC),
    )
    result = await service.initiate_disbursement(outcome)
    assert result is not None
    assert result.disbursement_txn_id == "TXN-2026-987654"
    assert result.disbursement_status == DisbursementStatus.SUCCESS


@pytest.mark.asyncio
async def test_mock_payment_rail_disbursement_failure() -> None:
    service = MockPaymentRailService()
    outcome = GovernanceOutcomePayload(
        session_id="sess_12345678",
        payload_id="ext_12345678",
        ai_confidence_score=0.96,
        eligibility_status=EligibilityStatus.ELIGIBLE,
        governance_action=GovernanceAction.AUTO_APPROVE,
        disbursement_txn_id="TXN-2026-FAIL-101",
        disbursement_status=DisbursementStatus.PENDING,
        evaluated_at=datetime.now(UTC),
    )
    result = await service.initiate_disbursement(outcome)
    assert result is not None
    assert result.disbursement_status == DisbursementStatus.FAILED
    assert result.failure_reason_code is not None


@pytest.mark.asyncio
async def test_mock_payment_rail_skips_when_txn_id_is_none() -> None:
    service = MockPaymentRailService()
    outcome = GovernanceOutcomePayload(
        session_id="sess_12345678",
        payload_id="ext_12345678",
        ai_confidence_score=0.45,
        eligibility_status=EligibilityStatus.INELIGIBLE,
        governance_action=GovernanceAction.AUTO_REJECT,
        rejection_reason=RejectionReasonCode.LAND_RECORD_NOT_FOUND,
        disbursement_txn_id=None,
        disbursement_status=None,
        evaluated_at=datetime.now(UTC),
    )
    result = await service.initiate_disbursement(outcome)
    assert result is None


@pytest.mark.asyncio
async def test_live_payment_rail_endpoint_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("Authorization") == "Bearer pfms_token"
        assert str(request.url) == "https://pfms.gov.in/v1/payments/disburse"
        return httpx.Response(
            200,
            json={
                "disbursement_txn_id": "TXN-2026-987654",
                "bank_reference_id": "NPCI-LIVE-UTR-123456",
                "disbursement_status": "SUCCESS",
                "cleared_at": "2026-08-26T12:00:00Z",
                "failure_reason_code": None,
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    service = LivePaymentRailService(
        endpoint_url="https://pfms.gov.in",
        api_key="pfms_token",
        http_client=client,
    )
    outcome = GovernanceOutcomePayload(
        session_id="sess_12345678",
        payload_id="ext_12345678",
        ai_confidence_score=0.96,
        eligibility_status=EligibilityStatus.ELIGIBLE,
        governance_action=GovernanceAction.AUTO_APPROVE,
        disbursement_txn_id="TXN-2026-987654",
        disbursement_status=DisbursementStatus.PENDING,
        evaluated_at=datetime.now(UTC),
    )
    result = await service.initiate_disbursement(outcome)
    assert result is not None
    assert result.disbursement_status == DisbursementStatus.SUCCESS
    assert result.bank_reference_id == "NPCI-LIVE-UTR-123456"


@pytest.mark.asyncio
async def test_live_payment_rail_skips_when_txn_id_is_none() -> None:
    client = httpx.AsyncClient()
    service = LivePaymentRailService(
        endpoint_url="https://pfms.gov.in",
        api_key="pfms_token",
        http_client=client,
    )
    outcome = GovernanceOutcomePayload(
        session_id="sess_12345678",
        payload_id="ext_12345678",
        ai_confidence_score=0.45,
        eligibility_status=EligibilityStatus.INELIGIBLE,
        governance_action=GovernanceAction.AUTO_REJECT,
        rejection_reason=RejectionReasonCode.LAND_RECORD_NOT_FOUND,
        disbursement_txn_id=None,
        disbursement_status=None,
        evaluated_at=datetime.now(UTC),
    )
    assert await service.initiate_disbursement(outcome) is None


@pytest.mark.asyncio
async def test_live_payment_rail_constructor_validation() -> None:
    client = httpx.AsyncClient()
    with pytest.raises(ServiceConfigurationError, match="endpoint URL is required"):
        LivePaymentRailService(endpoint_url="", api_key="valid_key", http_client=client)

    with pytest.raises(ServiceConfigurationError, match="must start with 'http://' or 'https://'"):
        LivePaymentRailService(endpoint_url="pfms.gov.in", api_key="valid_key", http_client=client)

    with pytest.raises(ServiceConfigurationError, match="API key is required"):
        LivePaymentRailService(endpoint_url="https://pfms.gov.in", api_key="", http_client=client)


@pytest.mark.asyncio
async def test_live_payment_rail_fail_closed_on_500() -> None:
    def error_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="Banking Gateway Timeout")

    client = httpx.AsyncClient(transport=httpx.MockTransport(error_handler))
    service = LivePaymentRailService(
        endpoint_url="https://pfms.gov.in",
        api_key="valid_key",
        http_client=client,
    )
    outcome = GovernanceOutcomePayload(
        session_id="sess_12345678",
        payload_id="ext_12345678",
        ai_confidence_score=0.96,
        eligibility_status=EligibilityStatus.ELIGIBLE,
        governance_action=GovernanceAction.AUTO_APPROVE,
        disbursement_txn_id="TXN-2026-987654",
        disbursement_status=DisbursementStatus.PENDING,
        evaluated_at=datetime.now(UTC),
    )
    with pytest.raises(ServiceUnavailableError, match="status=500"):
        await service.initiate_disbursement(outcome)


@pytest.mark.asyncio
async def test_live_payment_rail_fail_closed_on_auth_failure() -> None:
    def auth_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, text="Unauthorized")

    client = httpx.AsyncClient(transport=httpx.MockTransport(auth_handler))
    service = LivePaymentRailService(
        endpoint_url="https://pfms.gov.in",
        api_key="invalid_key",
        http_client=client,
    )
    outcome = GovernanceOutcomePayload(
        session_id="sess_12345678",
        payload_id="ext_12345678",
        ai_confidence_score=0.96,
        eligibility_status=EligibilityStatus.ELIGIBLE,
        governance_action=GovernanceAction.AUTO_APPROVE,
        disbursement_txn_id="TXN-2026-987654",
        disbursement_status=DisbursementStatus.PENDING,
        evaluated_at=datetime.now(UTC),
    )
    with pytest.raises(ServiceAuthenticationError, match="Payment rail authentication failed"):
        await service.initiate_disbursement(outcome)


@pytest.mark.asyncio
async def test_live_payment_rail_malformed_payload_error() -> None:
    def bad_request_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(422, text="Invalid disbursement transaction payload schema")

    client = httpx.AsyncClient(transport=httpx.MockTransport(bad_request_handler))
    service = LivePaymentRailService(
        endpoint_url="https://pfms.gov.in",
        api_key="valid_key",
        http_client=client,
    )
    outcome = GovernanceOutcomePayload(
        session_id="sess_12345678",
        payload_id="ext_12345678",
        ai_confidence_score=0.96,
        eligibility_status=EligibilityStatus.ELIGIBLE,
        governance_action=GovernanceAction.AUTO_APPROVE,
        disbursement_txn_id="TXN-2026-987654",
        disbursement_status=DisbursementStatus.PENDING,
        evaluated_at=datetime.now(UTC),
    )
    with pytest.raises(ServiceRequestPayloadError, match="Invalid disbursement transaction"):
        await service.initiate_disbursement(outcome)


@pytest.mark.asyncio
async def test_live_payment_rail_response_payload_contract_violation() -> None:
    def invalid_schema_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"unexpected": 123})

    client = httpx.AsyncClient(transport=httpx.MockTransport(invalid_schema_handler))
    service = LivePaymentRailService(
        endpoint_url="https://npci.gov.in",
        api_key="valid_key",
        http_client=client,
    )
    outcome = GovernanceOutcomePayload(
        session_id="sess_12345678",
        payload_id="ext_12345678",
        ai_confidence_score=0.96,
        eligibility_status=EligibilityStatus.ELIGIBLE,
        governance_action=GovernanceAction.AUTO_APPROVE,
        disbursement_txn_id="TXN-2026-987654",
        disbursement_status=DisbursementStatus.PENDING,
        evaluated_at=datetime.now(UTC),
    )
    with pytest.raises(ServiceResponsePayloadError, match="violated schema"):
        await service.initiate_disbursement(outcome)


@pytest.mark.asyncio
async def test_live_payment_rail_non_dict_json_response() -> None:
    def list_json_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=["unexpected", "array"])

    client = httpx.AsyncClient(transport=httpx.MockTransport(list_json_handler))
    service = LivePaymentRailService(
        endpoint_url="https://npci.gov.in",
        api_key="valid_key",
        http_client=client,
    )
    outcome = GovernanceOutcomePayload(
        session_id="sess_12345678",
        payload_id="ext_12345678",
        ai_confidence_score=0.96,
        eligibility_status=EligibilityStatus.ELIGIBLE,
        governance_action=GovernanceAction.AUTO_APPROVE,
        disbursement_txn_id="TXN-2026-987654",
        disbursement_status=DisbursementStatus.PENDING,
        evaluated_at=datetime.now(UTC),
    )
    with pytest.raises(ServiceResponsePayloadError, match="non-dictionary JSON"):
        await service.initiate_disbursement(outcome)


@pytest.mark.asyncio
async def test_live_payment_rail_service_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NPCI_APBS_API_ENDPOINT", raising=False)
    monkeypatch.delenv("NPCI_APBS_API_KEY", raising=False)

    with pytest.raises(ServiceConfigurationError, match="endpoint URL is required"):
        LivePaymentRailService.from_env()

    with pytest.raises(ServiceConfigurationError, match="API key is required"):
        LivePaymentRailService.from_env(endpoint_url="https://pfms.gov.in")

    # From explicit parameters
    service = LivePaymentRailService.from_env(
        endpoint_url="https://pfms.gov.in", api_key="valid_key"
    )
    assert isinstance(service, LivePaymentRailService)

    # From environment variables
    monkeypatch.setenv("NPCI_APBS_API_ENDPOINT", "https://pfms.gov.in")
    monkeypatch.setenv("NPCI_APBS_API_KEY", "valid_key")
    service_env = LivePaymentRailService.from_env()
    assert isinstance(service_env, LivePaymentRailService)


@pytest.mark.asyncio
async def test_create_payment_rail_service_factory(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.delenv("NPCI_APBS_API_ENDPOINT", raising=False)
    monkeypatch.delenv("NPCI_APBS_API_KEY", raising=False)

    service = create_payment_rail_service()
    assert isinstance(service, MockPaymentRailService)

    monkeypatch.setenv("ENVIRONMENT", "production")
    with pytest.raises(ServiceConfigurationError, match="NPCI_APBS_API_ENDPOINT"):
        create_payment_rail_service()

    monkeypatch.setenv("NPCI_APBS_API_ENDPOINT", "https://npci.org.in")
    monkeypatch.setenv("NPCI_APBS_API_KEY", "prod_token")
    live_service = create_payment_rail_service()
    assert isinstance(live_service, LivePaymentRailService)
