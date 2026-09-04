"""Layer 4 Governance Engine: Claim Evaluation Input Context Schema.

See: decisions/step3.3_layer4_orchestrator_brain.md (Section 4: Gate 3 Matrix)
See: decisions/step2.2_governance_flows_and_state_transitions.md (Section 3.1 & 4.1)
See: decisions/step2.0_canonical_domain_schemas.md (Section 4.3)
"""

from pydantic import Field

from src.data_models.common import (
    CropSeason,
    ExtractionPayloadId,
    HmacCitizenToken,
    SessionId,
    StrictBaseModel,
)
from src.data_models.governance.extracted_entity_payload import ExtractedEntityPayload

_DEFAULT_ACTIVE_SEASON: str = "KHARIF-2026"

__all__ = ["ClaimEvaluationPayload"]


class ClaimEvaluationPayload(StrictBaseModel):
    """Data model representing the input context for governance claim eligibility evaluation.

    Encapsulates citizen parameters, extracted entities, active season, and approved payout
    ledger records for Gate 3 rules matrix evaluation.

    Attributes:
        session_id: Primary session tracking identifier.
        payload_id: Extraction payload tracking identifier.
        tokenized_citizen_id: 64-character SHA-256 HMAC citizen identity token.
        extracted_payload: Extracted entity payload containing intent and domain entities.
        active_season: Agricultural crop season identifier (e.g. 'KHARIF-2026').
        approved_payouts_ledger: Set of (tokenized_citizen_id, season) tuples tracking prior
            disbursements.

    See: decisions/step2.2_governance_flows_and_state_transitions.md (Section 3.1 & 4.1)
    """

    session_id: SessionId
    payload_id: ExtractionPayloadId
    tokenized_citizen_id: HmacCitizenToken
    extracted_payload: ExtractedEntityPayload
    active_season: CropSeason = _DEFAULT_ACTIVE_SEASON
    approved_payouts_ledger: set[tuple[str, str]] = Field(
        default_factory=set,
        description=(
            "In-memory ledger of approved (citizen_token, season) payouts for "
            "anti-double-dipping validation"
        ),
    )
