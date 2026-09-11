# End-to-End Architecture & Workflow: Ingress to Governance Determination

This document maps the complete end-to-end architectural workflow of **AgriStack DBT Core** — from an initial multi-channel citizen event (e.g., WhatsApp message, IVR voice call, USSD keypress) through the 4-layer Zero-Trust pipeline to the final governance determination and adaptive outbound delivery.

---

## 1. Master End-to-End Sequence Diagram

```mermaid
sequenceDiagram
    autonumber
    actor Citizen as 🌾 Citizen
    participant L1 as Layer 1: Edge Connectors<br/>(WhatsApp / IVR / USSD / SMS)
    participant L2 as Layer 2: Perimeter Security Gateway<br/>(Auth / Rate Limiting / Tokenizer)
    participant L3 as Layer 3: Public Agent Gateway<br/>(Intake & Entity Extractor)
    participant AI as Sovereign AI Services<br/>(Bhashini ASR/NMT & SLM Extractor)
    participant L4_Orch as Layer 4: Claim Governance Engine<br/>(Completeness & Policy Coordinator)
    participant L4_Adj as Layer 4: Governance Adjudication<br/>(Gate 3 Decision Matrix)
    participant DPI as Authoritative Sovereign Registries<br/>(MOSIP / AgriStack / PFMS)
    participant L4_Case as Layer 4: Case Management<br/>(Escalation Queue & Audit Log)
    participant Deliv as Outbound Delivery Engine<br/>(Adaptive Multi-Channel Egress)

    %% Step 1: Channel Ingress
    Citizen->>L1: Inbound Interaction (WhatsApp, IVR Voice, USSD Menu, SMS)
    Note over L1: Validates raw carrier protocol format

    %% Step 2: Layer 2 Security Gateway
    L1->>L2: Ingest Raw Payload
    Note over L2: 1. Constant-Time HMAC Signature Check<br/>2. Token Bucket Rate Limiting<br/>3. Adversarial Prompt Injection Scan<br/>4. SHA-256 HMAC Identity Tokenization in RAM<br/>5. Strict Zero-PII Purge Assertion
    L2-->>L1: Return Standardized Intake Contract & Security Flags

    %% Step 3: Layer 3 Public Agent Gateway & Entity Extraction
    L1->>L3: Submit Standardized Intake Contract

    rect rgb(240, 248, 255)
    Note over L3,AI: Layer 3: Modality Handling & SLM Entity Extraction
    alt Ingress Modality is Audio
        L3->>AI: Transcribe Audio (Bhashini Speech-to-Text ASR)
        AI-->>L3: Vernacular Text Transcript
        L3->>AI: Extract Domain Entities (Sovereign SLM)
        AI-->>L3: Extracted Domain Entities & Confidence Score
    else Structure Level is Menu / DTMF Selection
        Note over L3: Structured Fast-Path Bypass<br/>(Confidence = 1.0, bypasses GPU SLM)
    else Ingress Modality is Free Text
        L3->>AI: Extract Domain Entities (Sovereign SLM)
        AI-->>L3: Extracted Domain Entities & Confidence Score
    end
    end

    %% Step 4: Layer 4 Claim Orchestration & Governance
    L3->>L4_Orch: Execute Governance Cycle (Intake + Extracted Entities)

    %% Gate 2: Mandatory Entity Completeness & Multi-Turn Reprompts
    rect rgb(255, 250, 240)
    Note over L4_Orch: GATE 2: Intent & Mandatory Entity Validation
    alt Missing Mandatory Entities (District, Crop, Survey) AND Attempts < 3
        L4_Orch-->>Citizen: Trigger Conversational Re-Prompt (REQUEST_MORE_INFO)
    end
    end

    %% Gate 3: Policy Adjudication Matrix
    rect rgb(240, 255, 240)
    Note over L4_Orch,L4_Adj: GATE 3: Governance Adjudication Matrix
    L4_Orch->>L4_Adj: Evaluate Claim Rules
    L4_Adj->>DPI: Verify Citizen Identity Token (Sovereign ID Registry)
    DPI-->>L4_Adj: Identity Verified (True/False)
    L4_Adj->>DPI: Cross-Match Cadastral Land & Crop (AgriStack Registry)
    DPI-->>L4_Adj: Entitlement Verified (True/False)
    Note over L4_Adj: Anti-Double-Dipping Active Season Validation
    L4_Adj-->>L4_Orch: Final Governance Determination
    end

    %% Post-Decision Execution
    rect rgb(255, 245, 245)
    Note over L4_Orch,DPI: Post-Decision Execution & Outbound Delivery
    alt Verdict is AUTO_APPROVE (Score >= 0.85 & Eligible & Unique)
        L4_Orch->>DPI: Dispatch Wire Payment (Payment Rails)
        DPI-->>L4_Orch: Disbursement Callback (PENDING -> SUCCESS)
        L4_Orch->>Deliv: Dispatch Notification (Approval Receipt)
    else Verdict is ROUTE_FOR_MANUAL_REVIEW (Score < 0.85 / Flagged / Attempts >= 3)
        L4_Orch->>L4_Case: Stage Incident Ticket (Caseworker Queue)
        L4_Case-->>L4_Orch: Staged Incident Case ID (SPP-CASE-YYYY-XXXXXX)
        L4_Orch->>Deliv: Dispatch Notification (Review Staged Receipt)
    else Verdict is AUTO_REJECT (Ineligible / Duplicate Active Claim)
        L4_Orch->>Deliv: Dispatch Notification (Rejection Reason + Helpline)
    end
    Deliv->>L1: Adapted Outbound Notification (WhatsApp / IVR / USSD / SMS)
    L1->>Citizen: Channel-Adapted Confirmation Receipt
    end
```

