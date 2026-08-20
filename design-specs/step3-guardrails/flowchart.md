Here is the fully updated master architecture diagram. The specific AI and DPI blocks are now explicitly denoted alongside their action tags, clearly distinguishing the external intelligence and national infrastructure calls from the internal routing logic.

```text
               [ LAYER 1: USER ACTION & CHANNELS ]

     📱 Smartphone         📞 Feature Phone        📵 Basic Phone
   ([ACTION] Voice Note)  ([ACTION] Voice Call) ([ACTION] USSD Menu)
            |                     |                      |
            v                     v                      v
      +------------+        +------------+         +------------+
      | WhatsApp   |        |    IVR     |         |    USSD    |
      +------------+        +------------+         +------------+

                                  |
               [ LAYER 2: GATEWAYS & CONNECTORS ]
                                  |
            v                     v                      v
 +--------------------+ +--------------------+ +--------------------+
 | [ACTION] Meta API  | | [ACTION] Telephony | | [ACTION] Telco Net |
 | Extracts: .ogg file| | Extracts: .wav file| | Extracts: Keystroke|
 +--------------------+ +--------------------+ +--------------------+
            |                     |                      |
            v                     v                      v
 +--------------------+ +--------------------+ +--------------------+
 | [ACTION] WA Connect| | [ACTION] IVR Con.  | | [ACTION] USSD Con. |
 | Packages to JSON   | | Packages to JSON   | | Packages to JSON   |
 | {type: "audio"}    | | {type: "audio"}    | | {type: "text"}     |
 +--------------------+ +--------------------+ +--------------------+
            \                     |                      /
             \                    |                     /
              \                   v                    /
               \      [ LAYER 3: THE PUBLIC AGENT ]   /
                \                 |                  /
                 \                v                 /
                  +--------------------------------+
                  | [ACTION] Public Agent Intake   |
                  | API Receives Standardized JSON |
                  +--------------------------------+
                                  |
                                  v
                  +--------------------------------+
                  | [ACTION] INITIATE DPI WORKFLOW |
                  +--------------------------------+
                                  |
                 [ LAYER 4: DPI WORKFLOW EXECUTION ]
                                  |
                  +--------------------------------+
                  | [CHECK] Evaluate 'payload_type'|
                  +--------------------------------+
                     /                          \
          (If audio file)                  (If text string)
                 /                                \
                v                                  v
 +-----------------------------+    +------------------------------+
 | [ACTION] [AI BLOCK]         |    | [CHECK] Evaluate             |
 | RUN speech_to_text()        |    | 'structure_level'            |
 | Converts audio to raw text  |    | (Free-text vs menu press)    |
 +-----------------------------+    +------------------------------+
                 \                                /        |
                  \                              /         | (If menu
                   v                            v          | option)
               (If unstructured natural language)          |
                             |                             |
                             v                             v
                  +--------------------------------+   [Bypass AI]
                  | [ACTION] [AI BLOCK]            |       |
                  | RUN structured_extract() (SLM) |       |
                  | EMITS: ai_confidence_score     |       |
                  +--------------------------------+       |
                                  |                        |
                                  v                        v
                  +--------------------------------+       |
                  | [STATE] JSON Intent Payload    |<------+
                  | Ready (e.g., "apply_subsidy")  |
                  +--------------------------------+
                                  |
                                  v
  ================================================================
  | [CHECK] INTAKE VALIDATION GATE                               |
  | Evaluates: extracted intent & missing_entities               |
  ================================================================
          /                       |                      \
 (If Intent != Application) (If Missing Entities)   (If Valid Application)
        /                         |                        \
       v                          v                         v
 +--------------------+  +--------------------+             |
 | [ACTION] ROUTE AWAY|  | [ACTION] TRIGGER   |             |
 | (e.g., Redirect to |  | CONVERSATIONAL LOOP|             |
 | grievance flow)    |  | (Prompt for info)  |             |
 +--------------------+  +--------------------+             |
                                                            |
                                                            v
                                            +--------------------------------+
                                            | [ACTION] [DPI BLOCK]           |
                                            | identity_verify() (Aadhaar)    |
                                            +--------------------------------+
                                                            |
                                                            v
                                            +--------------------------------+
                                            | [ACTION] [DPI BLOCK]           |
                                            | eligibility_verify() (KISAN)   |
                                            | EMITS: eligibility_status      |
                                            +--------------------------------+
                                                            |
                                                            v
                                            +--------------------------------+
                                            | [ACTION] [DPI BLOCK]           |
                                            | submit_application()           |
                                            | (Logs Case in OpenSPP)         |
                                            +--------------------------------+
                                                            |
                                                            v
  =========================================================================
  | [CHECK] GOVERNANCE ROUTING ENGINE (Deterministic Matrix)              |
  | Evaluates: ai_confidence_score + eligibility_status                   |
  =========================================================================
          /                         |                         \
 (If >95% + Eligible)    (If 60-94% OR fuzzy ID)   (If Ineligible OR <60%)
        /                           |                           \
       v                            v                            v
 +-------------------------+  +--------------------+  +--------------------+
 | [ACTION] [DPI BLOCK]    |  | [ACTION] HUMAN     |  | [ACTION] AUTO-     |
 | payments.disburse()     |  | REVIEW GATE        |  | REJECT GATE        |
 | (PFMS/APBS Payout)      |  | Escalate to Officer|  | Set case REJECTED  |
 +-------------------------+  +--------------------+  +--------------------+
       \                            |                          /
        \                           |                         /
         v                          v                        v
      +---------------------------------------------------------+
      | [ACTION] Dispatch Notification                          |
      | Routes final status payload back to Channel             |
      +---------------------------------------------------------+
                                  |
                                  v
                  +--------------------------------+
                  | [STATE] Workflow Complete      |
                  +--------------------------------+

```
