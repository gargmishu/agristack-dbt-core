#!/bin/bash
set -e

WORKFLOW_DIR="./n8n-config/workflows"
CREDENTIAL_DIR="./n8n-config/credentials"
SRC_DIR="./src"

if [ ! -d "$WORKFLOW_DIR" ]; then
    echo "❌ Error: Master configuration layout path does not exist."
    exit 1
fi

echo "📥 DIRECTION: Git (Clean .js + JSON Canvas) ──> Local n8n Database"

# 1. Reverse Compilation: Inject your clean JS scripts back into the workflow JSON
for wf_file in "$WORKFLOW_DIR"/*.json; do
    if [ -f "$wf_file" ]; then
        echo "🔧 Packing clean JS source modules into $(basename "$wf_file")..."
        
        # Look for matching .js source files that match node names inside the repository tree
        for js_file in "$SRC_DIR"/*.js; do
            if [ -f "$js_file" ]; then
                # Convert the underscore filename back to standard matching spaces for evaluation
                safe_node_name=$(basename "$js_file" .js)
                node_name=$(echo "$safe_node_name" | tr '_' ' ')
                
                # Convert raw JS text payload into a string-escaped JSON string segment using jq
                js_content=$(jq -Rs . "$js_file")
                
                # Walk the JSON structure and inject the code string exactly where the node name matches
                jq --arg name "$node_name" --arg code "$js_content" \
                  'walk(if type == "object" and .name == $name and has("parameters") then .parameters.jsCode = ($code | fromjson) else . end)' \
                  "$wf_file" > "$wf_file.tmp" && mv "$wf_file.tmp" "$wf_file"
            fi
        done
    fi
done

# 2. Push reassembled blueprints directly into your active n8n instance database
npx n8n import:workflow --input="$WORKFLOW_DIR/"
npx n8n import:credentials --input="$CREDENTIAL_DIR/"

echo "🚀 Local UI canvas hot-reloaded and synchronized with your source changes."
