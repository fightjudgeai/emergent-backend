# Real-Time Fantasy & Sportsbook API Guide

## 🎯 Overview

The API now includes streamlined endpoints and WebSocket enhancements for real-time fantasy points and market data.

---

## 📡 New REST Endpoints

### 1. GET /api/fantasy/{fight_id}/{profile_id}

**Description:** Get fantasy points breakdown for a fight

**Path Parameters:**
- `fight_id`: Fight code (e.g., `PFC50-F1`) or UUID
- `profile_id`: Scoring profile (e.g., `fantasy.basic`, `fantasy.advanced`, `sportsbook.pro`)

**Example Request:**
```bash
curl http://localhost:8002/api/fantasy/PFC50-F1/fantasy.basic | jq
```

**Response:**
```json
{
  "fight_code": "PFC50-F1",
  "fight_id": "uuid",
  "profile_id": "fantasy.basic",
  "fantasy_points": {
    "red": 84.5,
    "blue": 63.2
  },
  "breakdown": {
    "red": {
      "base_points": {
        "sig_strikes": 20.0,
        "knockdowns": 5.0,
        "control": 2.5
      },
      "bonuses": {
        "win": 10.0,
        "finish": 15.0,
        "ko": 5.0
      },
      "summary": {
        "grand_total": 84.5
      }
    },
    "blue": {
      "base_points": {...},
      "bonuses": {...},
      "summary": {
        "grand_total": 63.2
      }
    }
  }
}
```

---

### 2. GET /api/markets/{fight_id}

**Description:** Get market summary with settlements for a fight

**Path Parameters:**
- `fight_id`: Fight code (e.g., `PFC50-F1`) or UUID

**Example Request:**
```bash
curl http://localhost:8002/api/markets/PFC50-F1 | jq
```

**Response:**
```json
{
  "fight_code": "PFC50-F1",
  "fight_id": "uuid",
  "markets": {
    "WINNER": {
      "status": "SETTLED",
      "params": {"red_odds": 1.75, "blue_odds": 2.10},
      "winner_side": "RED",
      "method": "KO",
      "round": 2,
      "time": "3:15"
    },
    "TOTAL_SIG_STRIKES": {
      "status": "SETTLED",
      "params": {"line": 50.5, "over_odds": 1.91, "under_odds": 1.91},
      "line": 50.5,
      "actual": 82,
      "winning_side": "OVER",
      "red_sig_strikes": 40,
      "blue_sig_strikes": 42
    },
    "KD_OVER_UNDER": {
      "status": "SETTLED",
      "params": {"line": 0.5, "over_odds": 2.50, "under_odds": 1.50},
      "line": 0.5,
      "actual": 1,
      "winning_side": "OVER",
      "red_knockdowns": 1,
      "blue_knockdowns": 0
    }
  }
}
```

---

## 🔌 WebSocket Enhancement

### Injected Data

WebSocket messages now automatically include **fantasy_points** and **markets** data!

**Before:**
```json
{
  "type": "round_state",
  "payload": {
    "round": 2,
    "red": {"strikes": 40, "knockdowns": 1},
    "blue": {"strikes": 30, "knockdowns": 0}
  }
}
```

**After (Enhanced):**
```json
{
  "type": "round_state",
  "payload": {
    "round": 2,
    "red": {"strikes": 40, "knockdowns": 1},
    "blue": {"strikes": 30, "knockdowns": 0}
  },
  "fantasy_points": {
    "fantasy.basic": {
      "red": 84.5,
      "blue": 63.2
    },
    "fantasy.advanced": {
      "red": 96.8,
      "blue": 72.1
    },
    "sportsbook.pro": {
      "red": 112.5,
      "blue": 84.3
    }
  },
  "markets": {
    "WINNER": {
      "status": "OPEN"
    },
    "TOTAL_SIG_STRIKES": {
      "status": "OPEN",
      "line": 50.5
    },
    "KD_OVER_UNDER": {
      "status": "SETTLED",
      "line": 0.5,
      "actual": 1,
      "winning_side": "OVER"
    }
  }
}
```

### WebSocket Connection Example

```javascript
const ws = new WebSocket('ws://localhost:8002/v1/realtime');

ws.onopen = () => {
  // Authenticate
  ws.send(JSON.stringify({
    type: 'auth',
    api_key: 'FJAI_DEMO_FANTASY_ADV_001'
  }));
};

ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);
  console.log('Received:', msg);
  
  if (msg.type === 'auth_ok') {
    // Subscribe to fight
    ws.send(JSON.stringify({
      type: 'subscribe',
      channel: 'fight',
      filters: { fight_code: 'PFC50-F1' }
    }));
  }
  
  if (msg.type === 'round_state') {
    // Extract fantasy points
    const fantasyBasic = msg.fantasy_points?.['fantasy.basic'];
    console.log('Fantasy Points (Basic):', fantasyBasic);
    // { red: 84.5, blue: 63.2 }
    
    // Extract market data
    const markets = msg.markets;
    console.log('Markets:', markets);
    // { WINNER: {...}, TOTAL_SIG_STRIKES: {...} }
  }
};
```

---

## 🧪 Testing

### Test 1: Fantasy Breakdown Endpoint

```bash
# Basic profile
curl http://localhost:8002/api/fantasy/PFC50-F1/fantasy.basic | jq '.fantasy_points'

# Advanced profile
curl http://localhost:8002/api/fantasy/PFC50-F1/fantasy.advanced | jq '.fantasy_points'

# Sportsbook profile
curl http://localhost:8002/api/fantasy/PFC50-F1/sportsbook.pro | jq '.fantasy_points'
```

