# End-to-End Architecture & Code Flow: Ingress to Governance Determination

This document maps the complete end-to-end code execution flow of **AgriStack DBT Core** — from an initial multi-channel citizen event (e.g., WhatsApp message, IVR voice call, USSD keypress) through the 4-layer Zero-Trust pipeline to the final governance determination and adaptive outbound delivery.

---

## 1. Master End-to-End Sequence Diagram

```mermaid
sequenceDiagram
    autonumber
    actor Citizen as 🌾 Citizen
    participant L1 as Layer 1: Edge Connectors<br/>(WhatsApp / IVR / USSD / SMS)
    participant L2 as Layer 2: Ingestion Firewall<br/>(CarrierAuth / RateLimiter / Tokenizer)
    participant L3 as Layer 3: Public Agent API<br/>(Intake & Structure Gate)
    participant L4_Orch as Layer 4: Claim Orchestrator<br/>(Gate 1 & Gate 2 Coordinator)
    participant AI as Foundational AI Blocks<br/>(Bhashini ASR/NMT & SLM)
    participant L4_Adj as Layer 4: Claim Adjudicator<br/>(Gate 3 Decision Matrix)
    participant DPI as Authoritative DPI Registries<br/>(MOSIP / AgriStack / OpenSPP / PFMS)
    participant L4_Case as Layer 4: Case Management<br/>(Escalation Queues & Audit)
    participant Deliv as Outbound Delivery Service<br/>(Multichannel Notification)

    %% Step 1: Channel Ingress
    Citizen->>L1: Inbound Event (WhatsApp Text/Audio, IVR SIP, USSD Menu)
    Note over L1: Validates raw carrier schema<br/>(WhatsAppIngressPayload)

    %% Step 2: Layer 2 Security Gateway
    L1->>L2: Submit Raw Ingress (process_ingress)
    Note over L2: 1. Verify HMAC Signature (CarrierAuthValidator)<br/>2. Rate Limit Quota Check (RateLimiter)<br/>3. Adversarial Prompt Scan (AdversarialPromptFirewall)<br/>4. SHA-256 HMAC Tokenization in RAM (ZeroTrustIdentityTokenizer)<br/>5. PII Purge Assertion (PiiPurgeGuard)
    L2-->>L1: Return (Standardized Intake Payload, is_adversarial)

    %% Step 3: Layer 3 Public Agent Gateway
    L1->>L3: Submit Standardized Payload (_submit_payload)
    Note over L3: Evaluates Structure Level & Routing<br/>(IntakePayloadEvaluator)
    L3-->>L1: Return Intake Evaluation Result

    %% Step 4: Layer 4 Claim Orchestration
    L1->>L4_Orch: Execute Cycle (execute_orchestration_cycle)
    
    %% Gate 1: Ingress Modality & SLM Entity Extraction
    rect rgb(240, 248, 255)
    Note over L4_Orch,AI: GATE 1: Modality Intake & Entity Extraction
    alt PayloadType == AUDIO
        L4_Orch->>AI: Transcribe & Translate (BhashiniService)
        AI-->>L4_Orch: Vernacular Text Transcript
        L4_Orch->>AI: Extract Entities (SlmExtractor)
        AI-->>L4_Orch: ExtractedEntityPayload
    else StructureLevel in (DTMF_SELECTION, MENU_SELECTION)
        Note over L4_Orch: Structured Fast-Path Bypass<br/>(Score = 1.0, bypasses GPU SLM)
    else PayloadType == TEXT (Free Text)
        L4_Orch->>AI: Extract Entities (SlmExtractor)
        AI-->>L4_Orch: ExtractedEntityPayload
    end
    end

    %% Gate 2: Mandatory Entity Completeness & Multi-Turn Reprompts
    rect rgb(255, 250, 240)
    Note over L4_Orch: GATE 2: Intent & Mandatory Entity Validation
    alt Missing Mandatory Entities (District, Crop, Survey) AND Attempts < 3
        L4_Orch-->>Citizen: Conversational Re-Prompt (REQUEST_MORE_INFO)
    end
    end

    %% Gate 3: Policy Adjudication Matrix
    rect rgb(240, 255, 240)
    Note over L4_Orch,L4_Adj: GATE 3: Governance Adjudication Matrix
    L4_Orch->>L4_Adj: Evaluate Claim (evaluate_claim)
    L4_Adj->>DPI: Verify Identity Token (IdentityVerificationService)
    DPI-->>L4_Adj: Identity Verified (True/False)
    L4_Adj->>DPI: Cross-Match Cadastral Land & Crop (AgriRegistryService)
    DPI-->>L4_Adj: Entitlement Verified (True/False)
    Note over L4_Adj: Anti-Double-Dipping Season Check
    L4_Adj-->>L4_Orch: GovernanceOutcomePayload
    end

    %% Post-Decision Execution
    rect rgb(255, 245, 245)
    Note over L4_Orch,DPI: Post-Decision Execution & Outbound Delivery
    alt Verdict == AUTO_APPROVE (Score >= 0.85 & Eligible & Unique)
        L4_Orch->>DPI: Dispatch Wire Payment (PaymentRailService)
        DPI-->>L4_Orch: DisbursementCallbackPayload (PENDING -> SUCCESS)
        L4_Orch->>Deliv: Dispatch Delivery Notification (Approval Card)
    else Verdict == ROUTE_FOR_MANUAL_REVIEW (Score < 0.85 / Flagged / Attempts >= 3)
        L4_Orch->>L4_Case: Stage Escalation Ticket (CaseManagementService)
        L4_Case-->>L4_Orch: Staged Case ID (SPP-CASE-YYYY-XXXXXX)
        L4_Orch->>Deliv: Dispatch Delivery Notification (Review Staged Card)
    else Verdict == AUTO_REJECT (Ineligible / Duplicate Active Claim)
        L4_Orch->>Deliv: Dispatch Delivery Notification (Rejection Reason + Helpline)
    end
    Deliv->>L1: Outbound Payload (WhatsApp / IVR / USSD / SMS)
    L1->>Citizen: Channel-Adapted Confirmation Receipt
    end
```

