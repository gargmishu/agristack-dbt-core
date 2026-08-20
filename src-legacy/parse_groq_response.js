// 📑 Step 02 Output Adapter: parse_groq_response.js
const groq_response = $input.item.json;
// Pull the persistent tracking metadata we forwarded from the upstream execution flow
const upstream_meta = $node["speech_to_text_transcription.js"].json.meta;

return {
  json: {
    session_id: upstream_meta.session_id,
    channel_type: upstream_meta.channel_type,
    source_phone_number: upstream_meta.source_phone_number,
    consent_granted: upstream_meta.consent_granted,

    // Core target output required for Step 03
    unstructured_vernacular_string: groq_response.text || "",

    _meta_stt_metrics: {
      model_adapter: "GROQ_WHISPER_V3_PROXY",
      confidence: 1.0 // Whisper native API returns absolute strings without character-level weight bounds
    }
  }
};
