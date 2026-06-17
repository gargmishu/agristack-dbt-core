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

# 🟢 Append "|| true" to prevent a blank credential database from killing the script
npx n8n export:credentials --backup --output="$CREDENTIAL_DIR/" --user-folder="$USER_FOLDER" 2>/dev/null || true

# 2. Parse manifests and extract clean code blocks
for file in "$WORKFLOW_DIR"/*.json; do
    if [ -f "$file" ]; then
        echo "✂️  Extracting inline code blocks from $(basename "$file")..."
       
        jq -c '.nodes[] | select(.type | startswith("n8n-nodes-base.code")) | {name: .name, code: (.parameters.jsCode // .parameters.code // .parameters.pythonCode)} | select(.code != null)' "$file" | while read -r row; do
            node_name=$(echo "$row" | jq -r '.name')

            # Trim only  accidental leading/trailing spaces so the filesystem doesn't break.
            safe_filename=$(echo "$node_name" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
            
            echo "$row" | jq -r '.code' > "$SRC_DIR/${safe_filename}"
            echo "   💾 Saved clean module: $SRC_DIR/${safe_filename}"
        done

        # Strip ONLY the top-level root metadata properties, keeping your node internal structures perfect
        jq 'del(.id, .createdAt, .updatedAt)' "$file" > "${file}.tmp" && mv "${file}.tmp" "$file"
    fi
done

echo "✅ Export complete. Check your updated ./src/ tree structure!"