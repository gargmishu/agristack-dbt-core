"""Layer 3 Public Agent Gateway API (Layer 3 Intake Surface).

Receives canonical, zero-PII standardized intake payloads from the Layer 2 Security
Gateway, evaluates intake structure and routing requirements, and prepares validated
payloads for Layer 4 orchestration execution.

Why decouple Layer 3 Public Agent Gateway from Layer 2 Security Gateway?
1. Separation of Concerns: Layer 2 handles transport-level security (HMAC webhook signatures,
   Bearer tokens, token-bucket rate limiting, and in-memory PII tokenization into RAM).
2. Domain Intake Routing: Layer 3 provides the public API surface for event intake and
   structural intent evaluation (fast-path DTMF/menu bypass vs. SLM/NLU entity extraction)
   before submitting to Layer 4 governance orchestration.

See: decisions/step3.4_layer3_intake_gateway_and_connectors.md
See: decisions/step2.0_canonical_domain_schemas.md (Section 4.2)
See: decisions/step3.3_layer4_orchestrator_brain.md
"""

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.data_models.common import (
    ChannelType,
    DomainEntityKey,
    GovernanceAction,
    LanguageLocale,
    SessionId,
)
from src.data_models.notification import (
    NotificationDispatchResult,
    NotificationRequestPayload,
    TransmissionAck,
)
from src.data_models.public_agent import PublicAgentStandardizedIntakePayload
from src.data_models.raw_ingress import (
    IvrIngressPayload,
    SmsIngressPayload,
    UssdIngressPayload,
    WhatsAppIngressPayload,
)
from src.gateway.ingestion_firewall import IngestionFirewall
from src.orchestrator.claim_orchestrator import ClaimOrchestrator, OrchestrationExecutionResult
from src.public_agent.intake_payload_evaluator import (
    IntakeEvaluationResult,
    IntakePayloadEvaluator,
)
from src.services.notification.multichannel_notification_service import (
    MultichannelNotificationService,
)

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PublicAgentIntakeResult:
    """Consolidated end-to-end outcome from Public Agent intake and orchestration processing.

    Attributes:
        intake_payload: Normalized zero-PII standardized intake payload.
        evaluation_result: Intake structure and modality evaluation result.
        orchestration_result: Layer 4 claim orchestration execution outcome.
        dispatch_result: Outbound notification dispatch result.
    """

    intake_payload: PublicAgentStandardizedIntakePayload
    evaluation_result: IntakeEvaluationResult
    orchestration_result: OrchestrationExecutionResult
    dispatch_result: NotificationDispatchResult

    @property
    def session_id(self) -> SessionId:
        """Primary session tracking identifier."""
        return self.intake_payload.session_id

    @property
    def channel_type(self) -> ChannelType:
        """Ingress channel communication protocol."""
        return self.intake_payload.channel_type

    @property
    def transmission_ack(self) -> TransmissionAck:
        """Authoritative carrier transmission acknowledgment receipt."""
        return self.dispatch_result.transmission_ack