**Expected Output:**
```json
{
  "red": 84.5,
  "blue": 63.2
}
```

### Test 2: Markets Summary Endpoint

```bash
curl http://localhost:8002/api/markets/PFC50-F1 | jq '.markets'
```

**Expected Output:**
```json
{
  "WINNER": {
    "status": "SETTLED",
    "winner_side": "RED",
    "method": "UD"
  },
  "TOTAL_SIG_STRIKES": {
    "status": "SETTLED",
    "line": 50.5,
    "actual": 42,
    "winning_side": "UNDER"
  },
  "KD_OVER_UNDER": {
    "status": "SETTLED",
    "line": 0.5,
    "actual": 1,
    "winning_side": "OVER"
  }
}
```

### Test 3: WebSocket with Injected Data

```javascript
// Connect and subscribe
const ws = new WebSocket('ws://localhost:8002/v1/realtime');

ws.onopen = () => {
  ws.send(JSON.stringify({
    type: 'auth',
    api_key: 'FJAI_DEMO_FANTASY_BASIC_001'
  }));
};

ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);
  
  if (msg.type === 'auth_ok') {
    ws.send(JSON.stringify({
      type: 'subscribe',
      channel: 'fight',
      filters: { fight_code: 'PFC50-F1' }
    }));
  }
  
  // Every message will include fantasy_points and markets!
  if (msg.fantasy_points) {
    console.log('✅ Fantasy data injected:', msg.fantasy_points);
  }
  
  if (msg.markets) {
    console.log('✅ Market data injected:', msg.markets);
  }
};
```

### Test 4: Simulate Round Update

```bash
# Update round state to trigger WebSocket broadcast
curl -X POST http://localhost:8002/v1/fantasy/recompute?fight_id=FIGHT_UUID

# Connected WebSocket clients will receive updated message with:
# - Updated fantasy_points
# - Updated markets (if any auto-settled)
```

---

## 📊 Data Flow

```
Round State Update
       ↓
Auto-Recompute Fantasy Stats (Trigger)
       ↓
Auto-Settle Markets (if fight ended) (Trigger)
       ↓
WebSocket Broadcast
       ↓
Inject Fantasy Points (all 3 profiles)
       ↓
Inject Market Data (with settlements)
       ↓
Send to Subscribers
```

---

## 🎨 Frontend Integration Example

### React Hook for Real-Time Data

```javascript
import { useEffect, useState } from 'react';

function useFightData(fightCode, apiKey) {
  const [fantasyPoints, setFantasyPoints] = useState({});
  const [markets, setMarkets] = useState({});
  const [roundState, setRoundState] = useState(null);

  useEffect(() => {
    const ws = new WebSocket('ws://localhost:8002/v1/realtime');
    
    ws.onopen = () => {
      ws.send(JSON.stringify({ type: 'auth', api_key: apiKey }));
    };
    
    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      
      if (msg.type === 'auth_ok') {
        ws.send(JSON.stringify({
          type: 'subscribe',
          channel: 'fight',
          filters: { fight_code: fightCode }
        }));
      }
      
      if (msg.type === 'round_state') {
        setRoundState(msg.payload);
        
        if (msg.fantasy_points) {
          setFantasyPoints(msg.fantasy_points);
        }
        
        if (msg.markets) {
          setMarkets(msg.markets);
        }
      }
    };
    
    return () => ws.close();
  }, [fightCode, apiKey]);
  
  return { fantasyPoints, markets, roundState };
}

// Usage
function FightDashboard() {
  const { fantasyPoints, markets, roundState } = useFightData(
    'PFC50-F1',
    'FJAI_DEMO_FANTASY_ADV_001'
  );
  
  return (
    <div>
      <h2>Fantasy Points</h2>
      <div>Red: {fantasyPoints['fantasy.basic']?.red}</div>
      <div>Blue: {fantasyPoints['fantasy.basic']?.blue}</div>
      
      <h2>Markets</h2>
      {markets.TOTAL_SIG_STRIKES && (
        <div>
          Total Sig Strikes: {markets.TOTAL_SIG_STRIKES.actual} 
          ({markets.TOTAL_SIG_STRIKES.status})
        </div>
      )}
    </div>
  );
}
```

---

## 🔐 Scope-Based Filtering

Fantasy data is filtered based on API key scope:

- **fantasy.basic**: Only basic stats, no AI metrics
- **fantasy.advanced**: Basic stats + AI predictions
- **sportsbook.pro**: Full data including timeline

Market data is available to all scopes.

---

## ⚡ Performance Notes

1. **Caching:** Fantasy and market data is fetched on each broadcast
2. **Optimization:** Consider caching for high-frequency updates
3. **Lazy Loading:** Data only injected for fight subscriptions
4. **Error Handling:** Injection failures logged but don't break broadcast

---

## 📋 API Endpoint Summary

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/fantasy/{fight_id}/{profile_id}` | GET | Fantasy breakdown |
| `/api/markets/{fight_id}` | GET | Market summary |
| `/v1/realtime` | WebSocket | Real-time with fantasy/market injection |

---

## ✅ Benefits

✅ **Real-Time Updates:** Fantasy points update live as rounds progress
✅ **Market Visibility:** See settlement status in real-time
✅ **Single Connection:** No need for separate API calls
✅ **Bandwidth Efficient:** Compact data format
✅ **Framework Agnostic:** Works with any WebSocket client

The system provides complete real-time visibility into fantasy scoring and market settlements through both REST and WebSocket interfaces!
