"""Layer 3 Public Agent HTTP Server & Webhook Entrypoint.

Exposes the ASGI FastAPI application binding Layer 1 carrier edge connectors
(WhatsApp, IVR, USSD, SMS), Layer 2 perimeter authentication & Zero-Trust tokenization,
Layer 3 intake extraction, Layer 4 governance orchestration, District Caseworker review
queues, and CAG statutory audit endpoints.

See: decisions/step3.4_layer3_intake_gateway_and_connectors.md
See: decisions/step3.2_security_and_ingestion_firewalls.md
See: decisions/step4.5_database_persistence_and_analytical_deduplication.md
"""

from __future__ import annotations

from collections.abc import Mapping
from http import HTTPStatus
from typing import Any, Final

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from src.connectors import (
    IvrConnector,
    SmsConnector,
    UssdConnector,
    WhatsAppConnector,
)
from src.data_models.caseworker import (
    CaseworkerCaseReviewPayload,
    CaseworkerReviewOutcomePayload,
)
from src.data_models.common import (
    ApplicationStatus,
    EligibilityStatus,
    GovernanceAction,
    LanguageLocale,
)
from src.data_models.disbursement import (
    DisbursementCallbackPayload,
    G2pConnectOnDisbursePayload,
)
from src.data_models.raw_ingress import (
    IvrIngressPayload,
    SmsIngressPayload,
    UssdIngressPayload,
    WhatsAppIngressPayload,
)
from src.errors import validation_exception_handler
from src.gateway import CarrierAuthValidator
from src.orchestrator import CaseManagementService, ClaimOrchestrator
from src.public_agent.public_agent_api import PublicAgentApi, PublicAgentIntakeResult
from src.services.dpi import G2pConnectMapperService
from src.services.persistence import LedgerPersistenceService

__all__ = [
    "PublicAgentHttpServer",
    "create_public_agent_http_app",
]

_HEALTH_PATH: Final[str] = "/healthz"
_WHATSAPP_WEBHOOK_PATH: Final[str] = "/v1/webhooks/whatsapp"
_IVR_WEBHOOK_PATH: Final[str] = "/v1/webhooks/ivr"
_USSD_WEBHOOK_PATH: Final[str] = "/v1/webhooks/ussd"
_SMS_WEBHOOK_PATH: Final[str] = "/v1/webhooks/sms"
_PAYMENT_CALLBACK_WEBHOOK_PATH: Final[str] = "/v1/webhooks/payments/callback"
_G2P_ON_DISBURSE_WEBHOOK_PATH: Final[str] = "/v1/webhooks/g2p-connect/on-disburse"
_CASEWORKER_LIST_PATH: Final[str] = "/v1/caseworker/cases"
_CASEWORKER_REVIEW_PATH: Final[str] = "/v1/caseworker/cases/{escalation_case_id}/review"
_AUDIT_FUNNEL_PATH: Final[str] = "/v1/audit/funnel"
_AUDIT_HISTORY_PATH: Final[str] = "/v1/audit/history/{claim_id}"

_SIGNATURE_HEADER_NAME: Final[str] = "X-Hub-Signature-256"
_AUTHORIZATION_HEADER_NAME: Final[str] = "Authorization"
_LANGUAGE_HEADER_NAME: Final[str] = "X-Language-Locale"
_ATTEMPT_HEADER_NAME: Final[str] = "X-Attempt-Count"


