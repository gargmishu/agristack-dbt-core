# 1. Export all your visual workflows as individual JSON files
npx n8n export:workflow --backup --published --output=./n8n-config/workflows/

# 2. Export your credential definitions (This saves metadata schemas, NOT your actual private keys)
npx n8n export:credentials --backup --output=./n8n-config/credentials/