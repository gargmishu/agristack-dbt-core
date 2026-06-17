// 📑 Step 01: Universal Multi-Channel Ingress Normalizer & Consent Verification
const payload = $input.item.json.body || $input.item.json;


const session_id = payload.session_id || `session_generated_${Date.now()}`;
const channel_type = payload.ingress_channel || "IVR_VOICE";
const source_phone_number = payload.source_phone_number || "";

// Evaluate channel-specific consent indicators per specification
let consent_granted = false;
if (channel_type === "IVR_VOICE" && payload.ivr_dtmf === "1") consent_granted = true;
if (channel_type === "WHATSAPP" && payload.whatsapp_optin === "I Accept and Authorize Check") consent_granted = true;
if (channel_type === "USSD" && payload.ussd_optin === "1") consent_granted = true;

if (!consent_granted) {
  throw new Error(`Session Aborted: Citizen explicit opt-in consent rejected on channel ${channel_type}`);
}

// 📦 Extracted Data Payload Schema (PII Scrubbed at Edge)
const structuredUssdData = channel_type === "USSD" ? {
  farmer_id_cleartext: "[Aadhaar Redacted]", 
  district_name: payload.district_name || "",
  crop_type: payload.crop_type || ""
} : null;

return {
  json: {
    session_id: session_id,
    channel_type: channel_type,
    source_phone_number: source_phone_number,
    consent_granted: consent_granted,
    ussd_collected_payload: structuredUssdData,
    ivr_audio_stream_uri: payload.ivr_audio_stream_uri || null,
    whatsapp_cleartext_string: payload.whatsapp_cleartext_string || null
    }
};



