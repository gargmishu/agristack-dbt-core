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

USER_FOLDER="/home/codespace/.n8n"

# 1. Reverse Compilation: Inject your clean JS scripts back into the workflow JSON
for wf_file in "$WORKFLOW_DIR"/*.json; do
    if [ -f "$wf_file" ]; then
        echo "🔧 Packing clean JS source modules into $(basename "$wf_file")..."

        for js_file in "$SRC_DIR"/*; do
            if [ -f "$js_file" ]; then
                node_name=$(basename "$js_file")
                
                echo "   📦 Compiling logic for: [$node_name]"
                js_content=$(jq -Rs . "$js_file")
                
                jq --arg name "$node_name" --arg code "$js_content" \
                  'walk(if type == "object" and .name == $name and has("parameters") then .parameters.jsCode = ($code | fromjson) else . end)' \
                  "$wf_file" > "$wf_file.tmp" && mv "$wf_file.tmp" "$wf_file"
            fi
        done
    fi
done

#2: Only import workflows if individual json files exist
if [ -n "$(ls -A "$WORKFLOW_DIR"/*.json 2>/dev/null)" ]; then
    for json_file in "$WORKFLOW_DIR"/*.json; do
        echo "📥 Pushing manifest to database: $(basename "$json_file")"
        
        # 🟢 CHANGED: Re-inject a clean structural ID if it was stripped, using the filename prefix hash
        filename_hash=$(basename "$json_file" .json)
        jq --arg id "$filename_hash" '.id = $id' "$json_file" > "$json_file.import.tmp"
        
        # Run the import against the temporary file that contains the valid ID schema
        npx n8n import:workflow --input="$json_file.import.tmp" --user-folder="$USER_FOLDER"
        rm -f "$json_file.import.tmp"
    done
else
    echo "⚠️  No workflows found to import. Skipping."
fi

#3: Only import credentials if files exist
if [ -n "$(ls -A "$CREDENTIAL_DIR"/*.json 2>/dev/null)" ]; then
    for cred_file in "$CREDENTIAL_DIR"/*.json; do
        npx n8n import:credentials --input="$cred_file" --user-folder="$USER_FOLDER" 2>/dev/null || true
    done
else
    echo "⏭️  Credentials empty. Skipping safely."
fi

echo "🚀 Local UI canvas hot-reloaded and synchronized with your source changes."

