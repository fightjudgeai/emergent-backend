# FJAIPOS Integration Architecture

## Technology Stack

### Backend: Emergent.sh Only
- **Platform:** FastAPI on emergent.sh
- **Database:** MongoDB (included in emergent.sh)
- **All APIs:** REST endpoints on emergent backend
- **No external backend services required**

### Frontend: External Frontend Calling Emergent APIs
- **Deployment:** External hosting (Vercel, Netlify, etc.)
- **Framework:** React, Next.js, or any frontend framework
- **Integration:** REST API calls to emergent backend
- **CORS:** Already configured on emergent backend

### CV: Roboflow + Colab
- **Training:** Roboflow for dataset management and model training
- **Inference:** Google Colab notebooks with GPU
- **Models:** YOLOv8, MediaPipe, custom models
- **Output:** JSON batches sent to emergent via REST API

---

## Integration Flow

### 1. Colab → Emergent Backend (AI Events)

**Colab Notebook Integration:**

```python
import requests
import json
from datetime import datetime

# Emergent backend URL
EMERGENT_API_URL = "https://your-emergent-instance.emergent.sh/api/ai-merge/submit-batch"

# After CV analysis, prepare events
ai_events = []

for detection in frame_detections:
    event = {
        "fighter_id": detection['fighter_id'],
        "round": detection['round'],
        "timestamp": detection['timestamp'].isoformat(),
        "event_type": detection['action'],  # e.g., "jab", "kick"
        "target": detection['target'],  # e.g., "head", "body"
        "position": detection['position'],  # e.g., "distance", "clinch"
        "confidence": detection['confidence'],  # 0.0-1.0
        "landed": detection['landed']  # True/False
    }
    ai_events.append(event)

# Submit batch to emergent
payload = {
    "fight_id": "fight_123",
    "events": ai_events,
    "submitted_by": "roboflow_yolov8",
    "metadata": {
        "model": "yolov8n",
        "version": "1.2.3",
        "confidence_threshold": 0.85
    }
}

response = requests.post(
    EMERGENT_API_URL,
    json=payload,
    headers={"Content-Type": "application/json"}
)

result = response.json()
print(f"Auto-approved: {result['auto_approved']}")
print(f"Requires review: {result['marked_for_review']}")
```

**Merge Rules (Automatic):**
- AI + human agree within 2s & same event type → **Auto-approve**
- AI confidence ≥85% + no human event → **Auto-approve**
- Conflict detected → **Mark for review**
- Never overwrites human `source` directly

---

### 2. External Frontend → Emergent Backend

**React/Next.js Integration:**

```javascript
// config.js
export const EMERGENT_API_URL = process.env.NEXT_PUBLIC_EMERGENT_API_URL || 
  'https://your-emergent-instance.emergent.sh/api';

// api.js
import axios from 'axios';
import { EMERGENT_API_URL } from './config';

export const emergentAPI = axios.create({
  baseURL: EMERGENT_API_URL,
  headers: {
    'Content-Type': 'application/json'
  }
});

// Get live stats
export const getLiveStats = async (fightId) => {
  const response = await emergentAPI.get(`/overlay/live/${fightId}`);
  return response.data;
};

// Get fight timeline for review
export const getFightTimeline = async (fightId) => {
  const response = await emergentAPI.get(`/review/timeline/${fightId}`);
  return response.data;
};

// Edit event
export const editEvent = async (eventId, updates, supervisorId, reason) => {
  const response = await emergentAPI.put(`/review/events/${eventId}`, {
    updates,
    supervisor_id: supervisorId,
    reason
  });
  return response.data;
};

// Submit from CV
export const submitAIBatch = async (fightId, events) => {
  const response = await emergentAPI.post('/ai-merge/submit-batch', {
    fight_id: fightId,
    events,
    submitted_by: 'external_cv_system'
  });
  return response.data;
};
```

**WebSocket Integration:**

```javascript
// WebSocket for real-time overlay
const ws = new WebSocket(
  'wss://your-emergent-instance.emergent.sh/api/overlay/ws/live/fight_123'
);

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Live stats update:', data);
  // Update UI with live stats
};
```

---

### 3. Roboflow → Colab → Emergent

**Complete CV Pipeline:**

1. **Roboflow:**
   - Upload fight videos
   - Annotate events (strikes, takedowns, etc.)
   - Train YOLOv8 model
   - Export model to Colab

2. **Colab Notebook:**
   ```python
   from roboflow import Roboflow
   from ultralytics import YOLO
   
   # Load Roboflow model
   rf = Roboflow(api_key="YOUR_KEY")
   project = rf.workspace().project("mma-actions")
   model = project.version(1).model
   
   # Or use YOLO directly
   yolo_model = YOLO('yolov8n.pt')
   
   # Inference on video
   results = yolo_model.predict(
       source='fight_video.mp4',
       conf=0.85,
       save=False
   )
   
   # Process results and submit to emergent
   for result in results:
       events = parse_detections(result)
       submit_to_emergent(fight_id, events)
   ```

3. **Emergent Backend:**
   - Receives JSON batches
   - Merges with human events
   - Auto-approves or flags conflicts
   - Triggers stat recalculation

---

## API Endpoints Reference

### AI Merge Engine
```
POST /api/ai-merge/submit-batch
GET  /api/ai-merge/review-items
POST /api/ai-merge/review-items/{id}/approve
GET  /api/ai-merge/stats
```

