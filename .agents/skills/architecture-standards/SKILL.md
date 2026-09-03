---
name: architecture-standards
description: 4-Layer Zero-Trust architecture specification, directory structure, subpackage taxonomy, and boundary separation for AgriStack core development. Use whenever organizing files, defining package structures, adding new microservice components, or designing cross-layer boundaries.
---

# AgriStack 4-Layer Zero-Trust Architecture Standards

This document defines the system topology, package layout, layer responsibilities, and architectural boundaries for AgriStack.

---

## 1. 4-Layer System Topology

The platform is structured into four strictly decoupled architectural layers:

```
[ Citizen (WhatsApp / IVR / USSD / SMS) ]
                  │
                  ▼
┌────────────────────────────────────────────────────────┐
│ Layer 1: Channel Edge Connectors                       │
│ - WhatsApp Webhook (Meta API / BSPs)                   │
│ - IVR Voice Telephony (SIP trunk audio streams)        │
│ - USSD Cellular Signaling (SS7 / SIGTRAN menus)        │
│ - Transactional SMS (TRAI DLT gateways)                │
└────────────────────────┬───────────────────────────────┘
                         │ Raw Ingress Payloads
                         ▼
┌────────────────────────────────────────────────────────┐
│ Layer 2: API Gateway & Perimeter Security              │
│ - Timing-safe HMAC webhook signature & bearer auth     │
│ - Token-bucket rate limiting (DoS protection)          │
│ - In-memory SHA-256 HMAC zero-PII identity tokenization│
│ - In-memory PII cleartext sanitization & purge guards  │
│ - Adversarial prompt injection pre-inspection          │
│ - Payload canonicalization (Raw -> Standardized Intake)│
└────────────────────────┬───────────────────────────────┘
                         │ PublicAgentStandardizedIntakePayload (Zero-PII)
                         ▼
┌────────────────────────────────────────────────────────┐
│ Layer 3: Public Agent Intake Gateway                   │
│ - Modality handling (Bhashini speech-to-text ASR)      │
│ - Fast-path structured bypass (DTMF/USSD)              │
│ - Sovereign SLM domain entity extraction               │
└────────────────────────┬───────────────────────────────┘
                         │ ExtractedEntityPayload (Structured Domain Contract)
                         ▼
┌────────────────────────────────────────────────────────┐
│ Layer 4: Orchestrator Brain & Governance Engine        │
│ - Mandatory completeness & reprompt matrix (Gate 2)    │
│ - Deterministic policy rules matrix (Approve/Review/Reject) (Gate 3)│
│ - Post-decision payment dispatch & caseworker staging  │
└───────────┬────────────────────────────────┬───────────┘
            │                                │
            ▼                                ▼
┌────────────────────────┐      ┌────────────────────────┐
│ External AI Blocks     │      │ Authoritative DPI Rails│
│ - Bhashini ASR/NMT/TTS │      │ - Identity Verification│
│ - Sovereign SLM Engine │      │ - AgriStack Land/Crops │
│                        │      │ - OpenSPP Caseworker   │
│                        │      │ - NPCI/PFMS Payout Rail│
└────────────────────────┘      └────────────────────────┘
```

---

## 2. Directory Layout & Package Structure

