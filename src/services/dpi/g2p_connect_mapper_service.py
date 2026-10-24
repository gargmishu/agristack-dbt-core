"""Authoritative DPI Interoperability: G2P Connect (DCI) v1.0.0 Envelope Mapper Service.

Translates internal Zero-Trust governance outcomes and registry verification requests
into signed G2P Connect (Digital Convergence Initiative) v1.0.0 envelopes compatible
with OpenG2P, OpenSPP, and PFMS payment bridges, and verifies inbound `on-disburse`
asynchronous callbacks using timing-safe HMAC-SHA256 verification.

Why timing-safe HMAC-SHA256 signing and Zero-PII assertions?
1. Enforces DPG Indicator 6 & 8 standards interoperability while guaranteeing that
   zero cleartext PII ever enters a G2P Connect wire envelope (`PiiPurgeGuard.assert_zero_pii`).
2. Uses `secrets.compare_digest` when verifying inbound `on-disburse` payment bridge
   callbacks to prevent timing side-channel forgery attacks.

See: decisions/step2.0_canonical_domain_schemas.md (Section 4.5)
See: decisions/step2.3_governance_flows_and_state_transitions.md (Section 4.4)
See: docs/dpg_standard_compliance.md (Indicator 8: Adherence to Standards & Best Practices)
"""

import hashlib
import hmac
import secrets
from datetime import UTC, datetime
from typing import Final, Self

from src.config.channel_settings import get_pepper_secret
from src.data_models.common import APPROVE_GOVERNANCE_ACTIONS
from src.data_models.disbursement import (
    DisbursementCallbackPayload,
    G2pConnectAction,
    G2pConnectDisbursementEnvelope,
    G2pConnectDisbursementInstruction,
    G2pConnectHeader,
    G2pConnectOnDisbursePayload,
    G2pConnectOnSearchPayload,
    G2pConnectRegistrySearchEnvelope,
)
from src.data_models.governance import GovernanceOutcomePayload
from src.gateway.pii_purge_guard import PiiPurgeGuard

DEFAULT_G2P_SENDER_ID: Final[str] = "agristack-dbt-core.gov.in"
DEFAULT_G2P_REGISTRY_RECEIVER_ID: Final[str] = "farmer-registry.agristack.gov.in"
DEFAULT_G2P_PAYMENT_RECEIVER_ID: Final[str] = "payment-bridge.openg2p.gov.in"
_G2P_PROTOCOL_VERSION: Final[str] = "1.0.0"

__all__ = [
    "DEFAULT_G2P_PAYMENT_RECEIVER_ID",
    "DEFAULT_G2P_REGISTRY_RECEIVER_ID",
    "DEFAULT_G2P_SENDER_ID",
    "G2pConnectMapperService",
]


