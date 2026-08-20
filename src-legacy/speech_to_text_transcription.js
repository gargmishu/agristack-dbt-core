// 📑 Step 02: speech_to_text_transcription.js (Groq ASR Proxy Config)
const payload = $input.item.json.body || $input.item.json;

// 1. Enforce Execution Condition
if (payload.channel_type !== "IVR_VOICE" && !payload.CallSid) {
  return {
    json: {
      ...payload,
      unstructured_vernacular_string: "",
      _meta_stt_status: "SKIPPED_CHANNEL_NON_VOICE"
    }
  };
}

// 2. Extract Session Meta
const session_id = payload.session_id || payload.CallSid || `sess_${Math.random().toString(36).substring(2, 9)}`;
const source_phone = payload.source_phone_number || "";

// 3. RETURN BOTH JSON AND UPSTREAM BINARY OBJECTS
return {
  json: {
    meta: {
      session_id: session_id,
      source_phone_number: source_phone,
      channel_type: "IVR_VOICE",
      consent_granted: true
    },
    groq_config: {
      model: "whisper-large-v3",
      language: "hi",
      response_format: "json"
    }
  },
  // Forward the binary file array ('data') downstream to Groq
  binary: $input.item.binary
};
