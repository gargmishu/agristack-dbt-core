#!/bin/bash
set -e

WORKFLOW_DIR="./n8n-config/workflows"
CREDENTIAL_DIR="./n8n-config/credentials"
SRC_DIR="./src"

mkdir -p "$WORKFLOW_DIR" "$CREDENTIAL_DIR" "$SRC_DIR"

echo "📤 DIRECTION: Local n8n Database ──> Git (Clean .js + JSON Canvas)"
echo "Serializing active canvas configurations to repository tree..."

# 💡 Bind explicitly to the active Codespace n8n database folder
USER_FOLDER="/home/codespace/.n8n"

# 1. Standard structural metadata dump out of matching database path
npx n8n export:workflow --backup --output="$WORKFLOW_DIR/" --user-folder="$USER_FOLDER"
npx n8n export:credentials --backup --output="$CREDENTIAL_DIR/" --user-folder="$USER_FOLDER"

# 2. Parse JSON manifests, extract code blocks, and normalize layout parameters
for file in "$WORKFLOW_DIR"/*.json; do
    if [ -f "$file" ]; then
        echo "✂️  Extracting inline code blocks from $(basename "$file")..."
        
        # Locate all Code Nodes and dump their jsCode payloads into unescaped .js files
        jq -c '.nodes[] | select(.type == "n8n-nodes-base.code" and .parameters.jsCode != null) | {name: .name, code: .parameters.jsCode}' "$file" | while read -r row; do
            node_name=$(echo "$row" | jq -r '.name')
            # Normalize filename: replace spaces/special chars with underscores
            safe_name=$(echo "$node_name" | tr '[:space:]' '_')
            echo "$row" | jq -r '.code' > "$SRC_DIR/${safe_name}.js"
            echo "   💾 Saved clean module: $SRC_DIR/${safe_name}.js"
        done

        # Strip dynamic instance metrics to keep git diffs completely clean and green
        jq 'walk(if type == "object" then del(.id, .createdAt, .updatedAt) else . end)' "$file" > "${file}.tmp" && mv "${file}.tmp" "$file"
    fi
done

echo "✅ Export complete. Run 'git status' to inspect your clean code tracking layout."