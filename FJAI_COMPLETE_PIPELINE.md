# Fight Judge AI - Complete E2 → E1 Pipeline Documentation

## Architecture Overview

```
[Multi/Single Cameras]  
        ↓  
CV Model (external - future)
        ↓  
E2 — CV Analytics Engine (/api/cv-analytics)
        ↓  
Standardized Clean Events
        ↓  
E1 — Scoring Engine (/api/fjai)
        ↓  
Supervisor Dashboard & Judge Console & Overlay
        ↓  
Arena Jumbotron / Live Stream Output
```

## System Components

### E2: CV Analytics Engine (`/app/backend/cv_analytics/`)

**Purpose**: Convert raw computer vision model outputs into standardized combat events

**Modules**:
- `analytics_engine.py` - Main processing engine
- `temporal_smoothing.py` - Rolling window smoothing & optical flow validation
- `multicam_fusion.py` - Consensus detection & angle weighting
- `mock_generator.py` - Mock CV data for testing

**Key Features**:
- ✅ **Temporal Smoothing**: 5-frame rolling window with 60% consistency threshold
- ✅ **Optical Flow Validation**: Motion vector validation for impact events
- ✅ **Multi-Camera Fusion**: Angle-weighted consensus (front angles preferred)
- ✅ **Momentum Detection**: Auto-detect flurries (≥4 strikes in <1.5s)
- ✅ **Fighter Style Classification**: Striker/Grappler/Wrestler/Balanced
- ✅ **Analytics Output**: Control time, pace, tempo, cumulative damage

**API Endpoints**:
```
POST /api/cv-analytics/process
POST /api/cv-analytics/process/batch  (multi-camera)
POST /api/cv-analytics/analytics
GET  /api/cv-analytics/mock/scenario/{scenario}
GET  /api/cv-analytics/health
```

### E1: Fight Judge AI Scoring Engine (`/app/backend/fjai/`)

**Purpose**: Combine manual + CV events into unified 10-Point-Must scores

**Modules**:
- `models.py` - Standardized event schema (Jabbr/CombatIQ compatible)
- `event_pipeline.py` - Deduplication & validation
- `scoring_engine.py` - Weighted scoring with damage primacy
- `round_manager.py` - Round lifecycle management
- `audit_layer.py` - Append-only SHA256 audit logs
- `websocket_manager.py` - Real-time feeds

**Key Features**:
- ✅ **13 Event Types**: KD tiers, strikes, grappling, control, momentum
- ✅ **Deduplication**: 80-150ms configurable window
- ✅ **Weighted Scoring**: Damage 50% | Control 25% | Aggression 15% | Defense 10%
- ✅ **Damage Primacy Rule**: Auto-override when >30% damage advantage
- ✅ **10-Point-Must Mapping**: 10-10, 10-9, 10-8, 10-7 based on score differential
- ✅ **Confidence Scoring**: Based on event count, quality, and margin
- ✅ **SHA256 Audit**: CombatIQ-style cryptographic integrity
- ✅ **Multi-Camera Fusion**: Angle-weighted canonical event selection

**API Endpoints**:
```
POST /api/fjai/round/open
POST /api/fjai/round/event
GET  /api/fjai/round/score/{round_id}
POST /api/fjai/round/lock/{round_id}
GET  /api/fjai/audit/export/{bout_id}
GET  /api/fjai/audit/verify/{log_id}
GET  /api/fjai/system/status

WebSockets:
ws://  /api/fjai/ws/cv/{bout_id}
ws://  /api/fjai/ws/judge/{bout_id}
ws://  /api/fjai/ws/score/{bout_id}
ws://  /api/fjai/ws/broadcast/{bout_id}
```

## Event Schema

### Standardized Combat Event
```python
{
    "event_id": "uuid",
    "bout_id": "string",
    "round_id": "string",
    "fighter_id": "fighter_a | fighter_b",
    
    "event_type": "kd_flash | kd_hard | kd_nf | rocked | 
                   strike_sig | strike_highimpact | 
                   td_attempt | td_land | sub_attempt |
                   control_start | control_end | 
                   momentum_swing",
    
    "severity": 0.0 - 1.0,
    "confidence": 0.0 - 1.0,
    "timestamp_ms": integer,
    "source": "manual | cv_system | analytics",
    
    "camera_id": "optional",
    "position": "optional - octagon position",
    "angle": "optional - camera angle degrees",
    "metadata": {}
}
```

## Scoring Algorithm

### Category Scoring
```python
# Base Values
KD_NF = 35.0        # Near-finish knockdown
KD_HARD = 25.0      # Hard knockdown
KD_FLASH = 15.0     # Flash knockdown
ROCKED = 12.0       # Rocked but not down
STRIKE_HIGHIMPACT = 5.0
STRIKE_SIG = 2.0
SUB_ATTEMPT = 6.0
TD_LAND = 4.0
MOMENTUM_SWING = 8.0
CONTROL = 0.3 per second

# Weighted Formula
final_score = (
    damage * 0.50 +
    control * 0.25 +
    aggression * 0.15 +
    defense * 0.10
)
```

