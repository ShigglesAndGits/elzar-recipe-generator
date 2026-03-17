#!/bin/bash
set -e

echo "=============================================="
echo "  Elzar - AI Recipe Generator for Grocy"
echo "  BAM! Let's kick it up a notch!"
echo "=============================================="

# Ensure data directory exists and has correct permissions
mkdir -p /app/data
chmod 755 /app/data

# Validate environment variables
# Grocy is optional (app works without it per Grocy-free audit)
# LLM settings can be configured via env vars OR the Settings UI (stored in SQLite)
if [ -z "$LLM_API_URL" ] && [ -z "$LLM_API_KEY" ] && [ -z "$LLM_MODEL" ]; then
    echo "NOTE: No LLM env vars set. Configure via Settings UI or provide LLM_API_URL, LLM_API_KEY, LLM_MODEL."
fi

echo "Configuration:"
echo "  - Grocy URL: ${GROCY_URL:-(not set, configure in Settings)}"
echo "  - LLM API: ${LLM_API_URL:-(not set, configure in Settings)}"
echo "  - LLM Model: ${LLM_MODEL:-(not set, configure in Settings)}"
echo "  - Unit Preference: ${UNIT_PREFERENCE:-imperial}"
echo "  - Max History: ${MAX_RECIPE_HISTORY:-1000}"
echo ""
echo "Starting services..."

# Execute the main command (supervisord)
exec "$@"