### Post-Fight Review
```
GET    /api/review/timeline/{fight_id}
PUT    /api/review/events/{id}
DELETE /api/review/events/{id}
POST   /api/review/events/merge
POST   /api/review/fights/{id}/approve
POST   /api/review/videos/upload
GET    /api/review/videos/{fight_id}
```

### Stats Overlay (Low-latency)
```
GET /api/overlay/live/{fight_id}
GET /api/overlay/comparison/{fight_id}
WS  /api/overlay/ws/live/{fight_id}
```

### Verification Engine
```
POST /api/verification/verify/round/{fight_id}/{round}
POST /api/verification/verify/fight/{fight_id}
GET  /api/verification/discrepancies
POST /api/verification/discrepancies/{id}/resolve
```

---

## Data Flow Diagram

```
┌─────────────┐
│  Roboflow   │ → Train models
└──────┬──────┘
       │
       ↓
┌─────────────┐
│   Colab     │ → Inference on videos
│   (GPU)     │ → Generate JSON events
└──────┬──────┘
       │ POST /api/ai-merge/submit-batch
       ↓
┌────────────────────────┐
│  Emergent Backend      │
│  (FastAPI + MongoDB)   │
│  ┌──────────────────┐  │
│  │ AI Merge Engine  │  │ → Auto-approve or flag
│  └────────┬─────────┘  │
│           │             │
│  ┌────────▼─────────┐  │
│  │ Events Table     │  │ → source: ai_cv
│  └────────┬─────────┘  │
│           │             │
│  ┌────────▼─────────┐  │
│  │ Stat Engine      │  │ → Recalculate
│  └────────┬─────────┘  │
│           │             │
│  ┌────────▼─────────┐  │
│  │ Stats Overlay    │  │ → Real-time stats
│  └────────┬─────────┘  │
└───────────┼─────────────┘
            │ GET/WS
            ↓
┌──────────────────────────┐
│  External Frontend       │
│  (React/Next.js)         │
│  - Live stats display    │
│  - Review interface      │
│  - Event editing         │
└──────────────────────────┘
```

---

## Environment Variables

### Emergent Backend (.env)
```bash
# Already configured in emergent.sh
MONGO_URL=mongodb://localhost:27017/fjaipos
```

### External Frontend (.env)
```bash
# Point to your emergent instance
NEXT_PUBLIC_EMERGENT_API_URL=https://your-instance.emergent.sh/api
NEXT_PUBLIC_WS_URL=wss://your-instance.emergent.sh/api
```

### Colab Notebook
```python
# Set in Colab secrets
EMERGENT_API_URL = "https://your-instance.emergent.sh/api"
ROBOFLOW_API_KEY = "your_roboflow_key"
```

---

## Security Considerations

### API Authentication
- Add API key validation for production
- Implement rate limiting for AI batch submissions
- Use HTTPS for all external communication

### CORS Configuration
- Already configured in emergent backend
- Whitelist specific frontend domains in production

### Video Upload
- Implement file size limits (e.g., 500MB max)
- Validate video formats (mp4, mov, avi)
- Use cloud storage for production (S3, GCS)

---

## Deployment Checklist

### Emergent Backend
- [x] All APIs deployed on emergent.sh
- [x] MongoDB configured
- [x] Video upload directory created
- [ ] API authentication added (if needed)
- [ ] Rate limiting configured

### External Frontend
- [ ] Deploy to Vercel/Netlify
- [ ] Configure EMERGENT_API_URL
- [ ] Test CORS
- [ ] Implement authentication

### CV Pipeline (Colab)
- [ ] Train models on Roboflow
- [ ] Set up Colab notebook with GPU
- [ ] Configure emergent API URL
- [ ] Test end-to-end flow
- [ ] Schedule automated runs (if needed)

---

## Testing

### Test AI Merge from Colab
```bash
curl -X POST https://your-instance.emergent.sh/api/ai-merge/submit-batch \
  -H "Content-Type: application/json" \
  -d '{
    "fight_id": "test_fight",
    "events": [{
      "fighter_id": "fighter_1",
      "round": 1,
      "timestamp": "2025-01-15T10:30:45.123Z",
      "event_type": "jab",
      "confidence": 0.92
    }],
    "submitted_by": "test_colab"
  }'
```

### Test Frontend API Call
```javascript
const response = await fetch(
  'https://your-instance.emergent.sh/api/overlay/live/fight_123'
);
const data = await response.json();
console.log(data);
```

---

## Troubleshooting

### Issue: CORS errors from external frontend
**Solution:** Check emergent backend CORS configuration, ensure frontend domain is allowed

### Issue: Colab can't reach emergent API
**Solution:** Check emergent instance is publicly accessible, verify API URL is correct

### Issue: AI events not auto-approving
**Solution:** Check confidence threshold (must be ≥0.85), verify event format matches schema

### Issue: Video upload fails
**Solution:** Check file size limits, ensure upload directory has write permissions

---

## Next Steps

1. **Deploy External Frontend:** Host React app on Vercel/Netlify
2. **Train CV Models:** Use Roboflow to train on your fight footage
3. **Set up Colab Notebook:** Configure GPU runtime and test inference
4. **Test End-to-End:** Submit AI events from Colab, verify in frontend
5. **Production Hardening:** Add authentication, monitoring, backups