```
src/
├── connectors/                      # Layer 1 Channel Edge Connectors
│   ├── whatsapp_connector.py        # WhatsApp text/audio webhook connector
│   ├── ivr_connector.py             # SIP telephony voice stream connector
│   ├── ussd_connector.py            # SS7/SIGTRAN USSD menu connector
│   └── sms_connector.py             # DLT transactional SMS connector
├── gateway/                         # Layer 2 Gateway & Perimeter Security
│   ├── carrier_auth_validator.py    # Webhook HMAC signature & Bearer token verification
│   ├── zero_trust_identity_tokenizer.py # RAM-only SHA-256 HMAC Zero-PII identity tokenization
│   ├── pii_purge_guard.py           # In-memory Zero-PII sanitizer & assertion sentinel
│   ├── adversarial_prompt_firewall.py # Adversarial prompt injection & override defense
│   ├── payload_canonicalizer.py     # Ingress payload canonicalization (Raw -> StandardizedIntake)
│   ├── rate_limiter.py              # Token bucket rate limiter & quota guard
│   └── ingestion_firewall.py        # Unified Layer 2 perimeter firewall facade
├── public_agent/                    # Layer 3 Public Agent Intake Gateway Surface
│   ├── public_agent_api.py          # Public Agent Gateway API Surface
│   └── intake_entity_extractor.py   # Modality handling & SLM domain entity extractor
├── orchestrator/                    # Layer 4 Orchestrator Brain & Governance Engine
│   ├── claim_adjudicator.py         # Gate 3 decision matrix & threshold adjudication
│   ├── claim_orchestrator.py        # End-to-end claim governance & policy orchestration
│   └── case_management_service.py   # Layer 4 internal caseworker queue & review service
├── services/                        # External DPI Registries & AI Adapter Services ONLY
│   ├── ai/                          # Foundational & sovereign AI model clients
│   │   ├── ai_mock_fixtures.py
│   │   ├── bhashini_service.py
│   │   └── slm_extractor.py
│   ├── delivery/                    # Outbound multichannel delivery service
│   │   └── multichannel_notification_service.py
│   └── dpi/                         # Authoritative sovereign DPI clients
│       ├── dpi_mock_fixtures.py
│       ├── agri_registry_service.py
│       ├── identity_verification_service.py
│       ├── payment_rail_service.py
│       └── social_registry_service.py # External OpenSPP registry boundary client
├── errors/                          # RFC 7807 problem details exception handlers
│   └── validation_exception_handler.py
└── data_models/                     # Domain data contracts & Pydantic validation schemas
    ├── common/                      # Shared foundational primitives & type annotations
    ├── raw_ingress/                 # Layer 1 -> Layer 2 carrier raw ingress payloads
    ├── public_agent/                # Layer 2 -> Layer 3 normalized intake contracts
    ├── governance/                  # Layer 4 governance models & extraction payloads
    ├── caseworker/                  # Caseworker portal review staging & outcome models
    ├── delivery/                    # Layer 4 outbound multichannel delivery contracts
    └── disbursement/                # Financial clearing callback models
```

---

## 3. Separation of Concerns & Boundary Invariants

### 3.1 External Dependencies Isolation (`src/services/`)
* **Strict Encapsulation**: Third-party APIs, sovereign foundational AI blocks, and government registry clients reside strictly in `src/services/ai/` and `src/services/dpi/`.
* **No Leaking into Core Domain**: Layer 4 orchestrators and state machines interact with registries exclusively through service client interfaces.
* **Service Adapter Transport Decoupling (`src/services/http_transport.py`)**:
  * Public service methods must only handle domain-level concerns: validating domain input arguments and validating domain response schemas against data contracts.
  * Low-level network transport (HTTP connection pooling, Bearer authorization, timeouts, base URL normalization, HTTP status-code triage, and domain exception mapping) is standardized in `ServiceHttpTransport` (`src/services/http_transport.py`). Live service adapters initialize `self._transport = ServiceHttpTransport(http_client, api_key, ServiceTransportConfig(service_name=..., service_title=..., timeout_seconds=...), base_url=endpoint_url)` and delegate JSON dispatches via `await self._transport.post_json(PATH_CONSTANT, payload, context_label=...)` using module-level static endpoint path constants (e.g. `_DISBURSE_PATH = "/v1/payments/disburse"`).
  * **Incorrect**: Inlining `await client.post(...)`, headers, ad-hoc `f"{self._endpoint_url}/..."` string formatting, or duplicating private `_post_json` transport implementations across individual service adapter classes.
  * **Correct**: Service adapter instantiates `ServiceHttpTransport(..., base_url=...)` and delegates request dispatch to `await self._transport.post_json(_PATH_CONSTANT, ...)`.

### 3.2 Categorized Domain Schema Namespacing (`src/data_models/`)
* Subpackages within `data_models/` mirror functional lifecycle stages (`raw_ingress`, `public_agent`, `governance`, `caseworker`, `delivery`, `disbursement`).
* File names represent the schema entity (e.g. `claim_evaluation_payload.py`), while class names include domain namespaces (e.g. `ClaimEvaluationPayload`) to avoid symbol collisions when imported across boundaries.

### 3.3 Architecture Decision Record (ADR) Traceability
* Every module and domain schema must reference its foundational ADR `.md` file in `decisions/` in its module docstring:

```python
"""Layer 4 Governance Engine: Decision Matrix Router.

See: decisions/step3.3_layer4_orchestrator_brain.md (Section 4: Gate 3 Matrix)
See: decisions/step2.2_governance_flows_and_state_transitions.md (Section 3.1 & 4.1)
See: decisions/step2.0_canonical_domain_schemas.md (Section 4.3)
"""
```
