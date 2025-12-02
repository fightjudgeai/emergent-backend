#!/bin/bash

# Test script for Fight Judge AI Data Feed API
# Run this after loading dummy data into Supabase

echo "=========================================="
echo "🧪 Fight Judge AI Data Feed API Tests"
echo "=========================================="
echo ""

# Check if server is running
echo "1. Checking if API server is running..."
response=$(curl -s http://localhost:8002/health)
if [ $? -eq 0 ]; then
    echo "✅ API server is responding"
    echo "   Response: $response"
else
    echo "❌ API server is not responding"
    echo "   Please start with: cd /app/datafeed_api && python main.py"
    exit 1
fi

echo ""
echo "2. Getting API keys from database..."
echo "   Run this in Supabase SQL Editor:"
echo "   SELECT name, api_key, scope FROM api_clients ORDER BY scope;"
echo ""
echo "   Then export one as:"
echo "   export API_KEY='your_api_key_here'"
echo ""

# Check if API_KEY is set
if [ -z "$API_KEY" ]; then
    echo "⚠️  API_KEY environment variable not set"
    echo "   Please run: export API_KEY='your_api_key_here'"
    echo ""
    echo "Continuing with test endpoints that don't require auth..."
    echo ""
else
    echo "✅ API_KEY is set"
    echo ""
fi

echo "=========================================="
echo "3. Testing REST Endpoints"
echo "=========================================="
echo ""

# Test root endpoint
echo "📍 GET / (root)"
curl -s http://localhost:8002/ | python3 -m json.tool
echo ""

if [ -n "$API_KEY" ]; then
    echo "📍 GET /v1/events/PFC50"
    curl -s -H "Authorization: Bearer $API_KEY" \
        http://localhost:8002/v1/events/PFC50 | python3 -m json.tool
    echo ""
    
    echo "📍 GET /v1/fights/PFC50-F1/live"
    curl -s -H "Authorization: Bearer $API_KEY" \
        http://localhost:8002/v1/fights/PFC50-F1/live | python3 -m json.tool
    echo ""
    
    echo "📍 GET /v1/fights/PFC50-F2/live"
    curl -s -H "Authorization: Bearer $API_KEY" \
        http://localhost:8002/v1/fights/PFC50-F2/live | python3 -m json.tool
    echo ""
    
    # Test timeline (requires sportsbook.pro scope)
    echo "📍 GET /v1/fights/PFC50-F1/timeline (requires sportsbook.pro)"
    curl -s -H "Authorization: Bearer $API_KEY" \
        http://localhost:8002/v1/fights/PFC50-F1/timeline | python3 -m json.tool
    echo ""
fi

echo "=========================================="
echo "4. WebSocket Test Instructions"
echo "=========================================="
echo ""
echo "To test WebSocket, use this JavaScript in browser console:"
echo ""
echo "const ws = new WebSocket('ws://localhost:8002/v1/realtime');"
echo "ws.onopen = () => {"
echo "  console.log('Connected!');"
echo "  ws.send(JSON.stringify({type: 'auth', api_key: 'YOUR_API_KEY'}));"
echo "};"
echo "ws.onmessage = (e) => {"
echo "  const msg = JSON.parse(e.data);"
echo "  console.log('Received:', msg);"
echo "  if (msg.type === 'auth_ok') {"
echo "    ws.send(JSON.stringify({type: 'subscribe', channel: 'fight', filters: {fight_code: 'PFC50-F1'}}));"
echo "  }"
echo "};"
echo ""

echo "=========================================="
echo "✅ Test script complete"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Get API keys from Supabase"
echo "2. Export API_KEY environment variable"
echo "3. Run this script again: ./test_api.sh"
echo "4. Test WebSocket connection"
echo ""
