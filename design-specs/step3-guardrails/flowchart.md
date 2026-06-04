[CITIZEN INGRESS PERIMETER]
          o IVR Voice Gateway (SIP Inbound)   o WhatsApp API Webhook   o USSD Signaling (*147#)
                        │                               │                        │
                        │ [IVR_VOICE]                   │ [WHATSAPP]             │ [USSD]
                        ▼                               ▼                        │
          ┌───────────────────────────┐   ┌───────────────────────────┐       ┌──────────────────────────────────────────────────┐   
          │ IVR Ingress  Node         │   │ Whatsapp Ingress Node     │       │ USSD Ingress Node                                │   
          │  - Generates session_id   │   │   - Generates session_id  │       │    -  Bypasses entire AI stack                   │
          └─────────────┬─────────────┘   └─────────────┬─────────────┘       │    - Maps cellular signaling digits to fields    │
                        │                               │                     │   - Hardcodes extraction_confidence = 1.0        │
                        ▼                               │                     └──────────────────┬───────────────────────────────┘  
          ┌───────────────────────────────────┐         │                                        │
          │ Foundational AI: ASR              │         │                                        │
          │   - Audio -> Raw Text String      │         │                                        │
          └─────────────┬─────────────────────┘         │                                        │
                        │                               │                                        │
                        └────────┬──────────────────────┘                                        │
                                 │                                                               │
                                 │(Raw Text Strings)                                             │
                                 ▼                                                               │
              ┌────────────────────────────────────────────────────────────┐                     │
              │ Shared Foundational AI: NMT                                │                     │                     
              │   - Converts regional agricultural dialect text -> English │                     │
              └──────────────────┬─────────────────────────────────────────┘                     │
                                 │ (English Text Strings)                                        │
                                 │                                                               │
                                 ▼                                                               │                               │                                                               │  
        ┌────────────────────────────────────────────────────────┐                               │                          
        │ Sector-Specific SLM NodeL                              │                               │
        │   - Local  SLM Entity Extraction                       │                               │
        │   - Runs structured_extract() to parse target entities │                               │
        │   - Emits probabilistic AI Confidence Score metrics    │                               │
        └─────────────────────────────┬──────────────────────────┘                               │
                                      │                                                          │
                                      └───────────────────┬──────────────────────────────────────┘
                                                          │ [Channels CONVERGE POINT]
                                                          ▼
=========================================================================================
 GOVERNANCE PERIMETER GATES - APPLIED TO ALL CONVERGED CHANNELS BEFORE DISBURSEMENT 
=========================================================================================
                                         │
                                         ▼
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│ METADATA PERSISTENCE TRACK - Unified Telemetry Ingestion                                 │                                     
│ - Commits core tracking metadata directly to session_telemetry_log table on disk:        │
│   session_id (UUID PK), source_phone_number, ingress_channel, and created_at.            │
│ - Sets initial operational state flag cleanly as 'ACTIVE'.                               │
└───────────────────────────────────────┬──────────────────────────────────────────────────┘
                                        │
                                        ▼
┌───────────────────────────────────────────────────────────────────────────────────────────┐
│ [Guardrail 1] GATE_01_PII_SANITY Cryptographic RAM Tokenization Perimeter                 │
│ 1. Intercepts raw payload parameters inside volatile runtime RAM (Zero-Disk Logging Track)│
│ 2. Validates extracted identifier patterns using strict length/regex integrity filters    │
│ 3. Ingests an environment-injected cryptographic pepper-salt configuration value          │
│ 4. Computes: SHA-256(raw_unmasked_identifier + pepper_salt) execution logic               │
│ 5. Instantly purges raw cleartext parameters from volatile memory post-tokenization pass  │
└───────────────────────────────────────────┬───────────────────────────────────────────────┘
                                            ├────────────────────────────────────────────────┐
                                            │ [PASS: Secure Hash Generated]                  │ [CRITICAL FAIL: Malformed String]
                                            ▼                                                ▼
┌────────────────────────────────────────────────────────────────────────────────────┐  ┌───────────────────────────────────┐
│ DETAILED PAYLOAD PERSISTENCE - Unified Extraction Payload                          │  │Abort Malformed Session Pipeline   │
│ - Commits payload_id (PK), relational session_id (FK), and current loop attempt_id │  │ - Updates existing parent row     │
│ - Stores irreversible tokenized identifier token into farmer_id_cleartext column   │  │   in session_telemetry_log to     │
│ - Saves extracted entities (district, crop, anomaly descriptions)                  │  │   status = 'REJECTED'.            │
│ - Enforces operational tracking flags by updating processing_state to 'STAGED'     │  │ - Termines session instantly to   │
└───────────────────────────────────────────┬────────────────────────────────────────┘  │   prevent dirty DB downstream.    │
                                            │                                           └───────────────────────────────────┘
                                            ▼
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│ DOWNSTREAM DATA TRANSFORMATION:                                                          │
│   dbt-core Analytical Modeling Logic Transformation Perimeter                            │
│ - Compiles local model staging views (`stg_session_extraction_details`)                  │
│ - Executes window partitions (`QUALIFY ROW_NUMBER() OVER (PARTITION BY session_id...)`)  │
│ - Dedupes multi-attempt correction entries to isolate active payload lines               │
│ - Materializes refined clean tables, preparing variables for registry integration arrays │
└───────────────────────────────────────────┬──────────────────────────────────────────────┘
                                            │
                                            ▼
                ┌──────────────────────────────────────────────────────────────────┐
                │ [Guardrail 2] Algorithmic Model Extraction Confidence Check      │
                │  - Is extraction_confidence >= 0.85?                             │
                │  - (USSD always passes; static 1.0)                              │
                └──────────────────────────┬───────────────────────────────────────┘
                                           │
                                           ├────────────────────────────────┐
                                           │ [PASS]                         │ [FAIL]
                                           ▼                                ▼
                    ┌──────────────────────────────────────────┐     ┌──────────────┐
                    │Core Registry Integration                 │     │ loop_count++ │
                    │ - Query Authoritative AgriStack Gateway  │     │ attempt_id>3?│
                    └──────────────────┬───────────────────────┘     └──────┬───────┘
                                           │                                │
                                           ▼                                ├─────────────┐
                    ┌────────────────────────────────────────────┐          │[YES]        │[NO] 
                    │[Guardrail 3]                               │          │             ▼       
                    │   GATE_02_REGISTRY_CROSSMATCH Verified     │          │      ┌─────────────────┐ 
                    │ - Does land plot ID crop sown              │          │      │ Conversational  │
                    │    record match self-reported data?        │          │      │ Retry           │
                    └──────────────────┬─────────────────────────┘          │      └─────────────────┘ 
                                           │                                │               │ 
                                  ┌────────┴────────┐                       │               │
                                  │ [PASS]          │ [FAIL]                │               │
                                  ▼                 ▼                       ▼               ▼
                        ┌──────────────────┐     ┌────────────────────────────────────────────────┐
                        │                  │     │ Human In The Loop Fallback Gate.               │
                        │ Automated Payment│     │ - DB Processing State updated to 'REFERRED'    │  
                        │ Disbursement Rail│     │ - Suspends automated track; updates SPP        │
                        │ Clearing Tracks  │     │ - Routes payload to manual worker queues       │
                        └──────────────────┘     └────────────────────────────────────────────────┘