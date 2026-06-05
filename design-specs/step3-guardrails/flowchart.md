[CITIZEN INGRESS PERIMETER]
          o IVR Voice Gateway (SIP Inbound)   o WhatsApp API Webhook               o USSD Signaling (*147#)
                        │                               │                                │
                        │ [IVR_VOICE]                   │ [WHATSAPP]                     │ [USSD]
                        ▼                               ▼                                │
          ┌─────────────────────────────────────┐   ┌──────────────────────────────────────┐       ┌──────────────────────────────────────────────────┐   
          │ IVR: step_01_initiation_and_...     │   │ Whatsapp: step_01_initiation_and_... │       │ USSD: step_01_initiation_and_                    │
          │  - Generates session_id             │   │   - Generates session_id             │       │  - Bypasses entire AI stack                      │
          │   - Emits ivr_audio_stream_uri      │   │    - Emits whatsapp_cleartext_string │       │  - Mapped to district_name & crop_type strings   │
          └─────────────┬───────────────────────┘   └─────────────┬────────────────────────┘       │  - Hardcodes extraction_confidence = 1.0         │
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
        │   - [RE-ENTRY POINT FOR UPSTREAM CONVERSATIONAL LOOPS] │                                                │
        │   - Local SLM Entity Extraction                        │                                                │
        │   - Parses district, crop_type, reported_anomaly       │                                                │
        │   - Emits probabilistic AI Confidence Score metrics    │                                                │
        └─────────────────────────────┬──────────────────────────┘                                                │
                                      │                                                                           │
                                      └───────────────────┬───────────────────────────────────────────────────────┘
                                                          │ [Channels CONVERGE POINT]
                                                          ▼
============================================================================================================
 ZERO-TRUST SECURITY & GOVERNANCE PERIMETER GATES - APPLIED TO ALL CONVERGED CHANNELS BEFORE DISBURSEMENT 
 [ RUNTIME INTAKE PHASES - SECURING & PERSISTING CONVERGED DATA PACKETS ]
============================================================================================================
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
│    step_05_identity_perimeter_tokenization                                                │
│      [Guardrail 1] GATE_01_PII_SANITY                                                     │ 
│ 1. Intercepts raw payload parameters inside volatile runtime RAM (Zero-Disk Logging Track)│
│ 2. Validates extracted identifier patterns using strict length/regex integrity filters    │
│ 3. Ingests an environment-injected cryptographic pepper-salt configuration value          │
│ 4. Computes: SHA-256(raw_unmasked_identifier + pepper_salt) execution logic               │
│ 5. Instantly purges raw cleartext parameters from volatile memory post-tokenization pass  │
└───────────────────────────────────────────┬───────────────────────────────────────────────┘
                                            │ 
                                            ├──────────────────────────────────────────────────────┐
                                            │ [PASS: Secure Hash Generated]                        │ [CRITICAL FAIL: Malformed String]
                                            ▼                                                      ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐  ┌─────────────────────────────────────┐
│ PHASE C: DETAILED PAYLOAD PERSISTENCE                                                  │  │ step_05_identity_and_agri_...       │
│    step_05_identity_perimeter_tokenization (Extraction Payload Target)                 │  │          (Abort Ingress)            │     
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
│ 1. Compiles local model staging views (`stg_session_extraction_details`)                 │
│ 2. Executes window partitions (`QUALIFY ROW_NUMBER() OVER (PARTITION BY session_id...)`) │
│ 3. Dedupes multi-attempt correction entries to isolate active payload lines              │
│ 4. Materializes refined clean tables, preparing variables for registry integration arrays│
└───────────────────────────────────────────┬──────────────────────────────────────────────┘
                                            │
                                            ▼
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│ PHASE E: AUTHORITATIVE REGISTRY INTERCONNECT                                             │
│   step_06_agricultural_registry_crossmatch                                               │
│ 1. Passes tokenized_identity_hash & unified agricultural_assertions to land registers    │
│ 2. Verifies crop sown logs, cadastral_plot_id, ownership boundaries across state tables  │
│ 3. Emits registry_match_flag & agristack_eligibility_status updates                      │
└───────────────────────────────────────────┬──────────────────────────────────────────────┘
                                            │
                                            ▼
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│ PHASE F: SOCIAL PROTECTION PLATFORM INTAKE                                               │
│   step_07_social_benefits_registry_submission                                            │
│ 1. Consumes successful registry_match_flag to open case workflows                        │
│ 2. Interfaces with OpenSPP core APIs to stage transaction state lines                    │
│ 3. Emits openspp_case_id & sets registration_status to 'STAGED_SUCCESSFULLY'             │
└───────────────────────────────────────────┬──────────────────────────────────────────────┘
                                            │
                                            ▼
                ┌────────────────────────────────────────────────────────────────────┐
                │ step_08_governance_threshold_evaluation_and_routing                │
                │   [Guardrail 2] Extraction Confidence Check                        │
                │ 1. Evaluates confidence parameters and registry matching flags     │
                │ 2. Sourced via step_01 (USSD static 1.0) or step_04 (Probabilistic)│
                └───────────────────────┬────────────────────────────────────────────┘
                                        │
                                        ├─────────────────────────────────────┐
                                        │ [PASS: confidence >= 0.85]          │ [FAIL]
                                        ▼                                     ▼
                    ┌──────────────────────────────────────────┐     ┌──────────────┐
                    │ [PASSING TRACK RETRIEVAL BRANCH]         │     │ loop_count++ │
                    │ - Routes processing straight to core DBT │     │ attempt_id>3?│
                    │ - Clears NPCI Treasury clearing systems  │     │              │ 
                    └──────────────────────┬───────────────────┘     └──────┬───────┘
                                           │                                │
                                           ▼                                ├─────────────┐
                    ┌─────────────────────────────────────────────┐         │[YES]        │[NO] 
                    │ step_09_adaptive_multichannel_...           │         │             ▼
                    │   [AUTOMATED CASH CLEARING]                 │         │      ┌──────────────────────────┐
                    │ - Dispatches passing SMS template headers   │         │      │ step_04_ (Retry loop)    │
                    │ - Delivers automated PM-KISAN Ledger        │         │      │  - re-entry at step_04   │
                    │     Payment Transaction ID to citizen rail  │         │      │                          │
                    └─────────────────────────────────────────────┘         │      └──────────────────────────┘ 
                                                                            │                
                                                                            │
                                                                            │
                                                                     ┌────────────────────────────────────────────────┐
                                                                     │ [FALLBACK TRACK ESCALATION BRANCH]             │
                                                                     │ step_08_governance_threshold_eval_routing      │
                                                                     │   Human In The Loop Fallback Gate              │
                                                                     │ 1. Updates DB processing state to 'REFERRED'   │
                                                                     │ 2. Routes payload to manual caseworker queue   │
                                                                     │ 3. step_09_adaptive_multichannel_delivery      │
                                                                     │    returns encrypted Escalation Case ID        │
                                                                     └────────────────────────────────────────────────┘