---

## 2. Detailed Execution Flow by Layer

### Phase 1: Edge Ingress & Layer 2 Perimeter Security

An inbound request arrives from a carrier network and is processed through perimeter security:

```mermaid
flowchart TD
    A["Inbound Request<br/>(e.g., WhatsApp Webhook)"] --> B["CarrierAuthValidator<br/>HMAC-SHA256 Signature Check"]
    B -- "Invalid / Missing Signature" --> B1["Fail Closed (HTTP 401/403)"]
    B -- "Valid Signature" --> C["RateLimiter<br/>Token Bucket Quota Guard"]
    C -- "Rate Limit Exceeded" --> C1["Raise PermissionError (HTTP 429)"]
    C -- "Quota Allowed" --> D["AdversarialPromptFirewall<br/>Scan for Injections / Overrides"]
    D -- "Flagged Threat" --> D1["Mark is_adversarial = True"]
    D -- "Clean Content" --> D2["Mark is_adversarial = False"]
    D1 --> E["PayloadCanonicalizer<br/>+ ZeroTrustIdentityTokenizer"]
    D2 --> E
    E --> F["ZeroTrustIdentityTokenizer<br/>SHA-256 HMAC in RAM"]
    F --> G["PiiPurgeGuard.assert_zero_pii<br/>Strict Zero-PII Sentinel"]
    G -- "Cleartext PII Detected" --> G1["Raise ValueError (Purge Guard Failed)"]
    G -- "Zero-PII Validated" --> H["PublicAgentStandardizedIntakePayload<br/>(Clean Normalized Contract)"]
```

---

### Phase 2: Layer 3 Intake Evaluation & Layer 4 Gate 1

The standardized intake contract enters Layer 3 for structure classification, and Layer 4 Gate 1 executes modality handling:

```mermaid
flowchart TD
    H["PublicAgentStandardizedIntakePayload"] --> I["PublicAgentApi._submit_payload"]
    I --> J["IntakePayloadEvaluator.evaluate_payload"]
    
    J --> K{"Structure Level Check"}
    K -- "DTMF / MENU_SELECTION" --> L["Structured Fast-Path Bypass<br/>requires_nlu_extraction = False"]
    K -- "FREE_TEXT" --> M["NLU Extraction Path<br/>requires_nlu_extraction = True"]
    
    L --> N["ClaimOrchestrator.process_ingress_payload (Gate 1)"]
    M --> N

    N --> O{"Modality Dispatch"}
    O -- "PayloadType.AUDIO" --> P["BhashiniService.transcribe_audio<br/>+ BhashiniService.translate_text"]
    P --> Q["SlmExtractor.extract_entities"]
    O -- "PayloadType.TEXT (Structured)" --> R["Direct Keypress Mapping<br/>Confidence = 1.0, Bypass GPU SLM"]
    O -- "PayloadType.TEXT (Free Text)" --> Q
    
    Q --> S["ExtractedEntityPayload<br/>(Intent, Entities, Confidence Score)"]
    R --> S
```

---

### Phase 3: Layer 4 Gate 2 — Intent & Completeness Validation

Gate 2 evaluates domain intent, checks for required fields, and coordinates multi-turn conversational re-prompts:

```mermaid
flowchart TD
    S["ExtractedEntityPayload"] --> T["ClaimOrchestrator.check_claim_completeness (Gate 2)"]
    
    T --> U{"Is Structured Bypass or Adversarial?"}
    U -- "Yes" --> V["Bypass Gate 2 Completeness Check"]
    U -- "No" --> W{"ApplicationIntent == APPLY_SUBSIDY?"}
    
    W -- "No (Status Check / Grievance)" --> X["Route to Read-Only Inquiry Flow"]
    W -- "Yes" --> Y["Scan Mandatory Domain Entities:<br/>1. District<br/>2. Crop Name<br/>3. Survey Number"]
    
    Y --> Z{"Missing Entities?"}
    Z -- "No (All Present)" --> AA["Proceed to Gate 3 Adjudication"]
    Z -- "Yes" --> AB{"Attempt Count < 3?"}
    AB -- "Yes" --> AC["Build Re-prompt Outcome<br/>(REQUEST_MORE_INFO)<br/>Return to Citizen"]
    AB -- "No (Attempts >= 3)" --> AD["Halt Loop to Prevent Fatigue<br/>Proceed to Gate 3 (Will Route to Review)"]
```

---

### Phase 4: Layer 4 Gate 3 — Governance Adjudication Matrix

Gate 3 cross-matches the claim against sovereign DPI registries and evaluates the tri-state decision matrix:

```mermaid
flowchart TD
    AA["ClaimEvaluationPayload"] --> AE["ClaimAdjudicator.evaluate_claim (Gate 3)"]
    
    AE --> AF["IdentityVerificationService<br/>verify_identity_token(token)"]
    AE --> AG["AgriRegistryService<br/>verify_land_record(token, survey_no)"]
    AE --> AH["Anti-Double-Dipping Check<br/>(citizen_token, active_season) in ledger?"]
    
    AF & AG & AH --> AI{"Decision Matrix Evaluation"}
    
    AI -- "Score >= 0.85 & Eligible & Unique" --> AJ["Verdict: AUTO_APPROVE<br/>Action: AUTO_APPROVE<br/>Status: APPROVED<br/>DisbursementTxnId: TXN-YYYY-XXXXXX"]
    
    AI -- "Score < 0.85 OR Flagged Adversarial OR Missing Entities" --> AK["Verdict: ROUTE_FOR_MANUAL_REVIEW<br/>Action: ROUTE_FOR_MANUAL_REVIEW<br/>Status: UNDER_REVIEW<br/>EscalationCaseId: SPP-CASE-YYYY-XXXXXX"]
    
    AI -- "Ineligible Land Record OR Duplicate Claim Detected" --> AL["Verdict: AUTO_REJECT<br/>Action: AUTO_REJECT<br/>Status: REJECTED<br/>RejectionReason: Non-empty Reason"]
```

---

### Phase 5: Post-Decision Execution & Outbound Confirmation Delivery

Once the decision is made, financial clearing or caseworker queues are updated, and the outbound delivery service dispatches channel-native confirmations:

```mermaid
flowchart TD
    AJ --> AM["PaymentRailService.initiate_disbursement"]
    AM --> AN["DisbursementCallbackPayload<br/>(disbursement_status = SUCCESS)"]
    
    AK --> AO["CaseManagementService.stage_incident_ticket"]
    AO --> AP["Caseworker Review Queue<br/>(Staged SPP-CASE Ticket)"]
    
    AN & AP & AL --> AQ["MultichannelNotificationService<br/>prepare_and_dispatch"]
    
    AQ --> AR{"Originating Channel"}
    AR -- "WHATSAPP" --> AS["Render Rich Markdown Card<br/>(Txn ID / Case ID + Emojis)"]
    AR -- "IVR_VOICE" --> AT["Synthesize Spoken Vernacular Audio<br/>(Bhashini TTS Audio URL)"]
    AR -- "USSD / SMS" --> AU["Format GSM Text String<br/>(Strictly <= 160 Characters)"]
    
    AS & AT & AU --> AV["Edge Connector Egress Dispatch<br/>(WhatsApp / IVR / USSD / SMS)"]
    AV --> AW["TransmissionAck Receipt<br/>Delivered to Citizen"]
```

---

## 3. Data Contract Lifecycle & Transformation Progression

| Pipeline Stage | Active Data Contract | Key Attributes & Invariants | Consuming Component |
| :--- | :--- | :--- | :--- |
| **Layer 1 Ingress** | [`WhatsAppIngressPayload`](../src/data_models/raw_ingress/whatsapp_payload.py) / [`IvrIngressPayload`](../src/data_models/raw_ingress/ivr_payload.py) / [`UssdIngressPayload`](../src/data_models/raw_ingress/ussd_payload.py) / [`SmsIngressPayload`](../src/data_models/raw_ingress/sms_payload.py) | Raw phone number (`E.164`), raw text body or audio URL. | [`IngestionFirewall`](../src/gateway/ingestion_firewall.py) |
| **Layer 2 Security** | [`PublicAgentStandardizedIntakePayload`](../src/data_models/public_agent/standardized_intake_payload.py) | 64-character SHA-256 HMAC `tokenized_citizen_id`. Zero cleartext PII. Redacted text content. | [`PublicAgentApi`](../src/public_agent/public_agent_api.py) |
| **Layer 3 Intake** | [`IntakeEvaluationResult`](../src/public_agent/intake_payload_evaluator.py) | `is_valid: bool`, `requires_nlu_extraction: bool` (fast-path bypass flag). | [`ClaimOrchestrator`](../src/orchestrator/claim_orchestrator.py) |
| **Gate 1 Extractor** | [`ExtractedEntityPayload`](../src/data_models/governance/extracted_entity_payload.py) | `application_intent`, `domain_entities: dict`, `ai_confidence_score: float`, `is_adversarial_attempt: bool`. | [`ClaimOrchestrator`](../src/orchestrator/claim_orchestrator.py) |
| **Gate 3 Adjudication** | [`ClaimEvaluationPayload`](../src/data_models/governance/claim_evaluation_payload.py) $\rightarrow$ [`GovernanceOutcomePayload`](../src/data_models/governance/governance_outcome_payload.py) | `governance_action` (`AUTO_APPROVE` / `ROUTE_FOR_MANUAL_REVIEW` / `AUTO_REJECT`), `disbursement_txn_id`, `escalation_case_id`. | [`PaymentRailService`](../src/services/dpi/payment_rail_service.py) / [`CaseManagementService`](../src/orchestrator/case_management_service.py) |
| **Delivery Egress** | [`NotificationRequestPayload`](../src/data_models/delivery/notification_request_payload.py) $\rightarrow$ [`OutboundNotificationPayload`](../src/data_models/delivery/outbound_notification_payload.py) $\rightarrow$ [`TransmissionAck`](../src/data_models/delivery/transmission_ack.py) | Adapted message string ($\le 160$ chars for USSD/SMS, Markdown for WhatsApp, TTS URL for IVR), carrier message reference. | Originating Carrier Gateway $\rightarrow$ Citizen |