class PublicAgentHttpServer:
    """ASGI HTTP server coordinating multichannel webhooks, caseworker reviews, and audit trails."""

    def __init__(  # noqa: PLR0913
        self,
        *,
        public_agent_api: PublicAgentApi | None = None,
        case_management_service: CaseManagementService | None = None,
        ledger_persistence_service: LedgerPersistenceService | None = None,
        whatsapp_connector: WhatsAppConnector | None = None,
        ivr_connector: IvrConnector | None = None,
        ussd_connector: UssdConnector | None = None,
        sms_connector: SmsConnector | None = None,
        g2p_connect_mapper: G2pConnectMapperService | None = None,
        whatsapp_app_secret: str | None = None,
        carrier_bearer_token: str | None = None,
    ) -> None:
        """Initializes the Public Agent HTTP server and wires all Layer 1-4 collaborators."""
        self._case_management_service = case_management_service or CaseManagementService()
        self._ledger_persistence_service = ledger_persistence_service or LedgerPersistenceService(
            database_url="sqlite:///:memory:"
        )
        if public_agent_api is not None:
            self._public_agent_api = public_agent_api
        else:
            orchestrator = ClaimOrchestrator(
                case_management_service=self._case_management_service,
                ledger_persistence_service=self._ledger_persistence_service,
            )
            self._public_agent_api = PublicAgentApi(orchestrator=orchestrator)

        self._whatsapp_connector = whatsapp_connector or WhatsAppConnector()
        self._ivr_connector = ivr_connector or IvrConnector()
        self._ussd_connector = ussd_connector or UssdConnector()
        self._sms_connector = sms_connector or SmsConnector()
        self._g2p_connect_mapper = g2p_connect_mapper or G2pConnectMapperService.from_env()
        self._whatsapp_app_secret = whatsapp_app_secret
        self._carrier_bearer_token = carrier_bearer_token
        self._app = self._build_fastapi_app()

    # -------------------------------------------------------------------------
    # Primary Public Workflow Entrypoints
    # -------------------------------------------------------------------------

    @property
    def app(self) -> FastAPI:
        """Returns the configured FastAPI ASGI application instance."""
        return self._app

    async def handle_health_check(self) -> JSONResponse:
        """Returns liveness status for State Data Centre and load balancer health probes."""
        return JSONResponse(
            status_code=HTTPStatus.OK,
            content={"status": "healthy", "service": "agristack-dbt-core"},
        )

    async def handle_whatsapp_webhook(self, incoming_request: Request) -> JSONResponse:
        """Processes inbound Meta WhatsApp Business API webhook events."""
        raw_body_bytes = await incoming_request.body()
        if self._whatsapp_app_secret is not None:
            signature_header = incoming_request.headers.get(_SIGNATURE_HEADER_NAME)
            is_valid_signature = CarrierAuthValidator.validate_hmac_signature(
                payload_bytes=raw_body_bytes,
                signature_header=signature_header,
                app_secret=self._whatsapp_app_secret,
            )
            if not is_valid_signature:
                return self._build_unauthorized_response(
                    "Invalid or missing X-Hub-Signature-256 webhook signature."
                )

        payload_mapping = await self._parse_json_mapping(incoming_request)
        validated_payload = await self._whatsapp_connector.process_webhook(payload_mapping)
        return await self._execute_ingress_pipeline(incoming_request, validated_payload)

    async def handle_ivr_webhook(self, incoming_request: Request) -> JSONResponse:
        """Processes inbound SIP telephony IVR voice session webhooks."""
        auth_error_response = self._verify_bearer_token_if_configured(incoming_request)
        if auth_error_response is not None:
            return auth_error_response

        payload_mapping = await self._parse_json_mapping(incoming_request)
        validated_payload = await self._ivr_connector.process_call_session(payload_mapping)
        return await self._execute_ingress_pipeline(incoming_request, validated_payload)

    async def handle_ussd_webhook(self, incoming_request: Request) -> JSONResponse:
        """Processes inbound SS7/SIGTRAN USSD menu signaling webhooks."""
        auth_error_response = self._verify_bearer_token_if_configured(incoming_request)
        if auth_error_response is not None:
            return auth_error_response

        payload_mapping = await self._parse_json_mapping(incoming_request)
        validated_payload = await self._ussd_connector.process_ussd_session(payload_mapping)
        return await self._execute_ingress_pipeline(incoming_request, validated_payload)

    async def handle_sms_webhook(self, incoming_request: Request) -> JSONResponse:
        """Processes inbound TRAI DLT transactional SMS webhooks."""
        auth_error_response = self._verify_bearer_token_if_configured(incoming_request)
        if auth_error_response is not None:
            return auth_error_response

        payload_mapping = await self._parse_json_mapping(incoming_request)
        validated_payload = await self._sms_connector.process_inbound_sms(payload_mapping)
        return await self._execute_ingress_pipeline(incoming_request, validated_payload)

    async def handle_list_staged_cases(self) -> JSONResponse:
        """Lists all escalated claims currently staged in the district caseworker queue."""
        staged_cases = [
            case_item.model_dump(mode="json")
            for case_item in self._case_management_service.list_staged_cases()
        ]
        return JSONResponse(
            status_code=HTTPStatus.OK,
            content={"staged_cases": staged_cases},
        )

    async def handle_caseworker_review(
        self, escalation_case_id: str, incoming_request: Request
    ) -> JSONResponse:
        """Processes a district officer manual review decision on a staged escalation ticket."""
        payload_mapping = await self._parse_json_mapping(incoming_request)
        review_outcome = CaseworkerReviewOutcomePayload.model_validate(payload_mapping)
        if review_outcome.escalation_case_id != escalation_case_id:
            return self._build_problem_response(
                http_status=HTTPStatus.BAD_REQUEST,
                error_type="https://api.agristack.gov.in/errors/case-id-mismatch",
                title="Escalation Case ID Mismatch",
                detail="Path escalation_case_id does not match payload escalation_case_id.",
            )

        staged_case = self._case_management_service.get_staged_case(escalation_case_id)
        was_processed = await self._case_management_service.process_officer_review(review_outcome)
        if not was_processed or staged_case is None:
            return self._build_problem_response(
                http_status=HTTPStatus.NOT_FOUND,
                error_type="https://api.agristack.gov.in/errors/case-not-found",
                title="Staged Case Not Found",
                detail=f"Escalation ticket '{escalation_case_id}' is not staged for review.",
            )

        updated_status = self._case_management_service.get_case_status(escalation_case_id)
        if updated_status is not None:
            self._persist_caseworker_review_decision(
                staged_case=staged_case,
                application_status=updated_status,
                review_outcome=review_outcome,
            )

        return JSONResponse(
            status_code=HTTPStatus.OK,
            content={
                "escalation_case_id": escalation_case_id,
                "application_status": updated_status,
                "governance_action": review_outcome.governance_action,
                "reviewer_id": review_outcome.reviewer_id,
            },
        )

    async def handle_payment_callback(self, incoming_request: Request) -> JSONResponse:
        """Processes asynchronous NPCI APBS / PFMS payment clearing callback webhooks."""
        auth_error_response = self._verify_bearer_token_if_configured(incoming_request)
        if auth_error_response is not None:
            return auth_error_response

        payload_mapping = await self._parse_json_mapping(incoming_request)
        callback_payload = DisbursementCallbackPayload.model_validate(payload_mapping)
        return self._reconcile_and_build_callback_response(callback_payload)

    async def handle_g2p_on_disburse_webhook(self, incoming_request: Request) -> JSONResponse:
        """Processes signed G2P Connect (DCI) v1.0.0 `on-disburse` payment clearing callbacks."""
        payload_mapping = await self._parse_json_mapping(incoming_request)
        g2p_envelope = G2pConnectOnDisbursePayload.model_validate(payload_mapping)
        try:
            callback_payload = self._g2p_connect_mapper.parse_on_disburse_callback(g2p_envelope)
        except ValueError as signature_error:
            return self._build_unauthorized_response(str(signature_error))

        return self._reconcile_and_build_callback_response(callback_payload)

    async def handle_audit_funnel(self) -> JSONResponse:
        """Returns the window-deduplicated Citizen Journey Funnel analytical rows."""
        funnel_rows = self._ledger_persistence_service.fetch_deduplicated_citizen_journey_funnel()
        return JSONResponse(
            status_code=HTTPStatus.OK,
            content={"funnel_rows": funnel_rows},
        )

    async def handle_audit_history(self, claim_id: str) -> JSONResponse:
        """Returns the immutable SQL trigger governance audit trail for a specific claim."""
        audit_history = self._ledger_persistence_service.fetch_governance_audit_history(
            claim_id=claim_id
        )
        return JSONResponse(
            status_code=HTTPStatus.OK,
            content={"claim_id": claim_id, "audit_history": audit_history},
        )

    # -------------------------------------------------------------------------
    # Private Helpers (Strictly at Bottom)
    # -------------------------------------------------------------------------

    def _build_fastapi_app(self) -> FastAPI:
        """Constructs the FastAPI application, registers exception handlers, and mounts routes."""
        fastapi_app = FastAPI(
            title="AgriStack DBT Core — Sovereign Zero-Trust DPI Orchestrator",
            version="0.1.0",
        )
        fastapi_app.add_exception_handler(
            ValidationError,
            validation_exception_handler,  # type: ignore[arg-type]
        )

        fastapi_app.add_api_route(_HEALTH_PATH, self.handle_health_check, methods=["GET"])
        fastapi_app.add_api_route(
            _WHATSAPP_WEBHOOK_PATH, self.handle_whatsapp_webhook, methods=["POST"]
        )
        fastapi_app.add_api_route(_IVR_WEBHOOK_PATH, self.handle_ivr_webhook, methods=["POST"])
        fastapi_app.add_api_route(_USSD_WEBHOOK_PATH, self.handle_ussd_webhook, methods=["POST"])
        fastapi_app.add_api_route(_SMS_WEBHOOK_PATH, self.handle_sms_webhook, methods=["POST"])
        fastapi_app.add_api_route(
            _PAYMENT_CALLBACK_WEBHOOK_PATH,
            self.handle_payment_callback,
            methods=["POST"],
        )
        fastapi_app.add_api_route(
            _G2P_ON_DISBURSE_WEBHOOK_PATH,
            self.handle_g2p_on_disburse_webhook,
            methods=["POST"],
        )
        fastapi_app.add_api_route(
            _CASEWORKER_LIST_PATH, self.handle_list_staged_cases, methods=["GET"]
        )
        fastapi_app.add_api_route(
            _CASEWORKER_REVIEW_PATH, self.handle_caseworker_review, methods=["POST"]
        )
        fastapi_app.add_api_route(_AUDIT_FUNNEL_PATH, self.handle_audit_funnel, methods=["GET"])
        fastapi_app.add_api_route(_AUDIT_HISTORY_PATH, self.handle_audit_history, methods=["GET"])
        return fastapi_app

    def _reconcile_and_build_callback_response(
        self, callback_payload: DisbursementCallbackPayload
    ) -> JSONResponse:
        """Reconciles a validated DisbursementCallbackPayload in the ledger and formats response."""
        was_reconciled = self._ledger_persistence_service.reconcile_disbursement_callback(
            callback_payload
        )
        if not was_reconciled:
            return self._build_problem_response(
                http_status=HTTPStatus.CONFLICT,
                error_type="https://api.agristack.gov.in/errors/payment-reconciliation-failed",
                title="Payment Callback Reconciliation Failed",
                detail=(
                    f"Disbursement transaction '{callback_payload.disbursement_txn_id}' was not "
                    "found or violated monotonic state progression."
                ),
            )

        return JSONResponse(
            status_code=HTTPStatus.OK,
            content={
                "disbursement_txn_id": callback_payload.disbursement_txn_id,
                "disbursement_status": callback_payload.disbursement_status,
                "bank_reference_id": callback_payload.bank_reference_id,
                "reconciled": True,
            },
        )

    def _verify_bearer_token_if_configured(self, incoming_request: Request) -> JSONResponse | None:
        """Verifies Authorization Bearer token when carrier_bearer_token is configured."""
        if self._carrier_bearer_token is None:
            return None

        auth_header = incoming_request.headers.get(_AUTHORIZATION_HEADER_NAME)
        is_valid_token = CarrierAuthValidator.validate_carrier_bearer_token(
            auth_header=auth_header,
            expected_token=self._carrier_bearer_token,
        )
        if not is_valid_token:
            return self._build_unauthorized_response(
                "Invalid or missing Carrier Bearer token in Authorization header."
            )
        return None

    async def _execute_ingress_pipeline(
        self,
        incoming_request: Request,
        validated_payload: (
            WhatsAppIngressPayload | IvrIngressPayload | UssdIngressPayload | SmsIngressPayload
        ),
    ) -> JSONResponse:
        """Runs the Layer 2-4 intake pipeline and maps security errors to RFC 7807 responses."""
        language_locale = self._resolve_language_locale(incoming_request)
        attempt_count = self._resolve_attempt_count(
            incoming_request=incoming_request,
            session_id=str(validated_payload.session_id),
        )

        try:
            intake_result = await self._public_agent_api.process_raw_ingress(
                raw_payload=validated_payload,
                language_locale=language_locale,
                attempt_count=attempt_count,
            )
        except PermissionError as rate_limit_error:
            return self._build_problem_response(
                http_status=HTTPStatus.TOO_MANY_REQUESTS,
                error_type="https://api.agristack.gov.in/errors/rate-limit-exceeded",
                title="Rate Limit Exceeded",
                detail=str(rate_limit_error),
            )
        except ValueError as security_error:
            return self._build_problem_response(
                http_status=HTTPStatus.BAD_REQUEST,
                error_type="https://api.agristack.gov.in/errors/security-validation-failed",
                title="Security or Intake Validation Failed",
                detail=str(security_error),
            )

        return JSONResponse(
            status_code=HTTPStatus.OK,
            content=self._serialize_intake_result(intake_result),
        )

    def _persist_caseworker_review_decision(
        self,
        staged_case: CaseworkerCaseReviewPayload,
        application_status: ApplicationStatus,
        review_outcome: CaseworkerReviewOutcomePayload,
    ) -> None:
        """Updates application_governance_ledger with officer review outcome and fires trigger."""
        eligibility_status = EligibilityStatus.REQUIRES_REVIEW
        if review_outcome.governance_action == GovernanceAction.MANUAL_APPROVE:
            eligibility_status = EligibilityStatus.ELIGIBLE
        if review_outcome.governance_action == GovernanceAction.MANUAL_REJECT:
            eligibility_status = EligibilityStatus.INELIGIBLE

        metadata: dict[str, object] = {
            "reviewer_id": review_outcome.reviewer_id,
            "escalation_case_id": review_outcome.escalation_case_id,
            "review_notes": review_outcome.review_notes,
        }
        if review_outcome.approved_amount is not None:
            metadata["approval_amount"] = review_outcome.approved_amount
        if review_outcome.rejection_reason is not None:
            metadata["rejection_reason"] = str(review_outcome.rejection_reason)

        self._ledger_persistence_service.record_governance_decision(
            claim_id=f"claim-{staged_case.session_id}",
            session_id=staged_case.session_id,
            payload_id=staged_case.payload_id,
            tokenized_identity_hash=staged_case.tokenized_citizen_id,
            application_status=str(application_status),
            claimant_eligibility_status=str(eligibility_status),
            governance_action=str(review_outcome.governance_action),
            evaluated_at=review_outcome.reviewed_at.isoformat(),
            governance_metadata=metadata,
        )

    @staticmethod
    async def _parse_json_mapping(incoming_request: Request) -> Mapping[str, object]:
        """Parses HTTP request JSON body into a dictionary mapping."""
        parsed_body: Any = await incoming_request.json()
        if not isinstance(parsed_body, Mapping):
            return {}
        return parsed_body

    @staticmethod
    def _resolve_language_locale(incoming_request: Request) -> LanguageLocale:
        """Extracts optional X-Language-Locale header or defaults to Hindi ('hi-IN')."""
        raw_locale = incoming_request.headers.get(_LANGUAGE_HEADER_NAME)
        if raw_locale is None:
            return LanguageLocale.HINDI
        try:
            return LanguageLocale(raw_locale.strip())
        except ValueError:
            return LanguageLocale.HINDI

    def _resolve_attempt_count(self, incoming_request: Request, session_id: str) -> int:
        """Resolves attempt count from X-Attempt-Count header or session extraction history."""
        raw_attempt = incoming_request.headers.get(_ATTEMPT_HEADER_NAME)
        if raw_attempt is None:
            return self._ledger_persistence_service.fetch_next_attempt_count(session_id)
        try:
            parsed_attempt = int(raw_attempt.strip())
        except ValueError:
            return 1
        return max(1, parsed_attempt)

    @staticmethod
    def _serialize_intake_result(intake_result: PublicAgentIntakeResult) -> dict[str, object]:
        """Serializes PublicAgentIntakeResult into a JSON-compatible dictionary."""
        orchestration_outcome = intake_result.orchestration_result
        return {
            "session_id": intake_result.session_id,
            "channel_type": intake_result.channel_type,
            "tokenized_citizen_id": intake_result.intake_payload.tokenized_citizen_id,
            "requires_reprompt": orchestration_outcome.requires_reprompt,
            "reprompt_message": orchestration_outcome.reprompt_message,
            "governance_outcome": orchestration_outcome.governance_outcome.model_dump(mode="json"),
            "transmission_ack": intake_result.transmission_ack.model_dump(mode="json"),
        }

    @classmethod
    def _build_unauthorized_response(cls, detail: str) -> JSONResponse:
        """Constructs an RFC 7807 401 Unauthorized JSONResponse."""
        return cls._build_problem_response(
            http_status=HTTPStatus.UNAUTHORIZED,
            error_type="https://api.agristack.gov.in/errors/unauthorized-webhook",
            title="Unauthorized Carrier Webhook",
            detail=detail,
        )

    @staticmethod
    def _build_problem_response(
        http_status: HTTPStatus,
        error_type: str,
        title: str,
        detail: str,
    ) -> JSONResponse:
        """Constructs a standardized RFC 7807 Problem Details JSONResponse."""
        return JSONResponse(
            status_code=http_status,
            content={
                "type": error_type,
                "title": title,
                "status": int(http_status),
                "detail": detail,
            },
        )


def create_public_agent_http_app(
    whatsapp_app_secret: str | None = None,
    carrier_bearer_token: str | None = None,
    database_url: str | None = None,
) -> FastAPI:
    """Factory function constructing the FastAPI application for Uvicorn ASGI workers."""
    persistence_service = LedgerPersistenceService(database_url=database_url)
    server = PublicAgentHttpServer(
        ledger_persistence_service=persistence_service,
        whatsapp_app_secret=whatsapp_app_secret,
        carrier_bearer_token=carrier_bearer_token,
    )
    return server.app