---

## 2. Detailed Execution Flow by Layer

### Phase 1: Edge Ingress & Layer 2 Perimeter Security

An inbound request arrives from a carrier network and is processed through perimeter security:

```mermaid
flowchart TD
    A["Inbound Request<br/>(e.g., WhatsApp Webhook)"] --> B["Carrier Auth Validator<br/>Constant-Time HMAC-SHA256 Check"]
    B -- "Invalid / Missing Signature" --> B1["Fail Closed (HTTP 401/403)"]
    B -- "Valid Signature" --> C["Rate Limiter<br/>Token Bucket Quota Guard"]
    C -- "Rate Limit Exceeded" --> C1["Raise Permission Error (HTTP 429)"]
    C -- "Quota Allowed" --> D["Adversarial Prompt Firewall<br/>Scan for Injections & Overrides"]
    D -- "Flagged Threat" --> D1["Mark Threat Flag = True"]
    D -- "Clean Content" --> D2["Mark Threat Flag = False"]
    D1 --> E["Payload Canonicalizer<br/>+ Identity Tokenizer"]
    D2 --> E
    E --> F["Zero-Trust Identity Tokenizer<br/>SHA-256 HMAC in RAM"]
    F --> G["PII Purge Sentinel<br/>Strict Zero-PII Invariant Check"]
    G -- "Cleartext PII Detected" --> G1["Raise Security Error (Purge Guard Failed)"]
    G -- "Zero-PII Validated" --> H["Standardized Intake Contract<br/>(Zero-PII Normalized Payload)"]
```

---

### Phase 2: Layer 3 Modality Handling & SLM Entity Extraction

The standardized intake contract enters Layer 3 for speech transcription and SLM domain entity extraction:

```mermaid
flowchart TD
    H["Standardized Intake Contract"] --> I["Public Agent Gateway<br/>Intake Entity Extractor"]

    I --> O{"Modality Dispatch"}
    O -- "Audio Voice Stream" --> P["Bhashini Speech-to-Text ASR<br/>+ Machine Translation NMT"]
    P --> Q["Sovereign SLM Entity Extractor"]
    O -- "Structured Text Keypress" --> R["Direct Deterministic Entity Mapping<br/>Confidence = 1.0, Bypass GPU SLM"]
    O -- "Free-Text Message" --> Q

    Q --> S["Extracted Domain Entity Contract<br/>(Intent, Entities, Confidence Score)"]
    R --> S
```

---

### Phase 3: Layer 4 Gate 2 — Intent & Completeness Validation

