#!/bin/bash

# Test Script for Stat Engine Normalization API
# This script tests the new event stream endpoints

API_URL="http://localhost:8002"
API_KEY="FJAI_DEMO_SPORTSBOOK_001"  # Using sportsbook.pro scope

echo "=========================================="
echo "Stat Engine Normalization API Test"
echo "=========================================="
echo ""

# Test 1: Get event stream summary (will be empty until migration is run)
echo "Test 1: Get event stream summary"
echo "GET /v1/events/{fight_id}/summary"
echo ""

# Note: We need a valid fight_id from the database
# Let's first get a fight from the events endpoint
FIGHT_CODE="UFC309_JONES_MIOCIC"

# Get fight details first to extract fight ID
echo "Getting fight details for $FIGHT_CODE..."
FIGHT_RESPONSE=$(curl -s -X GET "$API_URL/v1/fights/$FIGHT_CODE/live" \
  -H "Authorization: Bearer $API_KEY")

# Extract fight ID using Python (more reliable than jq)
FIGHT_ID=$(echo "$FIGHT_RESPONSE" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    # We'll need to get the fight ID from the database
    print('Need to query database for fight_id')
except:
    print('Error parsing response')
")

echo "Note: Fight ID extraction requires a valid fight in the database."
echo ""

echo "=========================================="
echo "Test 2: Validate control time"
echo "GET /v1/events/{fight_id}/round/1/control-validation"
echo ""
echo "This endpoint validates control time integrity:"
echo "- RED + BLUE control ≤ 300 seconds"
echo "- No overlapping control periods"
echo ""
echo "Note: Requires migration 005 to be run first"
echo ""

echo "=========================================="
echo "Test 3: Aggregate stats from events"
echo "GET /v1/events/{fight_id}/round/1/aggregate"
echo ""
echo "This endpoint rebuilds cumulative stats from events"
echo "(reverse operation of generate-from-round-state)"
echo ""
echo "Note: Requires migration 005 to be run first"
echo ""

echo "=========================================="
echo "Test 4: Generate events from round state"
echo "POST /v1/events/generate-from-round-state"
echo ""

# This test requires a valid fight_id, so we'll demonstrate the payload
cat << 'EOF'
Example payload:
{
    "fight_id": "uuid-from-database",
    "round_num": 1,
    "round_state": {
        "red_sig_strikes": 25,
        "blue_sig_strikes": 18,
        "red_knockdowns": 1,
        "blue_knockdowns": 0,
        "red_control_sec": 120,
        "blue_control_sec": 45
    }
}

This will create granular events distributed across the round.
EOF
echo ""

echo "=========================================="
echo "IMPORTANT: Migration Required"
echo "=========================================="
echo ""
echo "The Stat Engine Normalization features require running migration:"
echo "  /app/datafeed_api/migrations/005_stat_engine_normalization.sql"
echo ""
echo "To run the migration:"
echo "  1. Go to your Supabase Dashboard"
echo "  2. Open SQL Editor"
echo "  3. Copy and paste the contents of the migration file"
echo "  4. Execute the SQL"
echo ""
echo "After running the migration, the following will be available:"
echo "  - fight_events table for granular event tracking"
echo "  - Event type normalization functions"
echo "  - Deterministic control time calculation"
echo "  - Control overlap validation"
echo ""

echo "=========================================="
echo "API Endpoints Available"
echo "=========================================="
echo ""
echo "Base URL: $API_URL/v1"
echo ""
echo "Events API:"
echo "  GET  /events/{fight_id}"
echo "  GET  /events/{fight_id}/summary"
echo "  GET  /events/{fight_id}/round/{round_num}/aggregate"
echo "  GET  /events/{fight_id}/round/{round_num}/control-validation"
echo "  POST /events/generate-from-round-state"
echo ""
echo "For detailed documentation, see:"
echo "  /app/datafeed_api/STAT_ENGINE_NORMALIZATION_GUIDE.md"
echo ""