class PublicAgentApi:
    """Public Agent Gateway API providing intake submission, validation, and full execution.

    Serves as the primary Layer 3 entrypoint that bridges Layer 2 perimeter security,
    Layer 4 claim orchestration, and Outbound Multi-Channel Delivery.

    Routing Classification:
    - Structured Inputs (DTMF / USSD menu choices): Evaluates fast-path bypass
      (`requires_nlu_extraction=False`) to avoid GPU NLU latency and eliminate AI hallucinations.
    - Unstructured Inputs (Free text / Voice audio): Routes to NLU extraction
      (`requires_nlu_extraction=True`) for ASR speech transcription and SLM entity parsing.
    """

    def __init__(
        self,
        evaluator: IntakePayloadEvaluator | None = None,
        orchestrator: ClaimOrchestrator | None = None,
        delivery_service: MultichannelNotificationService | None = None,
        firewall: IngestionFirewall | None = None,
    ) -> None:
        """Initializes the public agent gateway with required services.

        Args:
            evaluator: Optional intake evaluator instance (defaults to standard evaluator).
            orchestrator: Optional Layer 4 claim orchestrator (defaults to ClaimOrchestrator).
            delivery_service: Optional outbound notification delivery engine (defaults to
                MultichannelNotificationService).
            firewall: Optional Layer 2 perimeter security firewall (defaults to IngestionFirewall).
        """
        self._evaluator = evaluator or IntakePayloadEvaluator()
        self._orchestrator = orchestrator or ClaimOrchestrator()
        self._delivery_service = delivery_service or MultichannelNotificationService()
        self._firewall = firewall or IngestionFirewall.from_env()

    # -------------------------------------------------------------------------
    # Primary Public Workflow Entrypoint
    # -------------------------------------------------------------------------

    async def process_raw_ingress(
        self,
        raw_payload: (
            WhatsAppIngressPayload | IvrIngressPayload | UssdIngressPayload | SmsIngressPayload
        ),
        language_locale: LanguageLocale = LanguageLocale.HINDI,
        attempt_count: int = 1,
    ) -> PublicAgentIntakeResult:
        """Executes full end-to-end flow from raw carrier webhook to citizen transmission receipt.

        Args:
            raw_payload: Typed carrier ingress payload (WhatsApp, IVR, USSD, or SMS).
            language_locale: Target BCP-47 language locale (default: 'hi-IN').
            attempt_count: Current conversation turn attempt number.

        Returns:
            PublicAgentIntakeResult containing full end-to-end outcome and transmission receipt.

        Raises:
            PermissionError: If rate limit is exceeded.
            ValueError: If authentication fails, PII check fails, or payload is invalid.
        """
        intake_payload = self._firewall.process_ingress(
            payload=raw_payload,
            language_locale=language_locale,
        )

        return await self._process_claim_intake(
            payload=intake_payload,
            attempt_count=attempt_count,
        )

    # -------------------------------------------------------------------------
    # Private Helpers (Strictly at Bottom)
    # -------------------------------------------------------------------------

    async def _process_claim_intake(
        self,
        payload: PublicAgentStandardizedIntakePayload,
        attempt_count: int = 1,
    ) -> PublicAgentIntakeResult:
        """Executes internal claim processing pipeline from intake payload to outbound receipt.

        Args:
            payload: Normalized zero-PII standardized intake payload from Layer 2 firewall.
            attempt_count: Current conversation turn attempt number for reprompt bounds.

        Returns:
            PublicAgentIntakeResult containing the full execution lifecycle telemetry and receipt.

        Raises:
            ValueError: If payload structure or downstream execution fails validation constraints.
        """
        eval_result = await self._submit_payload(payload)

        orchestration_result = await self._orchestrator.execute_orchestration_cycle(
            intake=payload,
            attempt_count=attempt_count,
        )

        notification_request = self._build_notification_request(
            intake=payload,
            orch_result=orchestration_result,
        )

        dispatch_result = await self._delivery_service.dispatch_notification(notification_request)

        return PublicAgentIntakeResult(
            intake_payload=payload,
            evaluation_result=eval_result,
            orchestration_result=orchestration_result,
            dispatch_result=dispatch_result,
        )

    async def _submit_payload(
        self, payload: PublicAgentStandardizedIntakePayload
    ) -> IntakeEvaluationResult:
        """Evaluates intake payload structure and returns verified routing evaluation outcome.

        Performs content sanity checks and determines whether the incoming interaction requires
        natural language processing (SLM extraction) or can follow a deterministic structured path.

        Args:
            payload: Validated PublicAgentStandardizedIntakePayload from Layer 2 Gateway.

        Returns:
            IntakeEvaluationResult: Structural evaluation outcome containing `is_valid`,
            `requires_nlu_extraction`, and descriptive status notes.

        Raises:
            ValueError: If payload fails structural validation, contains empty or whitespace-only
                content, or violates channel-structure compatibility constraints.
        """
        evaluation_result = self._evaluator.evaluate_payload(payload)
        if not evaluation_result.is_valid:
            logger.warning(
                "PublicAgentApi rejected payload for session=%s: %s",
                payload.session_id,
                evaluation_result.evaluation_message,
            )
            raise ValueError(f"Invalid intake payload: {evaluation_result.evaluation_message}")

        logger.info(
            "PublicAgentApi accepted payload for session=%s, channel=%s, nlu_required=%s",
            payload.session_id,
            payload.channel_type,
            evaluation_result.requires_nlu_extraction,
        )
        return evaluation_result

    @staticmethod
    def _build_notification_request(
        intake: PublicAgentStandardizedIntakePayload,
        orch_result: OrchestrationExecutionResult,
    ) -> NotificationRequestPayload:
        """Translates orchestration outcome into an outbound notification request payload.

        Args:
            intake: Active standardized intake payload.
            orch_result: Outcome returned by ClaimOrchestrator.

        Returns:
            Validated NotificationRequestPayload.
        """
        outcome = orch_result.governance_outcome
        missing_entity: DomainEntityKey | None = None

        if outcome.governance_action == GovernanceAction.REQUEST_MORE_INFO:
            missing_entity = DomainEntityKey.DISTRICT

        return NotificationRequestPayload(
            session_id=intake.session_id,
            channel_type=intake.channel_type,
            governance_action=outcome.governance_action,
            language_locale=intake.language_locale,
            disbursement_txn_id=outcome.disbursement_txn_id,
            escalation_case_id=outcome.escalation_case_id,
            rejection_reason=outcome.rejection_reason,
            missing_entity=missing_entity,
        )
