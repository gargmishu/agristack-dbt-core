#!/bin/bash
set -e

# Configuration Tracking Matrices
WORKFLOW_DIR="./n8n-config/workflows"
CREDENTIAL_DIR="./n8n-config/credentials"
SRC_DIR="./src-legacy"
USER_FOLDER="/home/codespace/.n8n"
MASTER_DUMP="${WORKFLOW_DIR}/all_exported_workflows.json"

# Ensure runtime workspace tree is initialized
mkdir -p "$WORKFLOW_DIR" "$CREDENTIAL_DIR" "$SRC_DIR"

echo "📤 DIRECTION: Local n8n Database ──> Git (Deterministic Extraction)"
echo "Querying local system vault engine at: $USER_FOLDER"

# 1. Atomic Database Dump to a single trusted tracking array
npx n8n export:workflow --all --output="$MASTER_DUMP" --user-folder="$USER_FOLDER"
npx n8n export:credentials --backup --output="$CREDENTIAL_DIR/" --user-folder="$USER_FOLDER" 2>/dev/null || true

# 2. Parse the verified index names directly out of the database array matrix
workflow_names=$(jq -r '.[] | select(.active == true) | .name' "$MASTER_DUMP")

echo "$workflow_names" | while read -r name; do
    if [ -n "$name" ] && [ "$name" != "null" ]; then
        # Normalize the name string for the standard unix file structure
        safe_name=$(echo "$name" | sed 's/[[:space:]]/_/g' | sed 's/[^a-zA-Z0-9__-]//g')
        target_json="${WORKFLOW_DIR}/${safe_name}.json"

        echo "🔀 Unpacking and normalising: [$name] ──> ${target_json}"

        # Isolate the specific canvas schema block from the master file and drop transient metadata tags
        jq --arg wf_name "$name" '.[] | select(.name == $wf_name) | del(.id, .createdAt, .updatedAt)' "$MASTER_DUMP" > "$target_json"

        # ✂️ Extract clean, standalone JavaScript code blocks from the node tree
        jq -c '.nodes[] | select(.type | startswith("n8n-nodes-base.code")) | {name: .name, code: (.parameters.jsCode // .parameters.code)} | select(.code != null)' "$target_json" | while read -r row; do
            node_name=$(echo "$row" | jq -r '.name')

            # Trim accidental whitespace and remove an existing .js suffix if present to prevent double extensions
            base_filename=$(echo "$node_name" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' | sed 's/\.js$//i')

            # 🌟 FIX: Deterministically enforce the .js extension
            final_filename="${base_filename}.js"

            echo "$row" | jq -r '.code' > "${SRC_DIR}/${final_filename}"
            echo "   💾 Saved decoupled module: ${SRC_DIR}/${final_filename}"
        done
    fi
done

# 3. Clean up the temporary combined master database file
rm -f "$MASTER_DUMP"

echo "✅ Pipeline script execution complete. All tracking targets aligned!"
