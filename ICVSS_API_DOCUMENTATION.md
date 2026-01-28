# ICVSS API Documentation

**Intelligent Combat Vision Scoring System**  
Production-ready CV + Judge hybrid scoring backend

---

## 🎯 Overview

ICVSS is a hybrid scoring system that combines:
- **Computer Vision events** (70% weight) from CV vendors
- **Manual judge events** (30% weight) from human operators
- **Damage primacy** rule (knockdowns override volume)
- **10-Point Must System** (10-9, 10-8, 10-7, 10-10)

---

## 📡 Base URL

```
https://fight-scoring-pro.preview.emergentagent.com/api/icvss
```

---

## 🔑 Authentication

- **CV Vendor Endpoints**: Require `X-API-Key` header
- **WebSocket Feeds**: Optional `auth_token` parameter
- **Broadcast Feed**: Public (no auth required)

---

## 📋 API Endpoints

### **1. Round Lifecycle**

#### **POST /round/open**
Open a new ICVSS round

**Request**:
```json
{
  "bout_id": "bout-uuid-123",
  "round_num": 1
}
```

**Response**:
```json
{
  "round_id": "round-uuid-456",
  "bout_id": "bout-uuid-123",
  "round_num": 1,
  "status": "open",
  "cv_events": [],
  "judge_events": [],
  "opened_at": "2025-11-20T17:55:00Z"
}
```

---

#### **POST /round/event**
Add a CV or judge event to a round

**Request**:
```json
{
  "round_id": "round-uuid-456",
  "event": {
    "bout_id": "bout-uuid-123",
    "round_id": "round-uuid-456",
    "fighter_id": "fighter1",
    "event_type": "strike_jab",
    "severity": 0.8,
    "confidence": 0.95,
    "position": "distance",
    "timestamp_ms": 12500,
    "source": "cv_system",
    "vendor_id": "vendor_a"
  }
}
```

**Event Types**:
- **Strikes**: `strike_jab`, `strike_cross`, `strike_hook`, `strike_uppercut`, `strike_elbow`, `strike_knee`
- **Kicks**: `kick_head`, `kick_body`, `kick_low`, `kick_front`
- **Damage**: `rock`, `KD_flash`, `KD_hard`, `KD_nearfinish`
- **Grappling**: `td_landed`, `sub_attempt_light`, `sub_attempt_deep`, `sub_attempt_nearfinish`, `sweep`
- **Control**: `control_start`, `control_end`, `control_top`, `control_back`, `control_cage`

**Response**:
```json
{
  "success": true,
  "message": "Event accepted"
}
```

---

#### **POST /round/event/batch**
Add multiple events at once

**Request**:
```json
{
  "round_id": "round-uuid-456",
  "events": [
    { "fighter_id": "fighter1", "event_type": "strike_jab", ... },
    { "fighter_id": "fighter2", "event_type": "kick_body", ... }
  ]
}
```

**Response**:
```json
{
  "success": true,
  "accepted": 45,
  "rejected": 5,
  "total": 50
}
```

---

#### **GET /round/score/{round_id}**
Calculate current score for a round

**Response**:
```json
{
  "bout_id": "bout-uuid-123",
  "round_id": "round-uuid-456",
  "round_num": 1,
  "fighter1_score": 10,
  "fighter2_score": 9,
  "score_card": "10-9",
  "winner": "fighter1",
  "fighter1_breakdown": {
    "cv_score": 45.2,
    "judge_score": 12.0,
    "striking": 38.5,
    "grappling": 15.2,
    "control": 3.5
  },
  "fighter2_breakdown": {
    "cv_score": 32.1,
    "judge_score": 8.5,
    "striking": 28.0,
    "grappling": 10.6,
    "control": 2.0
  },
  "confidence": 0.85,
  "cv_event_count": 127,
  "judge_event_count": 18,
  "total_events": 145,
  "cv_contribution": 0.7,
  "judge_contribution": 0.3,
  "calculated_at": "2025-11-20T18:00:00Z"
}
```

---

#### **POST /round/lock/{round_id}**
Lock a round (finalize score)

**Response**:
```json
{
  "success": true,
  "round_id": "round-uuid-456",
  "event_hash": "a3f5b8c9d2e1...",
  "locked_at": "2025-11-20T18:05:00Z"
}
```

---

#### **GET /round/{round_id}**
Get round data

**Response**: Full `ICVSSRound` object with all events

---

### **2. CV Vendor Endpoints**

#### **POST /cv/event**
Receive event from CV vendor (vendor-specific format)

**Headers**:
```
X-API-Key: your-vendor-api-key
```

**Request**:
```json
{
  "vendor_id": "vendor_a",
  "raw_data": {
    "bout_id": "bout-uuid-123",
    "round_id": "round-uuid-456",
    "fighter_id": "fighter1",
    "type": "punch_jab",
    "impact": 0.8,
    "certainty": 0.95,
    "timestamp_ms": 12500
  }
}
```

**Response**:
```json
{
  "success": true,
  "message": "Event accepted"
}
```

---

### **3. WebSocket Feeds**

#### **WS /ws/cv-feed/{bout_id}**
Real-time CV events

**Connect**:
```javascript
const ws = new WebSocket('wss://judge-sync-app.preview.emergentagent.com/api/icvss/ws/cv-feed/bout-123');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('CV Event:', data);
};
```

