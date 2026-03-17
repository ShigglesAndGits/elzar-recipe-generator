#!/bin/bash
set -e

echo "=============================================="
echo "  Elzar - AI Recipe Generator for Grocy"
echo "  BAM! Let's kick it up a notch!"
echo "=============================================="

# Ensure data directory exists and has correct permissions
mkdir -p /app/data
chmod 755 /app/data

# Validate required environment variables
if [ -z "$GROCY_URL" ]; then
    echo "ERROR: GROCY_URL environment variable is required"
    exit 1
fi

if [ -z "$GROCY_API_KEY" ]; then
    echo "ERROR: GROCY_API_KEY environment variable is required"
    exit 1
fi

if [ -z "$LLM_API_URL" ]; then
    echo "ERROR: LLM_API_URL environment variable is required"
    exit 1
fi

if [ -z "$LLM_API_KEY" ]; then
    echo "ERROR: LLM_API_KEY environment variable is required"
    exit 1
fi

if [ -z "$LLM_MODEL" ]; then
    echo "ERROR: LLM_MODEL environment variable is required"
    exit 1
fi

echo "Configuration:"
echo "  - Grocy URL: $GROCY_URL"
echo "  - LLM API: $LLM_API_URL"
echo "  - LLM Model: $LLM_MODEL"
echo "  - Unit Preference: ${UNIT_PREFERENCE:-imperial}"
echo "  - Max History: ${MAX_RECIPE_HISTORY:-50}"
echo ""
echo "Starting services..."

# Execute the main command (supervisord)
exec "$@"