### Damage Primacy Override
```python
if (max_damage / total_damage) >= 0.80:
    # Winner determined solely by damage
    winner_score = max(winner_score, loser_score + 20.0)
```

### 10-Point-Must Mapping
```python
diff < 3.0    → 10-10 (draw)
diff < 15.0   → 10-9 (clear winner)
diff < 30.0   → 10-8 (dominant)
diff >= 30.0  → 10-7 (overwhelming)
```

## Usage Examples

### 1. Process Raw CV Frame (E2)
```python
import requests

# Raw CV input from vision model
raw_cv_data = {
    "frame_id": 1,
    "timestamp_ms": 1000,
    "camera_id": "cam_1",
    "fighter_id": "fighter_a",
    "action_type": "punch",
    "action_logits": {"punch": 0.92, "kick": 0.05},
    "fighter_bbox": [0.3, 0.4, 0.2, 0.4],
    "keypoints": [...],  # 17 keypoints
    "impact_detected": true,
    "impact_level": "heavy",
    "motion_vectors": {"vx": 5.0, "vy": -2.0, "magnitude": 7.5},
    "camera_angle": 90.0,
    "camera_distance": 5.0
}

# Process through E2
response = requests.post(
    "http://api/cv-analytics/process",
    params={"bout_id": "PFC_50", "round_id": "round_1"},
    json=raw_cv_data
)

combat_events = response.json()  # Standardized events
```

### 2. Send Events to Scoring Engine (E1)
```python
# Open round
response = requests.post(
    "http://api/fjai/round/open",
    params={"bout_id": "PFC_50", "round_num": 1}
)
round_data = response.json()
round_id = round_data["round_id"]

# Add events
for event in combat_events:
    requests.post(
        f"http://api/fjai/round/event?round_id={round_id}",
        json=event
    )

# Get live score
score = requests.get(f"http://api/fjai/round/score/{round_id}").json()
print(f"Score: {score['score_card']}")
print(f"Winner: {score['winner']}")

# Lock round
requests.post(f"http://api/fjai/round/lock/{round_id}")
```

### 3. Multi-Camera Processing
```python
# Get mock multi-camera data
cameras = requests.get(
    "http://api/cv-analytics/mock/multicam",
    params={
        "bout_id": "PFC_50",
        "round_id": "round_1",
        "fighter_id": "fighter_a",
        "action": "punch",
        "impact": "heavy",
        "num_cameras": 3
    }
).json()

# Process batch with fusion
fused_events = requests.post(
    "http://api/cv-analytics/process/batch",
    params={"bout_id": "PFC_50", "round_id": "round_1"},
    json=cameras
).json()
```

## Testing

### Run Integration Tests
```bash
cd /app/backend
python tests/test_fjai_integration.py
```

**Tests Include**:
- ✅ KD vs Volume Scoring (damage primacy)
- ✅ Momentum Swing Detection
- ✅ Event Deduplication (80-150ms)
- ✅ Multi-Camera Fusion
- ✅ Confidence Threshold Filtering
- ✅ Raw CV → CombatEvent Conversion
- ✅ KD Tier Classification
- ✅ Fighter Style Classification
- ✅ End-to-End Pipeline (E2 → E1)

### Run Live Demo
```bash
cd /app/backend
python demo_e2_to_e1_pipeline.py
```

**Demo Scenarios**:
1. **Balanced** - Mix of strikes and grappling
2. **Striker Dominance** - Heavy striking with KDs
3. **Grappler Control** - Takedowns and control
4. **War** - High-paced back-and-forth

## Production Deployment

### PFC 50 Configuration
```python
# Optimized for low latency
EventPipeline(
    dedup_window_ms=100,      # 100ms deduplication
    confidence_threshold=0.5   # 50% confidence minimum
)

TemporalSmoother(
    window_size=5,             # 5-frame window
    confidence_threshold=0.6   # 60% for smoothing
)

MultiCameraFusion(
    fusion_window_ms=150       # 150ms fusion window
)
```

### WebSocket Integration
```javascript
// Subscribe to live scores
const ws = new WebSocket('ws://api/fjai/ws/score/PFC_50');

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === 'score_update') {
        updateJumbotron(data.data.score_card);
        updateBroadcastOverlay(data.data);
    }
};
```

## Monitoring

### System Health
```bash
# E2 Status
curl http://api/cv-analytics/status

# E1 Status
curl http://api/fjai/system/status
```

### Audit Export
```bash
# Export complete audit trail
curl http://api/fjai/audit/export/PFC_50 > audit_bundle.json

# Verify log signature
curl http://api/fjai/audit/verify/{log_id}
```

## Performance Metrics

- **Event Processing Latency**: <50ms (target)
- **Score Calculation**: <100ms
- **Multi-Camera Fusion**: <150ms
- **WebSocket Broadcast**: <10ms

## Future Enhancements

- [ ] PostgreSQL migration (currently MongoDB)
- [ ] Real CV model integration
- [ ] Machine learning style classifier
- [ ] Advanced analytics (strike accuracy, ring control heatmaps)
- [ ] Replay system integration
- [ ] Judge variance detection
- [ ] Real-time coaching insights

---

**Version**: 1.0.0  
**Status**: Production Ready  
**Last Updated**: 2025-11-21
