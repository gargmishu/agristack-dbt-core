[CITIZEN INGRESS PERIMETER]
          o IVR Voice Gateway (SIP Inbound)   o WhatsApp API Webhook               o USSD Signaling (*147#)
                        │                               │                                │
                        │ [IVR_VOICE]                   │ [WHATSAPP]                     │ [USSD]
                        ▼                               ▼                                │
          ┌─────────────────────────────────────┐   ┌──────────────────────────────────────┐       ┌──────────────────────────────────────────────────┐   
          │ IVR: step_01_initiation_and_...     │   │ Whatsapp: step_01_initiation_and_... │       │ USSD: step_01_initiation_and_                    │
          │  - Generates session_id             │   │   - Generates session_id             │       │   - Bypasses entire AI stack                     │
          └─────────────┬───────────────────────┘   └─────────────┬────────────────────────┘       │   - Maps cellular signaling digits to fields     │
                        │                                         │                                │   - Hardcodes extraction_confidence = 1.0        │
                        ▼                                         │                                └──────────────┬───────────────────────────────────┘  
          ┌───────────────────────────────────────┐               │                                               │
          │ step_02_speech_to_text_transcription  │               │                                               │
          │   - Audio -> Raw Text String          │               │                                               │
          └─────────────┬─────────────────────────┘               │                                               │
                        │                                         │                                               │
                        └────────┬────────────────────────────────┘                                               │
                                 │                                                                                │
                                 │(Raw Text Strings)                                                              │
                                 ▼                                                                                │
              ┌────────────────────────────────────────────────────────────┐                                      │
              │ step_03_text_translation_and_normalization                 │                                      │                     
              │   - Converts regional agricultural dialect text -> English │                                      │
              └──────────────────┬─────────────────────────────────────────┘                                      │
                                 │ (English Text Strings)                                                         │
                                 │                                                                                │
                                 ▼                                                                                │
        ┌────────────────────────────────────────────────────────┐                                                │                          
        │ step_04_structured_field_entity_extraction             │                                                │
        │   - Local  SLM Entity Extraction                       │                                                │
        │   - Runs structured_extract() to parse target entities │                                                │
        │   - Emits probabilistic AI Confidence Score metrics    │                                                │
        └─────────────────────────────┬──────────────────────────┘                                                │
                                      │                                                                           │
                                      └───────────────────┬───────────────────────────────────────────────────────┘
                                                          │ [Channels CONVERGE POINT]
                                                          ▼
=========================================================================================
 GOVERNANCE PERIMETER GATES - APPLIED TO ALL CONVERGED CHANNELS BEFORE DISBURSEMENT 
 [ RUNTIME INTAKE PHASES - SECURING & PERSISTING CONVERGED DATA PACKETS ]
=========================================================================================
                                         │
                                         ▼
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│ PHASE A: METADATA PERSISTENCE TRACK                                                      │
│    step_01_initiation_and_channel_entry (Unified Telemetry Ingestion Ingress Target)     │                                     
│ 1. Commits core tracking metadata directly to session_telemetry_log table on disk:       │
│    session_id (UUID PK), source_phone_number, ingress_channel, and created_at.           │
│ 2. Sets initial operational state flag cleanly as 'ACTIVE'.                              │
└───────────────────────────────────────┬──────────────────────────────────────────────────┘
                                        │
                                        ▼
┌───────────────────────────────────────────────────────────────────────────────────────────┐
│ PHASE B: INLINE INGESTION GATE                                                            │
│    step_05_identity_and_agricultural_registry_verification                                │
│      [Guardrail 1] GATE_01_PII_SANITY                                                     │ 
│ 1. Intercepts raw payload parameters inside volatile runtime RAM (Zero-Disk Logging Track)│
│ 2. Validates extracted identifier patterns using strict length/regex integrity filters    │
│ 3. Ingests an environment-injected cryptographic pepper-salt configuration value          │
│ 4. Computes: SHA-256(raw_unmasked_identifier + pepper_salt) execution logic               │
│ 5. Instantly purges raw cleartext parameters from volatile memory post-tokenization pass  │
└───────────────────────────────────────────┬───────────────────────────────────────────────┘
                                            │ 
                                            ├────────────────────────────────────────────────┐
                                            │ [PASS: Secure Hash Generated]                  │ [CRITICAL FAIL: Malformed String]
                                            ▼                                                ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐  ┌─────────────────────────────────────┐
│ PHASE C: DETAILED PAYLOAD PERSISTENCE                                                  │  │ step_05_identity_and_agri_...       │
│    step_05_identity_and_agricultural_registry_verification (Extraction Payload Target) │  │          (Abort Ingress)            │     
│ 1. Commits payload_id (PK), relational session_id (FK), and current loop attempt_id    │  │ 1. Updates existing parent row in   │
│ 2. Stores irreversible tokenized identifier token into farmer_id_cleartext column      │  │    session_telemetry_log to         │
│ 3. Saves extracted entities (district, crop, anomaly descriptions)                     │  │    status = 'REJECTED'.             │
│ 4. Enforces operational tracking flags by updating processing_state to 'STAGED'        │  │ 2. Termines session instantly to    │
└───────────────────────────────────────────┬────────────────────────────────────────────┘  │    prevent dirty DB downstream.     │
                                            │                                               └─────────────────────────────────────┘
                                            ▼
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│ PHASE D: DOWNSTREAM DATA TRANSFORMATION:                                                 │
│   step_04_structured_field_entity_extraction (dbt-core Analytical Transformation)        │
│ 1. Compiles local model staging views (`stg_session_extraction_details`)                  │
│ 2. Executes window partitions (`QUALIFY ROW_NUMBER() OVER (PARTITION BY session_id...)`)  │
│ 3. Dedupes multi-attempt correction entries to isolate active payload lines               │
│ 4. Materializes refined clean tables, preparing variables for registry integration arrays │
└───────────────────────────────────────────┬──────────────────────────────────────────────┘
                                            │
                                            ▼
                ┌──────────────────────────────────────────────────────────────────┐
                │ step_07_governance_threshold_evaluation_and_routing              │
                │   [Guardrail 2] Extraction Confidence Check                      │
                │ 1. Is extraction_confidence >= 0.85?                             │
                │ 2. (USSD always passes; static 1.0)                              │
                └──────────────────────────┬───────────────────────────────────────┘
                                           │
                                           ├────────────────────────────────┐
                                           │ [PASS]                         │ [FAIL]
                                           ▼                                ▼
                    ┌──────────────────────────────────────────┐     ┌──────────────┐
                    │step_05_identity_and_agricultural_...     │     │ loop_count++ │
                    │ - Query Authoritative AgriStack Gateway  │     │ attempt_id>3?│
                    └──────────────────┬───────────────────────┘     └───────┬──────┘
                                           │                                 │
                                           ▼                                 ├─────────────┐
                    ┌─────────────────────────────────────────────┐          │[YES]        │[NO] 
                    │ step_05_identity_and_agricultural_...       │          │             ▼
                    │   [Guardrail 3] GATE_02_REGISTRY_CROSSMATCH │          │      ┌────────────────────┐
                    │ - Does land plot ID crop sown               │          │      │ step_04_ (Retry)   │
                    │    record match self-reported data?         │          │      │                    │
                    └──────────────────┬──────────────────────────┘          │      └────────────────────┘ 
                                           │                                 │               │ 
                                  ┌────────┴────────┐                        │               │
                                  │ [PASS]          │ [FAIL]                 │               │
                                  ▼                 ▼                        ▼               ▼
                    ┌───────────────────────────┐     ┌────────────────────────────────────────────────┐
                    │ step_07_gov_threshold...  │     │ step_07_gov_threshold...                       │
                    │ - Automated Payment       │     │   Human In The Loop Fallback Gate.             │  
                    │ Disbursement Rail         │     │ 1. Suspends automated track; updates SPP       │
                    └───────────────────────────┘     │ 2. Routes payload to manual worker queues      │
                                                      └────────────────────────────────────────────────┘