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

from src.data_models.common import (
    ChannelType,
    DomainEntityKey,
    GovernanceAction,
    LanguageLocale,
    SessionId,
)
from src.data_models.notification import (
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
from src.public_agent.intake_entity_extractor import IntakeEntityExtractor
from src.services.notification.multichannel_notification_service import (
    MultichannelNotificationService,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PublicAgentIntakeResult:
    """Consolidated end-to-end outcome from Public Agent intake and orchestration processing.

    Attributes:
        intake_payload: Normalized zero-PII standardized intake payload.
        orchestration_result: Layer 4 claim orchestration execution outcome.
        transmission_ack: Authoritative carrier transmission acknowledgment receipt.
    """

    intake_payload: PublicAgentStandardizedIntakePayload
    orchestration_result: OrchestrationExecutionResult
    transmission_ack: TransmissionAck

    @property
    def session_id(self) -> SessionId:
        """Primary session tracking identifier."""
        return self.intake_payload.session_id

    @property
    def channel_type(self) -> ChannelType:
        """Ingress channel communication protocol."""
        return self.intake_payload.channel_type


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
        extractor: IntakeEntityExtractor | None = None,
        orchestrator: ClaimOrchestrator | None = None,
        delivery_service: MultichannelNotificationService | None = None,
        firewall: IngestionFirewall | None = None,
    ) -> None:
        """Initializes the public agent gateway with required services.

        Args:
            extractor: Optional Layer 3 entity extractor (defaults to IntakeEntityExtractor).
            orchestrator: Optional Layer 4 claim orchestrator (defaults to ClaimOrchestrator).
            delivery_service: Optional outbound notification delivery engine (defaults to
                MultichannelNotificationService).
            firewall: Optional Layer 2 perimeter security firewall (defaults to IngestionFirewall).
        """
        self._extractor = extractor or IntakeEntityExtractor()
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
        # 1. Layer 2: Ingress Firewall, Tokenization & Canonicalization
        intake_payload = self._firewall.process_ingress(
            payload=raw_payload,
            language_locale=language_locale,
        )

        # 2. Layer 3: Modality Handling & SLM Domain Entity Extraction
        extracted_entities = await self._extractor.extract_entities(intake_payload)

        # 3. Layer 4: Governance Brain & Policy Adjudication Pipeline
        orchestration_result = await self._orchestrator.execute_orchestration_cycle(
            intake=intake_payload,
            extracted_entities=extracted_entities,
            attempt_count=attempt_count,
        )

        # 4. Delivery: Outbound Notification Preparation & Carrier Dispatch
        notification_request = self._build_notification_request(
            intake=intake_payload,
            orchestration_result=orchestration_result,
        )
        transmission_ack = await self._delivery_service.dispatch_notification(notification_request)

        return PublicAgentIntakeResult(
            intake_payload=intake_payload,
            orchestration_result=orchestration_result,
            transmission_ack=transmission_ack,
        )

    # -------------------------------------------------------------------------
    # Private Helpers (Strictly at Bottom)
    # -------------------------------------------------------------------------

    @staticmethod
    def _build_notification_request(
        intake: PublicAgentStandardizedIntakePayload,
        orchestration_result: OrchestrationExecutionResult,
    ) -> NotificationRequestPayload:
        """Translates orchestration outcome into an outbound notification request payload.

        Args:
            intake: Active standardized intake payload.
            orchestration_result: Outcome returned by ClaimOrchestrator.

        Returns:
            Validated NotificationRequestPayload.
        """
        outcome = orchestration_result.governance_outcome
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
