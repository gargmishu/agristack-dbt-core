#!/bin/bash

# 🌟 Configurable Endpoint variables
PORT=5678
ENDPOINT_PATH="v1/flows/wf-crop-loss-subsidy/ingress"
FULL_URL="http://localhost:${PORT}/webhook-test/${ENDPOINT_PATH}"

echo "⚡ Dispatching authorized WhatsApp mock payload to n8n ingress gateway..."
echo "🔗 Target URL: ${FULL_URL}"
echo "--------------------------------------------------------"

curl -X POST "${FULL_URL}" \
     -H "Content-Type: application/json" \
     -d '{
       "body": {
         "entry": [
           {
             "changes": [
               {
                 "value": {
                   "messages": [
                     {
                       "id": "ABGGFlA5F60A",
                       "from": "919876543210",
                       "text": {
                         "body": "I Accept and Authorize Check"
                       }
                     }
                   ]
                 }
               }
             ]
           }
         ]
       }
     }'

echo -e "\n--------------------------------------------------------"
echo "🟢 Payload dispatched successfully."