class G2pConnectMapperService:
    """Standards mapper for G2P Connect (DCI) v1.0.0 registry and disbursement envelopes.

    Constructs cryptographically signed `search` and `disburse` envelopes and validates
    inbound `on-search` and `on-disburse` callbacks.
    """

    def __init__(
        self,
        signing_key: str,
        sender_id: str = DEFAULT_G2P_SENDER_ID,
        registry_receiver_id: str = DEFAULT_G2P_REGISTRY_RECEIVER_ID,
        payment_receiver_id: str = DEFAULT_G2P_PAYMENT_RECEIVER_ID,
    ) -> None:
        """Initializes G2P Connect mapper with fail-fast signing key validation."""
        if not signing_key or not signing_key.strip():
            raise ValueError("G2P Connect signing_key cannot be empty or whitespace-only")
        self._signing_key: bytes = signing_key.strip().encode("utf-8")
        self._sender_id: str = sender_id
        self._registry_receiver_id: str = registry_receiver_id
        self._payment_receiver_id: str = payment_receiver_id

    @classmethod
    def from_env(cls) -> Self:
        """Factory constructor building G2P Connect mapper from environment secret."""
        return cls(signing_key=get_pepper_secret())

    # -------------------------------------------------------------------------
    # Primary Public Workflow Entrypoints
    # -------------------------------------------------------------------------

    def build_registry_search_envelope(
        self,
        session_id: str,
        tokenized_citizen_id: str,
        land_record_id: str,
        crop_season: str = "KHARIF-2026",
    ) -> G2pConnectRegistrySearchEnvelope:
        """Builds a signed G2P Connect `search` envelope for Federated Farmer Registry lookup."""
        if PiiPurgeGuard.redact_all(land_record_id, session_id) != land_record_id:
            raise ValueError(
                "Zero-PII violation: cleartext phone or Aadhaar detected in land_record_id"
            )
        now = datetime.now(UTC)
        header = G2pConnectHeader(
            version=_G2P_PROTOCOL_VERSION,
            message_id=f"g2p-search-{session_id}",
            message_timestamp=now,
            action=G2pConnectAction.SEARCH,
            sender_id=self._sender_id,
            receiver_id=self._registry_receiver_id,
            total_count=1,
            is_message_encrypted=False,
        )
        signature = self._compute_envelope_signature(
            header=header,
            transaction_id=session_id,
            subject_reference=f"{tokenized_citizen_id}:{land_record_id}:{crop_season}",
        )
        return G2pConnectRegistrySearchEnvelope(
            signature=signature,
            header=header,
            transaction_id=session_id,
            tokenized_citizen_id=tokenized_citizen_id,
            land_record_id=land_record_id,
            crop_season=crop_season,
        )

    def verify_on_search_callback(
        self,
        callback_envelope: G2pConnectOnSearchPayload,
    ) -> G2pConnectOnSearchPayload:
        """Verifies a G2P Connect `on-search` farmer registry callback envelope."""
        if (
            PiiPurgeGuard.redact_all(
                callback_envelope.land_record_id,
                callback_envelope.transaction_id,
            )
            != callback_envelope.land_record_id
        ):
            raise ValueError(
                "Zero-PII violation: cleartext phone or Aadhaar detected in land_record_id"
            )
        subject_reference = (
            f"{callback_envelope.tokenized_citizen_id}:{callback_envelope.land_record_id}:"
            f"{callback_envelope.crop_season}:{callback_envelope.eligibility_status}"
        )
        is_valid = self.verify_envelope_signature(
            header=callback_envelope.header,
            transaction_id=callback_envelope.transaction_id,
            subject_reference=subject_reference,
            candidate_signature=callback_envelope.signature,
        )
        if not is_valid:
            raise ValueError("Invalid G2P Connect on-search envelope signature")

        return callback_envelope

    def build_disbursement_envelope(
        self,
        outcome: GovernanceOutcomePayload,
        tokenized_citizen_id: str,
        crop_season: str = "KHARIF-2026",
    ) -> G2pConnectDisbursementEnvelope:
        """Maps an approved outcome into a signed G2P Connect `disburse` envelope."""
        if outcome.governance_action not in APPROVE_GOVERNANCE_ACTIONS:
            raise ValueError(
                "Cannot build G2P Connect disbursement envelope for non-approved action "
                f"{outcome.governance_action}"
            )
        if not outcome.disbursement_txn_id:
            raise ValueError("Approved outcome is missing required disbursement_txn_id")

        instruction = G2pConnectDisbursementInstruction(
            reference_id=outcome.disbursement_txn_id,
            session_id=outcome.session_id,
            payload_id=outcome.payload_id,
            payee_fa_token=tokenized_citizen_id,
            scheme_code=crop_season,
            governance_action=outcome.governance_action,
            instructed_at=outcome.evaluated_at,
        )
        header = G2pConnectHeader(
            version=_G2P_PROTOCOL_VERSION,
            message_id=f"g2p-disb-{outcome.disbursement_txn_id}",
            message_timestamp=outcome.evaluated_at,
            action=G2pConnectAction.DISBURSE,
            sender_id=self._sender_id,
            receiver_id=self._payment_receiver_id,
            total_count=1,
            is_message_encrypted=False,
        )
        signature = self._compute_envelope_signature(
            header=header,
            transaction_id=outcome.disbursement_txn_id,
            subject_reference=f"{tokenized_citizen_id}:{crop_season}",
        )
        return G2pConnectDisbursementEnvelope(
            signature=signature,
            header=header,
            transaction_id=outcome.disbursement_txn_id,
            disbursement_instruction=instruction,
        )

    def parse_on_disburse_callback(
        self,
        callback_envelope: G2pConnectOnDisbursePayload,
    ) -> DisbursementCallbackPayload:
        """Verifies a G2P Connect `on-disburse` webhook into a DisbursementCallbackPayload."""
        subject_reference = (
            f"{callback_envelope.bank_reference_id}:{callback_envelope.disbursement_status}"
        )
        is_valid = self.verify_envelope_signature(
            header=callback_envelope.header,
            transaction_id=callback_envelope.transaction_id,
            subject_reference=subject_reference,
            candidate_signature=callback_envelope.signature,
        )
        if not is_valid:
            raise ValueError("Invalid G2P Connect on-disburse envelope signature")

        return DisbursementCallbackPayload(
            disbursement_txn_id=callback_envelope.transaction_id,
            bank_reference_id=callback_envelope.bank_reference_id,
            disbursement_status=callback_envelope.disbursement_status,
            cleared_at=callback_envelope.cleared_at,
            failure_reason_code=callback_envelope.failure_reason_code,
        )

    # -------------------------------------------------------------------------
    # Public Component & Stage Methods
    # -------------------------------------------------------------------------

    def verify_envelope_signature(
        self,
        header: G2pConnectHeader,
        transaction_id: str,
        subject_reference: str,
        candidate_signature: str,
    ) -> bool:
        """Performs timing-safe HMAC-SHA256 verification of a G2P Connect envelope signature."""
        expected_signature = self._compute_envelope_signature(
            header=header,
            transaction_id=transaction_id,
            subject_reference=subject_reference,
        )
        return secrets.compare_digest(expected_signature, candidate_signature)

    # -------------------------------------------------------------------------
    # Private Helpers (Strictly at Bottom)
    # -------------------------------------------------------------------------

    def _compute_envelope_signature(
        self,
        header: G2pConnectHeader,
        transaction_id: str,
        subject_reference: str,
    ) -> str:
        """Computes canonical 64-char hex HMAC-SHA256 digest over envelope header and subject."""
        canonical_signing_input = (
            f"{header.version}|{header.message_id}|{header.action}|"
            f"{header.sender_id}|{header.receiver_id}|{transaction_id}|{subject_reference}"
        )
        return hmac.new(
            self._signing_key,
            canonical_signing_input.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
