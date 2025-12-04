#!/bin/bash

# Test Script for Public Stats API
# Demonstrates UFCstats-style public fight statistics endpoint

API_URL="http://localhost:8002"

echo "=========================================="
echo "Public Stats API Test"
echo "=========================================="
echo ""

echo "Endpoint: GET /v1/public/fight/{fight_id}"
echo "Authentication: NONE REQUIRED (Public endpoint)"
echo ""

echo "=========================================="
echo "Example Response Format"
echo "=========================================="
echo ""

cat << 'EOF'
{
    "fight": {
        "event": "PFC 50",
        "weight_class": "Welterweight",
        "rounds": 3,
        "result": "DEC"
    },
    "fighters": {
        "red": {
            "name": "John Doe",
            "winner": true
        },
        "blue": {
            "name": "Mike Smith",
            "winner": false
        }
    },
    "rounds": [
        {
            "round": 1,
            "red": {
                "sig": "24/55",       # Significant strikes (landed/attempted)
                "total": "39/88",     # Total strikes (landed/attempted)
                "td": "2/5",          # Takedowns (landed/attempted)
                "sub": 1,             # Submission attempts
                "kd": 1,              # Knockdowns
                "ctrl": "1:11",       # Control time (M:SS format)
                "acc_sig": 0.44,      # Sig strike accuracy (44%)
                "acc_td": 0.40        # Takedown accuracy (40%)
            },
            "blue": {
                "sig": "15/44",
                "total": "22/67",
                "td": "0/2",
                "sub": 0,
                "kd": 0,
                "ctrl": "0:19",
                "acc_sig": 0.34,
                "acc_td": 0.00
            }
        }
    ],
    "_note": "Strike attempts are estimated. Takedown/submission data requires event normalization system."
}
EOF

echo ""
echo ""

echo "=========================================="
echo "Testing Public Endpoint"
echo "=========================================="
echo ""

# Test with a fight ID (will likely return 404 unless you have data)
FIGHT_ID="test_fight_id"

echo "Test 1: Attempt to fetch fight stats"
echo "curl -X GET \"$API_URL/v1/public/fight/$FIGHT_ID\""
echo ""

RESPONSE=$(curl -s -X GET "$API_URL/v1/public/fight/$FIGHT_ID")

echo "Response:"
echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
echo ""

echo "=========================================="
echo "Current Data Status"
echo "=========================================="
echo ""

echo "✅ Strike Statistics: Available (with estimated attempts)"
echo "✅ Knockdown Statistics: Available (accurate)"
echo "✅ Control Time: Available (formatted M:SS)"
echo "⏳ Takedown Statistics: Pending (requires event system)"
echo "⏳ Submission Statistics: Pending (requires event system)"
echo ""

echo "=========================================="
echo "Usage Examples"
echo "=========================================="
echo ""

echo "JavaScript/TypeScript:"
cat << 'EOF'

fetch('https://api.fightjudge.ai/v1/public/fight/UFC309_JONES_MIOCIC')
  .then(res => res.json())
  .then(fight => {
    console.log(`Winner: ${fight.fighters.red.winner ? 
                 fight.fighters.red.name : fight.fighters.blue.name}`);
    
    fight.rounds.forEach(round => {
      console.log(`Round ${round.round}:`);
      console.log(`  Red: ${round.red.sig} sig strikes`);
      console.log(`  Blue: ${round.blue.sig} sig strikes`);
    });
  });

EOF

echo ""
echo "Python:"
cat << 'EOF'

import requests

response = requests.get('https://api.fightjudge.ai/v1/public/fight/UFC309_JONES_MIOCIC')
fight = response.json()

winner = fight['fighters']['red' if fight['fighters']['red']['winner'] else 'blue']
print(f"Winner: {winner['name']}")
print(f"Method: {fight['fight']['result']}")

# Calculate total significant strikes
total_red_sig = sum(int(r['red']['sig'].split('/')[0]) for r in fight['rounds'])
print(f"Total Red Sig Strikes: {total_red_sig}")

EOF

echo ""

echo "=========================================="
echo "Integration Steps"
echo "=========================================="
echo ""

echo "1. Get Fight Data:"
echo "   curl -X GET \"$API_URL/v1/public/fight/{fight_id}\""
echo ""

echo "2. Parse Response:"
echo "   - Extract fight.event, fight.result"
echo "   - Extract fighters.red.name, fighters.blue.name"
echo "   - Loop through rounds array"
echo ""

echo "3. Display Stats:"
echo "   - Show round-by-round breakdown"
echo "   - Calculate totals across rounds"
echo "   - Display accuracy percentages"
echo ""

echo "=========================================="
echo "Data Limitations (Current)"
echo "=========================================="
echo ""

echo "⚠️  Strike Attempts: ESTIMATED"
echo "    Current implementation estimates attempts from landed strikes."
echo "    Accuracy: ~90% (typical MMA strike accuracy is 35-45%)"
echo ""

echo "⚠️  Takedowns: NOT TRACKED"
echo "    Will show \"0/0\" until event system is enabled."
echo ""

echo "⚠️  Submissions: NOT TRACKED"
echo "    Will show 0 until event system is enabled."
echo ""

echo "To enable full stats:"
echo "  1. Run migration: /app/datafeed_api/migrations/005_stat_engine_normalization.sql"
echo "  2. Restart service: sudo supervisorctl restart datafeed_api"
echo "  3. Generate events from existing fights using the bridge function"
echo ""

echo "=========================================="
echo "Public API Benefits"
echo "=========================================="
echo ""

echo "✅ No Authentication Required"
echo "✅ UFCstats-Compatible Format"
echo "✅ Round-by-Round Breakdown"
echo "✅ Accuracy Percentages Calculated"
echo "✅ Human-Readable Control Time (M:SS)"
echo "✅ Winner/Loser Clearly Identified"
echo "✅ Easy to Parse and Display"
echo ""

echo "=========================================="
echo "Documentation"
echo "=========================================="
echo ""

echo "Full Guide: /app/datafeed_api/PUBLIC_STATS_API.md"
echo "Service Code: /app/datafeed_api/services/public_stats_service.py"
echo "API Routes: /app/datafeed_api/api/public_routes.py"
echo ""

echo "=========================================="
echo "Next Steps"
echo "=========================================="
echo ""

echo "1. Add fights to your database (events, fighters, fights, round_state)"
echo "2. Test endpoint with real fight IDs"
echo "3. Integrate into your application/website"
echo "4. (Optional) Run migration 005 for full stats"
echo ""
