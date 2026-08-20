#!/bin/bash
set -e

# Core Local Target Settings
TEST_URL="http://localhost:5678/webhook-test/v1/wf-crop-loss-subsidy/ingress"
AUDIO_PATH="./n8n-config/test_audio/ambala-call-771a.mp3"
ENV_FILE="./.env"

print_header() {
    echo -e "\n=========================================================="
    echo -e "🔮 RUNNING END-TO-END PIPELINE SYSTEM TEST"
    echo -e "=========================================================="
}

# 🛠️ Step 1: Pre-execution Environmental Readiness Check
print_header "Step 1: Checking Workspace Secrets Configuration"

if [ -f "$ENV_FILE" ]; then
    echo "💾 Local environment configuration discovered at: $ENV_FILE"
    # Safely source variable maps into this sub-shell execution environment
    set -a; source "$ENV_FILE"; set +a
else
    echo "❌ ERROR: No .env configuration file found in the project root."
    echo "Please configure your environment credentials before running this pipeline."
    exit 1
fi

if [ -z "$GROQ_API_KEY" ]; then
    echo "❌ ERROR: GROQ_API_KEY is not defined inside your local .env bundle."
    exit 1
else
    echo "✅ Success: API environment token validated."
fi

# 🛠️ Step 2: Validate Audio Ingress Asset State
print_header "Step 2: Checking Local Speech Matrix Allocation"

# Fallback checking if user is using wav or mp3 format paths
if [ ! -f "$AUDIO_PATH" ]; then
    AUDIO_PATH="./n8n-config/test_audio/ambala-call-771a.wav"
fi

if [ -f "$AUDIO_PATH" ]; then
    file_size=$(ls -lh "$AUDIO_PATH" | awk '{print $5}')
    echo "🎵 Spoken audio track discovered: $AUDIO_PATH ($file_size)"
else
    echo "❌ ERROR: Binary test file target missing at: $AUDIO_PATH"
    echo "Run 'python scripts/generate_sample_audio.py' first to synthesize test audio."
    exit 1
fi

# 🛠️ Step 3: Fire the Live E2E Multi-Part Network Request
print_header "Step 3: Dispatching Live Form-Data Request to n8n Ingress Webhook"

echo -e "Target Webhook: $TEST_URL"
echo -e "Payload Strategy: Multi-part Form Data Routing Array\n"

# Execute the call using the required form fields alongside the binary attachment stream
curl -i -X POST "$TEST_URL" \
  -F "ingress_channel=IVR_VOICE" \
  -F "source_phone_number=+919999999999" \
  -F "ivr_dtmf=1" \
  -F "data=@${AUDIO_PATH}"

echo -e "\n\n=========================================================="
echo -e "🏁 E2E Transaction completed. Check your n8n canvas output panels!"
echo -e "=========================================================="
