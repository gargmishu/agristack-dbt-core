#!/bin/bash

# Standard endpoints
TEST_URL="http://localhost:5678/webhook-test/api/v1/webhooks/v1/dpi-ingress"
PROD_URL="http://localhost:5678/webhook/api/v1/webhooks/v1/dpi-ingress"

print_header() {
    echo -e "\n========================================================"
    echo -e "🚀 RUNNING SYSTEM TEST: $1"
    echo -e "========================================================"
}

# 📡 Universal HTTP Post Execution Engine
send_payload() {
    local channel_name=$1
    local payload_data=$2
    
    echo -e "Target Endpoint: $TEST_URL"
    echo -e "Sending Channel: $channel_name\n"
    
    curl -i -X POST "$TEST_URL" \
      -H "Content-Type: application/json" \
      -d "$payload_data"
    
    echo -e "\n\n✅ Execution request dispatched."
}

# ==========================================================================
# 🛠️ DISCRETE ISOLATED TEST CASE FUNCTIONS
# ==========================================================================

run_ivr_test() {
    print_header "IVR Voice Pathway (Triggers Bhashini Speech-to-Text Branch)"
    
    local ivr_data='{
      "ingress_channel": "IVR_VOICE",
      "source_phone_number": "+919999999999",
      "ivr_dtmf": "1",
      "ivr_audio_stream_uri": "s3://gov-ingress-audio-buckets/2026/ambala-call-771a.pcm"
    }'
    
    send_payload "IVR_VOICE" "$ivr_data"
}

run_whatsapp_test() {
    print_header "WhatsApp Messaging Pathway (Bypasses Voice, Supplies Cleartext)"
    
    local whatsapp_data='{
      "ingress_channel": "WHATSAPP",
      "source_phone_number": "+919876543210",
      "whatsapp_optin": "I Accept and Authorize Check",
      "whatsapp_cleartext_string": "Mera dhan ka khet kharab ho gaya hai jila Ambala me"
    }'
    
    send_payload "WHATSAPP" "$whatsapp_data"
}

run_ussd_test() {
    print_header "USSD Signaling Pathway (Direct Structural Extraction Sync)"
    
    local ussd_data='{
      "ingress_channel": "USSD",
      "source_phone_number": "+918888888888",
      "ussd_optin": "1",
      "district_name": "Ambala",
      "crop_type": "Paddy"
    }'
    
    send_payload "USSD" "$ussd_data"
}

# Simple routing switch based on execution arguments
case "$1" in
    ivr)      run_ivr_test ;;
    whatsapp) run_whatsapp_test ;;
    ussd)     run_ussd_test ;;
    *)        
        echo -e "⚠️  Invalid option or no arguments provided."
        echo -e "Usage: ./test_ingress_channels.sh [ivr|whatsapp|ussd]"
        exit 1
        ;;
esac