**Message Format**:
```json
{
  "type": "cv_event",
  "bout_id": "bout-123",
  "round_id": "round-456",
  "data": {
    "event_id": "event-789",
    "fighter_id": "fighter1",
    "event_type": "strike_jab",
    "severity": 0.8,
    "confidence": 0.95
  },
  "timestamp": "2025-11-20T18:10:00Z"
}
```

---

#### **WS /ws/judge-feed/{bout_id}**
Real-time judge manual events

---

#### **WS /ws/score-feed/{bout_id}**
Real-time score updates

**Message Format**:
```json
{
  "type": "score_update",
  "bout_id": "bout-123",
  "round_id": "round-456",
  "data": {
    "score_card": "10-9",
    "winner": "fighter1",
    "fighter1_score": 10,
    "fighter2_score": 9
  },
  "timestamp": "2025-11-20T18:15:00Z"
}
```

---

#### **WS /ws/broadcast/{bout_id}**
Public broadcast feed for arena overlays (no auth)

**Message Format**:
```json
{
  "type": "broadcast",
  "bout_id": "bout-123",
  "data": {
    "action": "round_opened",
    "round_num": 2
  },
  "timestamp": "2025-11-20T18:20:00Z"
}
```

---

### **4. Utility Endpoints**

#### **GET /stats**
Get ICVSS system statistics

**Response**:
```json
{
  "event_processor": {
    "total_processed": 1523,
    "dedup_window_ms": 100,
    "confidence_threshold": 0.6
  },
  "websocket_connections": {
    "total_cv_feed": 3,
    "total_judge_feed": 2,
    "total_score_feed": 5,
    "total_broadcast_feed": 1
  },
  "active_rounds": 2,
  "timestamp": "2025-11-20T18:25:00Z"
}
```

---

#### **GET /health**
Health check

**Response**:
```json
{
  "status": "healthy",
  "service": "ICVSS",
  "version": "1.0.0",
  "timestamp": "2025-11-20T18:30:00Z"
}
```

---

## 🧪 Testing

### **Run Unit Tests**:
```bash
cd /app/backend
python tests/test_icvss.py
```

**Tests Cover**:
- ✅ Event deduplication (80-150ms window)
- ✅ Confidence filtering (threshold 0.6)
- ✅ 10-8 logic with knockdowns
- ✅ KD vs high volume (damage primacy)
- ✅ Conflicting CV + judge inputs
- ✅ 10-10 draw scenarios

---

## 📊 Scoring Algorithm

### **Category Weights** (FightJudge AI):
- **Striking**: 50%
- **Grappling**: 40%
- **Control**: 10%

### **Hybrid Fusion**:
- **CV Weight**: 70%
- **Judge Weight**: 30%

### **Damage Primacy**:
If damage differential > 30 points, damage winner gets round regardless of other stats

### **10-Point Must System**:
- **10-10**: Score diff ≤ 3.0 (extremely rare)
- **10-9**: Score diff < 100.0 (standard win)
- **10-8**: Score diff < 200.0 (dominant win with near-finish)
- **10-7**: Score diff ≥ 200.0 (complete domination)

---

## 🔒 Security

### **Event Integrity**:
- All events hashed with SHA256
- Audit trail in `icvss_audit_logs` collection
- Tamper detection via `verify_integrity(round_id)`

### **API Authentication**:
```python
# CV Vendor
headers = {"X-API-Key": "your-vendor-key"}

# WebSocket
ws_url = f"wss://.../ws/cv-feed/{bout_id}?auth_token=your-token"
```

---

## 📦 Database Schema

### **MongoDB Collections**:

#### `icvss_rounds`:
```json
{
  "round_id": "uuid",
  "bout_id": "uuid",
  "round_num": 1,
  "status": "open|active|locked",
  "cv_events": [...],
  "judge_events": [...],
  "fighter1_score": 10,
  "fighter2_score": 9,
  "score_card": "10-9",
  "event_hash": "sha256..."
}
```

#### `icvss_audit_logs`:
```json
{
  "log_id": "uuid",
  "bout_id": "uuid",
  "round_id": "uuid",
  "action": "event_added|round_locked",
  "actor": "cv_system|judge|operator",
  "data": {...},
  "data_hash": "sha256...",
  "timestamp": "2025-11-20T18:00:00Z"
}
```

---

## 🚀 Integration Example

```python
import requests
import json

BASE_URL = "https://fight-scoring-pro.preview.emergentagent.com/api/icvss"

# 1. Open round
response = requests.post(f"{BASE_URL}/round/open", json={
    "bout_id": "bout-123",
    "round_num": 1
})
round_data = response.json()
round_id = round_data["round_id"]

# 2. Send CV events
cv_event = {
    "bout_id": "bout-123",
    "round_id": round_id,
    "fighter_id": "fighter1",
    "event_type": "strike_jab",
    "severity": 0.8,
    "confidence": 0.95,
    "timestamp_ms": 1000,
    "source": "cv_system",
    "vendor_id": "my_cv_system"
}

requests.post(f"{BASE_URL}/round/event", json={
    "round_id": round_id,
    "event": cv_event
})

# 3. Get score
score = requests.get(f"{BASE_URL}/round/score/{round_id}").json()
print(f"Score: {score['score_card']} - Winner: {score['winner']}")

# 4. Lock round
requests.post(f"{BASE_URL}/round/lock/{round_id}")
```

---

## 📞 Support

- **GitHub**: [Report issues](https://github.com/your-repo/issues)
- **Docs**: `/app/ICVSS_API_DOCUMENTATION.md`
- **Tests**: `/app/backend/tests/test_icvss.py`

---

**Built with ❤️ for professional combat sports scoring**