Gate 2 evaluates domain intent, checks for required fields, and coordinates multi-turn conversational re-prompts:

```mermaid
flowchart TD
    S["Extracted Entity Contract"] --> T["Layer 4 Orchestrator<br/>Gate 2: Intake Completeness & Intent Validation"]

    T --> U{"Is Structured Bypass or Adversarial?"}
    U -- "Yes" --> V["Bypass Gate 2 Completeness Check"]
    U -- "No" --> W{"Application Intent == APPLY_SUBSIDY?"}

    W -- "No (Status Check / Grievance)" --> X["Route to Read-Only Inquiry Flow"]
    W -- "Yes" --> Y["Scan Mandatory Domain Entities:<br/>1. District<br/>2. Crop Name<br/>3. Survey Number"]

    Y --> Z{"Missing Mandatory Entities?"}
    Z -- "No (All Present)" --> AA["Proceed to Gate 3 Policy Adjudication"]
    Z -- "Yes" --> AB{"Attempt Count < 3?"}
    AB -- "Yes" --> AC["Build Re-prompt Directive<br/>(REQUEST_MORE_INFO)<br/>Return to Citizen"]
    AB -- "No (Attempts >= 3)" --> AD["Halt Multi-turn Loop to Prevent Fatigue<br/>Proceed to Gate 3 (Will Route to Review)"]
```

---

### Phase 4: Layer 4 Gate 3 — Governance Adjudication Matrix

Gate 3 cross-matches the claim against sovereign DPI registries and evaluates the tri-state decision matrix:

```mermaid
flowchart TD
    AA["Claim Evaluation Contract"] --> AE["Claim Adjudication Engine<br/>Gate 3: Policy Decision Matrix"]

    AE --> AF["Identity Verification Service<br/>Verify Token in Sovereign Registry"]
    AE --> AG["AgriStack Registry Service<br/>Cross-Match Cadastral Land & Crop"]
    AE --> AH["Anti-Double-Dipping Ledger<br/>Validate (Citizen Token, Season)"]

    AF & AG & AH --> AI{"Decision Matrix Evaluation"}

    AI -- "Score >= 0.85 & Eligible & Unique" --> AJ["Verdict: AUTO_APPROVE<br/>Status: APPROVED<br/>Financial State: PENDING<br/>DisbursementTxnId: TXN-YYYY-XXXXXX"]

    AI -- "Score < 0.85 OR Flagged Adversarial OR Missing Entities" --> AK["Verdict: ROUTE_FOR_MANUAL_REVIEW<br/>Status: UNDER_REVIEW<br/>Financial State: Bypassed<br/>EscalationCaseId: SPP-CASE-YYYY-XXXXXX"]

    AI -- "Ineligible Land Record OR Duplicate Claim Detected" --> AL["Verdict: AUTO_REJECT<br/>Status: REJECTED<br/>Financial State: Bypassed<br/>RejectionReason: Non-empty Reason Code"]
```

---

### Phase 5: Post-Decision Execution & Outbound Confirmation Delivery

Once the decision is made, financial clearing or caseworker queues are updated, and the outbound delivery service dispatches channel-native confirmations:

```mermaid
flowchart TD
    AJ --> AM["Payment Rail Service<br/>Initiate Treasury Wire Transfer"]
    AM --> AN["Disbursement Callback Receipt<br/>(Disbursement Status = SUCCESS)"]

    AK --> AO["Case Management Service<br/>Stage Incident Review Ticket"]
    AO --> AP["District Caseworker Dashboard<br/>(Staged SPP-CASE Ticket)"]

    AN & AP & AL --> AQ["Adaptive Multi-Channel Notification Engine<br/>Compose Outbound Notification"]

    AQ --> AR{"Originating Ingress Channel"}
    AR -- "WhatsApp" --> AS["Render Rich Markdown Card<br/>(Txn ID / Case ID + Emojis)"]
    AR -- "IVR Voice" --> AT["Synthesize Spoken Vernacular Audio<br/>(Bhashini TTS Audio URL)"]
    AR -- "USSD / SMS" --> AU["Format GSM Plain Text String<br/>(Strictly <= 160 Characters)"]

    AS & AT & AU --> AV["Edge Connector Egress Dispatch<br/>(WhatsApp / IVR / USSD / SMS)"]
    AV --> AW["Transmission Acknowledgment Receipt<br/>Delivered to Citizen"]
```

