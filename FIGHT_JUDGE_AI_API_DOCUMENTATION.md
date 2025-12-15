# Fight Judge AI - API Documentation
## Integration Guide for Lovable.dev & External Platforms

**Base URL:** `https://fightdata.preview.emergentagent.com/api`  
**Production URL:** (Will be provided after deployment)  
**Protocol:** REST API + WebSocket for real-time updates  
**Authentication:** None (Open API - Add your own auth layer if needed)  
**CORS:** Enabled for all origins (`*`)

---

## 📋 Table of Contents

1. [Quick Start](#quick-start)
2. [Core Endpoints](#core-endpoints)
3. [Live Scoring](#live-scoring)
4. [Judge Management](#judge-management)
5. [Event Logging](#event-logging)
6. [Fighter Analytics](#fighter-analytics)
7. [WebSocket Connections](#websocket-connections)
8. [Data Models](#data-models)
9. [Error Handling](#error-handling)
10. [Rate Limits](#rate-limits)

---

## 🚀 Quick Start

### Basic Health Check
```bash
curl https://fightdata.preview.emergentagent.com/api/
```

**Response:**
```json
{
  "message": "Fight Judge AI API",
  "version": "1.0.0",
  "status": "operational"
}
```

### Calculate Round Score (Main Endpoint)
```bash
curl -X POST https://fightdata.preview.emergentagent.com/api/calculate-score \
  -H "Content-Type: application/json" \
  -d '{
    "bout_id": "bout-123",
    "round_num": 1,
    "round_duration": 300,
    "events": [
      {
        "bout_id": "bout-123",
        "round_num": 1,
        "fighter": "fighter1",
        "event_type": "Cross",
        "timestamp": 45.5,
        "metadata": {"significant": true}
      },
      {
        "bout_id": "bout-123",
        "round_num": 1,
        "fighter": "fighter1",
        "event_type": "KD",
        "timestamp": 120.0,
        "metadata": {"tier": "Hard"}
      }
    ]
  }'
```

---

## 🎯 Core Endpoints

### 1. Calculate Round Score
**Endpoint:** `POST /api/calculate-score`  
**Purpose:** Calculate scoring for a complete round based on events

**Request Body:**
```json
{
  "bout_id": "string",
  "round_num": 1,
  "round_duration": 300,
  "events": [
    {
      "bout_id": "string",
      "round_num": 1,
      "fighter": "fighter1 | fighter2",
      "event_type": "Cross | Hook | KD | Takedown Landed | etc.",
      "timestamp": 45.5,
      "metadata": {
        "significant": true,
        "tier": "Flash | Hard | Near-Finish",
        "duration": 30
      }
    }
  ]
}
```

**Response:**
```json
{
  "bout_id": "bout-123",
  "round_num": 1,
  "fighter1_score": {
    "fighter": "fighter1",
    "final_score": 125.5,
    "subscores": {
      "KD": 0.70,
      "ISS": 45.2,
      "GCQ": 12.5,
      "TDQ": 5.0,
      "SUBQ": 0.0,
      "OC": 2.5,
      "AGG": 8.3,
      "RP": 0.0,
      "TSR": 0.95
    },
    "event_counts": {
      "knockdowns": 1,
      "sig_strikes": 32,
      "takedowns": 2
    }
  },
  "fighter2_score": {
    "fighter": "fighter2",
    "final_score": 89.3,
    "subscores": {...}
  },
  "score_gap": 36.2,
  "card": "10-9",
  "winner": "fighter1",
  "reasons": {
    "delta": 36.2,
    "gates_winner": {
      "finish_threat": true,
      "control_dom": false,
      "multi_cat_dom": true
    },
    "gates_loser": {...},
    "to_108": false,
    "to_107": false,
    "draw": false,
    "tie_breaker": null
  },
  "uncertainty": "medium_confidence",
  "uncertainty_factors": []
}
```

---

### 2. Calculate Score V2 (Enhanced)
**Endpoint:** `POST /api/calculate-score-v2`  
**Purpose:** Advanced scoring with percentage-based model

**Request:** Same as `/calculate-score`

**Response:** Enhanced with category breakdowns
```json
{
  "bout_id": "bout-123",
  "round_num": 1,
  "winner": "fighter1",
  "card": "10-9",
  "fighter1": {
    "raw_scores": {
      "striking": 35.5,
      "grappling": 12.0,
      "other": 2.5
    },
    "weighted_total": 28.25,
    "event_breakdown": {...}
  },
  "fighter2": {...},
  "score_differential": 15.5,
  "scoring_config": {
    "striking_weight": 50.0,
    "grappling_weight": 40.0,
    "other_weight": 10.0
  }
}
```

---

## 📊 Live Scoring

### 3. Get Live Scoring
**Endpoint:** `GET /api/live/{bout_id}`  
**Purpose:** Get real-time scoring for an active bout

**Request:**
```bash
curl https://fightdata.preview.emergentagent.com/api/live/bout-123
```

**Response:**
```json
{
  "bout_id": "bout-123",
  "current_round": 2,
  "rounds": [
    {
      "round_num": 1,
      "card": "10-9",
      "winner": "fighter1",
      "fighter1_total": 125.5,
      "fighter2_total": 89.3
    },
    {
      "round_num": 2,
      "card": "IN_PROGRESS",
      "live_scores": {
        "fighter1": 45.2,
        "fighter2": 38.7
      }
    }
  ],
  "cumulative": {
    "fighter1_rounds_won": 1,
    "fighter2_rounds_won": 0,
    "overall_leader": "fighter1"
  }
}
```

---

### 4. Get Final Bout Results
**Endpoint:** `GET /api/final/{bout_id}`  
**Purpose:** Get complete bout results after all rounds

**Response:**
```json
{
  "bout_id": "bout-123",
  "total_rounds": 3,
  "winner": "fighter1",
  "method": "UD",
  "rounds": [...],
  "official_cards": [
    {"round": 1, "card": "10-9"},
    {"round": 2, "card": "10-9"},
    {"round": 3, "card": "10-8"}
  ],
  "cumulative_score": {
    "fighter1": "30-27",
    "fighter2": "27-30"
  }
}
```

---

## 👨‍⚖️ Judge Management

### 5. Lock Judge Score
**Endpoint:** `POST /api/judge-scores/lock`  
**Purpose:** Lock a judge's score for a round (prevents changes)

**Request:**
```json
{
  "bout_id": "bout-123",
  "round_num": 1,
  "judge_id": "judge-001",
  "judge_name": "John Smith",
  "fighter1_score": 10,
  "fighter2_score": 9,
  "card": "10-9"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Score locked successfully",
  "locked_at": "2024-12-06T23:45:00Z"
}
```

---

### 6. Unlock Judge Score (Supervisor Only)
**Endpoint:** `POST /api/judge-scores/unlock`  
**Purpose:** Unlock a judge's score (requires supervisor code)

**Request:**
```json
{
  "bout_id": "bout-123",
  "round_num": 1,
  "judge_id": "judge-001",
  "supervisor_code": "199215"
}
```

---

### 7. Get Judge Scores for Round
**Endpoint:** `GET /api/judge-scores/{bout_id}/{round_num}`  
**Purpose:** Get all judge scores for a specific round

**Response:**
```json
{
  "bout_id": "bout-123",
  "round_num": 1,
  "scores": [
    {
      "judge_id": "judge-001",
      "judge_name": "John Smith",
      "fighter1_score": 10,
      "fighter2_score": 9,
      "card": "10-9",
      "locked": true,
      "locked_at": "2024-12-06T23:45:00Z"
    },
    {
      "judge_id": "judge-002",
      "judge_name": "Jane Doe",
      "locked": false
    }
  ],
  "all_judges_locked": false
}
```

---

## 🎮 Event Logging

### 8. Log Event (V2 - Enhanced)
**Endpoint:** `POST /api/events/v2/log`  
**Purpose:** Log a single combat event with deduplication

**Request:**
```json
{
  "bout_id": "bout-123",
  "round_id": 1,
  "judge_id": "judge-001",
  "fighter_id": "fighter1",
  "event_type": "Cross",
  "timestamp_ms": 45500,
  "device_id": "tablet-001",
  "metadata": {
    "significant": true,
    "source": "manual"
  }
}
```

**Response:**
```json
{
  "success": true,
  "event_id": "evt-12345",
  "deduplicated": false,
  "canonical_event_id": null
}
```

---

### 9. Verify Event Chain
**Endpoint:** `GET /api/events/v2/verify/{bout_id}/{round_id}`  
**Purpose:** Verify integrity of event chain (blockchain-style)

**Response:**
```json
{
  "bout_id": "bout-123",
  "round_id": 1,
  "total_events": 127,
  "chain_valid": true,
  "broken_links": [],
  "duplicate_events": 3,
  "canonical_events": 124
}
```

---

### 10. Get Events for Round
**Endpoint:** `GET /api/events/v2/{bout_id}/{round_id}`  
**Purpose:** Get all events for a specific round

**Response:**
```json
{
  "bout_id": "bout-123",
  "round_id": 1,
  "events": [
    {
      "event_id": "evt-001",
      "fighter_id": "fighter1",
      "event_type": "Cross",
      "timestamp_ms": 45500,
      "metadata": {"significant": true},
      "is_canonical": true,
      "hash": "abc123..."
    }
  ],
  "total_events": 127
}
```

---

## 🥊 Fighter Analytics

### 11. Get Fighter Stats
**Endpoint:** `GET /api/fighters/{fighter_name}/stats`  
**Purpose:** Get historical statistics for a fighter

**Request:**
```bash
curl https://fightdata.preview.emergentagent.com/api/fighters/John%20Doe/stats
```

**Response:**
```json
{
  "fighter_name": "John Doe",
  "total_rounds": 45,
  "total_fights": 15,
  "avg_kd_per_round": 0.3,
  "avg_ss_per_round": 28.5,
  "avg_td_per_round": 1.2,
  "avg_sub_attempts": 0.8,
  "avg_control_time": 45.2,
  "avg_round_score": 112.5,
  "rounds_won": 32,
  "rounds_lost": 11,
  "rounds_drawn": 2,
  "rate_10_8": 0.15,
  "rate_10_7": 0.02,
  "tendencies": {
    "striking_style": {
      "head": 0.6,
      "body": 0.3,
      "leg": 0.1
    },
    "grappling_rate": 0.35,
    "finish_threat_rate": 0.22,
    "control_preference": 0.45,
    "aggression_level": 7.5
  },
  "last_updated": "2024-12-06T23:00:00Z"
}
```

---

### 12. Compare Fighters
**Endpoint:** `GET /api/fighters/compare?fighter1={name1}&fighter2={name2}`  
**Purpose:** Side-by-side comparison of two fighters

**Request:**
```bash
curl "https://fightdata.preview.emergentagent.com/api/fighters/compare?fighter1=John%20Doe&fighter2=Jane%20Smith"
```

**Response:**
```json
{
  "fighter1": {
    "name": "John Doe",
    "stats": {...}
  },
  "fighter2": {
    "name": "Jane Smith",
    "stats": {...}
  },
  "comparison": {
    "striking_advantage": "fighter1",
    "grappling_advantage": "fighter2",
    "control_advantage": "fighter2",
    "finish_threat_advantage": "fighter1",
    "predicted_winner": "fighter1",
    "confidence": 0.65
  }
}
```

---

### 13. Update Fighter Stats
**Endpoint:** `POST /api/fighters/update-stats`  
**Purpose:** Update fighter statistics after a round/fight

**Request:**
```json
{
  "fighter_name": "John Doe",
  "round_events": [
    {"event_type": "Cross", "significant": true},
    {"event_type": "KD", "tier": "Hard"}
  ],
  "round_score": 125.5,
  "round_result": "won"
}
```

---

## 🔄 WebSocket Connections

### Real-Time Live Scoring WebSocket
**Endpoint:** `wss://fightdata.preview.emergentagent.com/ws/live/{bout_id}`  
**Purpose:** Receive real-time scoring updates as events are logged

**Connection:**
```javascript
const ws = new WebSocket('wss://fightdata.preview.emergentagent.com/ws/live/bout-123');

ws.onopen = () => {
  console.log('Connected to live scoring');
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Score update:', data);
  // {
  //   "type": "score_update",
  //   "bout_id": "bout-123",
  //   "round_num": 1,
  //   "fighter1_score": 125.5,
  //   "fighter2_score": 89.3,
  //   "card": "10-9",
  //   "winner": "fighter1",
  //   "timestamp": "2024-12-06T23:45:30Z"
  // }
};

ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};

ws.onclose = () => {
  console.log('Disconnected from live scoring');
};
```

**Message Types:**
- `score_update` - Real-time score changes
- `event_logged` - New event logged
- `round_ended` - Round has ended
- `judge_locked` - Judge locked their score
- `bout_finished` - Bout complete

---

## 📦 Data Models

### Event Types
```javascript
// Striking Events
"Jab" | "Cross" | "Hook" | "Uppercut" | "Elbow" | "Knee" | "Kick"

// Damage Events
"KD" | "Rocked/Stunned"

// Grappling Events
"Takedown Landed" | "Takedown Stuffed" | "Submission Attempt" | "Sweep/Reversal" | "Guard Passing"

// Control Events
"Ground Top Control" | "Ground Back Control" | "Cage Control Time"
```

### Event Metadata
```javascript
{
  "significant": boolean,           // For strikes (SS vs non-SS)
  "tier": "Flash | Hard | Near-Finish",  // For KDs and Subs
  "duration": number,                // For control time (seconds)
  "source": "manual | quick-input | cv-system"
}
```

### Scoring Config (Percentage-Based Model)
```javascript
{
  "categories": {
    "striking": 50.0,    // 50% weight
    "grappling": 40.0,   // 40% weight
    "other": 10.0        // 10% weight
  },
  "base_values": {
    "Cross": {"sig": 0.14, "non_sig": 0.07},
    "Hook": {"sig": 0.14, "non_sig": 0.07},
    "Uppercut": {"sig": 0.14, "non_sig": 0.07},
    "Elbow": {"sig": 0.14, "non_sig": 0.07},
    "Jab": {"sig": 0.10, "non_sig": 0.05},
    "Knee": {"sig": 0.10, "non_sig": 0.05},
    "Kick": {"sig": 0.14, "non_sig": 0.07},
    "KD": {"Flash": 0.40, "Hard": 0.70, "Near-Finish": 1.00},
    "Rocked/Stunned": 0.30,
    "Submission Attempt": {"Light": 0.25, "Deep": 0.60, "Near-Finish": 1.00},
    "Takedown Landed": 0.25,
    "Sweep/Reversal": 0.05,
    "Ground Back Control": 0.012,  // per second
    "Ground Top Control": 0.010,   // per second
    "Cage Control Time": 0.006,    // per second
    "Takedown Stuffed": 0.04
  }
}
```

---

## ⚠️ Error Handling

All endpoints return standard HTTP status codes:

**Success:**
- `200 OK` - Request successful
- `201 Created` - Resource created
- `204 No Content` - Success, no data returned

**Client Errors:**
- `400 Bad Request` - Invalid request data
- `401 Unauthorized` - Authentication required
- `403 Forbidden` - Insufficient permissions
- `404 Not Found` - Resource not found
- `409 Conflict` - Resource already exists

**Server Errors:**
- `500 Internal Server Error` - Server error
- `503 Service Unavailable` - Service temporarily down

**Error Response Format:**
```json
{
  "error": "Invalid event type",
  "detail": "Event type 'InvalidStrike' is not recognized",
  "timestamp": "2024-12-06T23:45:00Z"
}
```

---

## 🚦 Rate Limits

**Current Limits:**
- No rate limiting implemented
- Recommended: 1000 requests/minute per IP

**Future Implementation:**
- API keys for authentication
- Tiered rate limits based on plan

---

## 🔧 Additional Endpoints

### Review & Audit
- `POST /api/review/create-flag` - Flag discrepancies
- `GET /api/review/flags` - Get review flags
- `PUT /api/review/resolve/{flag_id}` - Resolve flag
- `GET /api/review/stats` - Review statistics
- `POST /api/audit/log` - Log audit event
- `GET /api/audit/logs` - Get audit logs

### Training & Shadow Judging
- `GET /api/training-library/rounds` - Get training rounds
- `POST /api/training-library/submit-score` - Submit shadow score
- `GET /api/training-library/judge-stats/{judgeId}` - Judge performance
- `GET /api/training-library/leaderboard` - Training leaderboard

### Device Telemetry
- `POST /api/telemetry/report` - Report device health
- `GET /api/telemetry/{bout_id}` - Get bout telemetry

### Supervisor Dashboard
- `GET /api/supervisor/dashboard/{bout_id}` - Supervisor overview
- `POST /api/rounds/force-close` - Force close round

---

## 📝 Integration Examples

### React/Next.js Integration
```javascript
// lib/fightJudgeApi.js
const API_BASE = 'https://fightdata.preview.emergentagent.com/api';

export const calculateRoundScore = async (boutId, roundNum, events) => {
  const response = await fetch(`${API_BASE}/calculate-score`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      bout_id: boutId,
      round_num: roundNum,
      round_duration: 300,
      events
    })
  });
  
  if (!response.ok) throw new Error('Failed to calculate score');
  return response.json();
};

export const subscribeToLiveScoring = (boutId, callback) => {
  const ws = new WebSocket(`wss://fightdata.preview.emergentagent.com/ws/live/${boutId}`);
  
  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    callback(data);
  };
  
  return ws;
};
```

### Python Integration
```python
import requests

API_BASE = 'https://fightdata.preview.emergentagent.com/api'

def calculate_round_score(bout_id, round_num, events):
    response = requests.post(
        f'{API_BASE}/calculate-score',
        json={
            'bout_id': bout_id,
            'round_num': round_num,
            'round_duration': 300,
            'events': events
        }
    )
    response.raise_for_status()
    return response.json()

def get_fighter_stats(fighter_name):
    response = requests.get(f'{API_BASE}/fighters/{fighter_name}/stats')
    response.raise_for_status()
    return response.json()
```

---

## 🎯 Quick Integration Checklist

For integrating with Lovable.dev or any external platform:

1. ✅ **Base URL:** `https://fightdata.preview.emergentagent.com/api`
2. ✅ **Authentication:** None required (add if needed)
3. ✅ **CORS:** Enabled for all origins
4. ✅ **Main Endpoint:** `POST /api/calculate-score`
5. ✅ **Live Updates:** WebSocket at `wss://.../ws/live/{bout_id}`
6. ✅ **Event Types:** See "Data Models" section
7. ✅ **Response Format:** JSON
8. ✅ **Error Handling:** Standard HTTP codes

---

## 📞 Support & Contact

**Issues:** Report via your Emergent dashboard  
**Documentation:** This file + `/app/SCORING_GUIDE.md`  
**Scoring Reference:** `/app/PERCENTAGE_BASED_SCORING_COMPLETE.md`

---

*Last Updated: December 2024*  
*API Version: 1.0.0*  
*Platform: Emergent.sh*
