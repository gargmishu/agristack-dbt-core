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
from src.services.dpi import PaymentRailService


@pytest.mark.asyncio
async def test_payment_rail_initiate_disbursement() -> None:
    service = PaymentRailService()
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
async def test_payment_rail_disbursement_failure() -> None:
    service = PaymentRailService()
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
async def test_payment_rail_skips_when_txn_id_is_none() -> None:
    service = PaymentRailService()
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
async def test_payment_rail_live_endpoint_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("Authorization") == "Bearer pfms_token"
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
    service = PaymentRailService(
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
async def test_payment_rail_live_endpoint_error_fallback() -> None:
    def error_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="Payment Gateway Down")

    client = httpx.AsyncClient(transport=httpx.MockTransport(error_handler))
    service = PaymentRailService(
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


@pytest.mark.asyncio
async def test_payment_rail_ephemeral_client_error_fallback() -> None:
    service = PaymentRailService(
        endpoint_url="http://invalid.unreachable.endpoint.local:9999",
        api_key="pfms_token",
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


@pytest.mark.asyncio
async def test_payment_rail_no_api_key_and_non_dict_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert "Authorization" not in request.headers
        return httpx.Response(200, json="invalid string response")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    service = PaymentRailService(
        endpoint_url="https://pfms.gov.in",
        api_key=None,
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