---

### Phase 6: Relational Persistence, Immutable Audit History & Analytical Deduplication

Operational state transitions and multi-turn conversational attempts are persisted to the normalized relational ledger while preserving strict Zero-PII invariants and preventing analytical cartesian fan-out:

```mermaid
flowchart TD
    S_LOG["Session Telemetry Log<br/>(session_telemetry_log)"]
    E_DET["Session Extraction Details<br/>(session_extraction_details)"]
    G_LED["Application Governance Ledger<br/>(application_governance_ledger)"]
    G_HIST["Immutable Audit History<br/>(application_governance_ledger_history)"]
    V_DEDUP["Analytical Deduplicated View<br/>ROW_NUMBER() OVER (PARTITION BY session_id ORDER BY attempt_id DESC) = 1"]
    V_OBT["Citizen Journey Funnel OBT<br/>(citizen_journey_funnel)"]

    AW --> S_LOG
    S_LOG -- "1:N Child Attempts (STAGED / SUPERSEDED / COMMITTED)" --> E_DET
    E_DET -- "Final Committed Turn (Attempt N)" --> G_LED
    G_LED -- "AFTER INSERT / AFTER UPDATE Triggers" --> G_HIST
    E_DET --> V_DEDUP
    S_LOG & V_DEDUP & G_LED --> V_OBT
```

1. **Multi-Turn Conversational State Separation**: Operational extraction attempts are recorded in `session_extraction_details` with lifecycle markers (`STAGED`, `SUPERSEDED`, `COMMITTED`).
2. **Window-Function Deduplication**: Downstream Business Intelligence (BI) views isolate the single authoritative extraction attempt per session via `ROW_NUMBER() OVER (PARTITION BY session_id ORDER BY attempt_id DESC) = 1`, eliminating multi-turn cartesian fan-out.
3. **Immutable Governance Audit Trail**: Database triggers (`AFTER INSERT`, `AFTER UPDATE`) automatically append every status and action transition to `application_governance_ledger_history` with actor attribution.

---

## 3. Data Contract Lifecycle & Transformation Progression

| Pipeline Stage | Active Data Contract | Key Attributes & Invariants | Consuming Architectural Layer |
| :--- | :--- | :--- | :--- |
| **Layer 1 Ingress** | *Carrier Ingress Contracts (WhatsApp, IVR, USSD, SMS)* | Raw phone number (`E.164`), raw text body or signed audio URL. | Layer 2 Perimeter Security Gateway |
| **Layer 2 Security** | *Standardized Intake Payload* | 64-character SHA-256 HMAC pseudonymous citizen token. Zero cleartext PII. Redacted text content. | Layer 3 Public Agent Gateway |
| **Layer 3 Perception & Extraction** | *Extracted Domain Entity Contract* | Application intent, domain entities map, AI confidence score, security threat flag. | Layer 4 Claim Governance Engine |
| **Layer 4 Adjudication** | *Claim Evaluation Contract $\rightarrow$ Governance Determination Outcome* | Governance action (`AUTO_APPROVE` / `ROUTE_FOR_MANUAL_REVIEW` / `AUTO_REJECT`), transaction ID, escalation case ID. | Sovereign Payment Rails / Caseworker Management Service |
| **Delivery Egress** | *Outbound Notification Request $\rightarrow$ Channel Notification Payload $\rightarrow$ Transmission Acknowledgment* | Adapted message string ($\le 160$ chars for USSD/SMS, Markdown card for WhatsApp, TTS URL for IVR), carrier message reference ID. | Originating Carrier Gateway $\rightarrow$ Citizen Device |
| **Persistence & Analytics** | *Relational Ledger Records $\rightarrow$ Citizen Journey Funnel View* | 64-character pseudonymous HMAC token, terminal JSONB governance metadata (`approval_amount` / `rejection_reason`), window-deduplicated attempt (`rn = 1`), immutable audit history. | Relational Database / Analytical BI Layer |
