// 📑 Step 01: Universal Multi-Channel Ingress Normalizer & Consent Verification
const payload = $input.item.json.body || $input.item.json.query || $input.item.json;

// 1. Initial sniffing to determine the incoming communication platform
const channel_type = payload.CallSid ? "IVR_VOICE" : (payload.ingress_channel || "IVR_VOICE");
const session_id = payload.CallSid || payload.session_id || `sess_${Math.random().toString(36).substring(2, 9)}`;

// 2. Declare normalizer destination variables
let source_phone_number = "";
let consent_granted = false;
let custom_channel_payload = null;

// 3. Channel-Specific Extraction Engine
switch (channel_type) {
  case "IVR_VOICE":
    source_phone_number = payload.From || payload.source_phone_number || "";
    const dtmf_input = payload.Digits || payload.ivr_dtmf || "";
    if (dtmf_input === "1") consent_granted = true;
    
    custom_channel_payload = {
      ivr_dtmf_captured: dtmf_input,
      ivr_audio_stream_uri: payload.ivr_audio_stream_uri || `s3://production-carrier-audio-streams/${session_id}.wav`
    };
    break;

  case "WHATSAPP":
    source_phone_number = payload.from || payload.chatId || payload.source_phone_number || "";
    const incoming_text = (payload.text?.body || payload.body || payload.whatsapp_cleartext_string || "").trim();
    if (incoming_text === "I Accept and Authorize Check" || payload.whatsapp_optin === "I Accept and Authorize Check") {
      consent_granted = true;
    }
    
    custom_channel_payload = {
      whatsapp_cleartext_string: incoming_text
    };
    break;

  case "USSD":
    source_phone_number = payload.source_phone_number || "";
    if (payload.ussd_optin === "1" || payload.ussd_input === "1") consent_granted = true;
    
    custom_channel_payload = {
      ussd_collected_payload: {
        farmer_id_cleartext: "[Aadhaar Redacted]", 
        district_name: payload.district_name || "",
        crop_type: payload.crop_type || ""
      }
    };
    break;

  default:
    throw new Error(`Security Violation: Unrecognized or unmapped ingress channel encountered: ${channel_type}`);
}

// 4. Enforce the Consent Gate
if (!consent_granted) {
  throw new Error(`Session Aborted: Explicit opt-in consent verification failed for channel type [${channel_type}]`);
}

// 5. Return Normalized Structure directly to downstream DBT ingestion staging nodes
return {
  json: {
    session_id: session_id,
    channel_type: channel_type,
    source_phone_number: source_phone_number.replace("@c.us", ""), // Clean up carrier tracking text if any
    consent_granted: consent_granted,
    ...custom_channel_payload
  },
  binary: $input.item.binary
};
