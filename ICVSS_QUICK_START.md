# ICVSS Quick Start Guide

**Get your CV system integrated in 10 minutes**

---

## 🚀 For Operators (Testing)

### **Step 1: Create a Bout**
1. Navigate to home page
2. Click "Start New Fight"
3. Enter fighter names and rounds
4. Click "Start Bout"

### **Step 2: Enable CV Mode**
1. Go to Operator Panel
2. Find the purple **"ICVSS - CV Enhanced Scoring"** card
3. Toggle **"CV Mode"** switch to **ON**
4. Wait for green WiFi icon (connected)

### **Step 3: Test with Simulator**
1. Click **"Simulate CV Events"** button
2. Watch 10 CV events being generated over 5 seconds
3. See real-time score calculation
4. View breakdown: Striking, Grappling, Control

### **Step 4: View Results**
Score card shows:
- **10-9, 10-8, 10-7, or 10-10**
- Winner (Fighter1/Fighter2)
- CV vs Judge contribution (70/30)
- Confidence percentage
- Event counts

### **Step 5: Lock Round**
1. Click **"Lock Round"** when satisfied
2. SHA256 hash generated for integrity
3. Round is immutable

---

## 🎯 For CV Vendors (Integration)

### **Authentication**
Request API key from system admin:
```bash
X-API-Key: your-vendor-api-key
```

### **Event Format**
Send events to:
```
POST https://bettingdata.preview.emergentagent.com/api/icvss/cv/event
```

**Request Body**:
```json
{
  "vendor_id": "your_vendor_name",
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

### **Supported Event Types**
Map your events to these types:

**Strikes**:
- `strike_jab`, `strike_cross`, `strike_hook`, `strike_uppercut`
- `strike_elbow`, `strike_knee`

**Kicks**:
- `kick_head`, `kick_body`, `kick_low`, `kick_front`

**Damage**:
- `rock` (wobbles fighter)
- `KD_flash` (quick knockdown)
- `KD_hard` (solid knockdown)
- `KD_nearfinish` (almost finished)

**Grappling**:
- `td_landed`, `td_stuffed`
- `sub_attempt_light`, `sub_attempt_deep`, `sub_attempt_nearfinish`
- `sweep`

**Control**:
- `control_top`, `control_back`, `control_cage`

### **Field Mappings**
Your system → ICVSS standard:

| Your Field | ICVSS Field | Type | Range |
|------------|-------------|------|-------|
| `confidence` / `certainty` | `confidence` | float | 0.0-1.0 |
| `impact` / `severity` | `severity` | float | 0.0-1.0 |
| `timestamp` | `timestamp_ms` | int | milliseconds |
| `fighter` | `fighter_id` | string | "fighter1"/"fighter2" |

### **Python Example**
```python
import requests
import time

BASE_URL = "https://bettingdata.preview.emergentagent.com/api/icvss"
API_KEY = "your-vendor-api-key"

def send_cv_event(bout_id, round_id, fighter, event_type, confidence, severity):
    response = requests.post(
        f"{BASE_URL}/cv/event",
        headers={"X-API-Key": API_KEY},
        json={
            "vendor_id": "your_vendor_name",
            "raw_data": {
                "bout_id": bout_id,
                "round_id": round_id,
                "fighter_id": fighter,
                "type": event_type,
                "certainty": confidence,
                "impact": severity,
                "timestamp_ms": int(time.time() * 1000)
            }
        }
    )
    return response.json()

# Example usage
result = send_cv_event(
    bout_id="bout-123",
    round_id="round-456",
    fighter="fighter1",
    event_type="strike_cross",
    confidence=0.95,
    severity=0.8
)

print(result)  # {"success": true, "message": "Event accepted"}
```

### **JavaScript Example**
```javascript
const BASE_URL = "https://bettingdata.preview.emergentagent.com/api/icvss";
const API_KEY = "your-vendor-api-key";

async function sendCVEvent(boutId, roundId, fighter, eventType, confidence, severity) {
  const response = await fetch(`${BASE_URL}/cv/event`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': API_KEY
    },
    body: JSON.stringify({
      vendor_id: "your_vendor_name",
      raw_data: {
        bout_id: boutId,
        round_id: roundId,
        fighter_id: fighter,
        type: eventType,
        certainty: confidence,
        impact: severity,
        timestamp_ms: Date.now()
      }
    })
  });
  
  return await response.json();
}

// Example usage
sendCVEvent(
  "bout-123",
  "round-456", 
  "fighter1",
  "strike_cross",
  0.95,
  0.8
).then(result => console.log(result));
```

---

## 🔍 Troubleshooting

### **Issue: Events Rejected**
**Cause**: Low confidence (<0.6)
**Solution**: Increase confidence threshold or improve CV model

### **Issue: Duplicate Events**
**Cause**: Multiple detections within 80-150ms
**Solution**: Already handled by deduplication engine

### **Issue: Scores Don't Match Expectations**
**Cause**: Understanding scoring weights
**Solution**: Review breakdown:
- Striking: 50%
- Grappling: 40%
- Control: 10%
- CV: 70%, Judge: 30%

### **Issue: WebSocket Disconnects**
**Cause**: Network instability
**Solution**: System auto-reconnects. Check connection status.

### **Issue: Round Won't Lock**
**Cause**: No events or incomplete round
**Solution**: Ensure at least 1 event logged

---

## 📊 Monitoring

### **Check System Health**
```bash
curl https://bettingdata.preview.emergentagent.com/api/icvss/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "ICVSS",
  "version": "1.0.0"
}
```

### **Get Statistics**
```bash
curl https://bettingdata.preview.emergentagent.com/api/icvss/stats
```

Response shows:
- Total events processed
- Deduplication window
- WebSocket connections
- Active rounds

---

## 🎯 Best Practices

### **For CV Vendors**:
1. **Send events immediately** (don't batch)
2. **Use realistic confidence scores** (0.6-0.99)
3. **Map severity accurately** (0.0 = glancing, 1.0 = flush)
4. **Test with simulator first**
5. **Monitor rejection rate** (<5% is good)

### **For Operators**:
1. **Enable CV mode at round start**
2. **Monitor connection status** (green WiFi)
3. **Review scores before locking**
4. **Lock rounds promptly** for integrity
5. **Use simulator for training**

### **For Judges**:
1. **CV mode supplements judging** (doesn't replace)
2. **Manual events still 30% weight**
3. **Review CV scores for validation**
4. **Flag discrepancies** to operator

---

## 🚨 Emergency Procedures

### **If CV System Fails Mid-Round**:
1. Toggle CV Mode **OFF**
2. System reverts to manual judging
3. Continue round normally
4. Re-enable CV Mode next round if fixed

### **If Scores Seem Wrong**:
1. Click **"Refresh Score"**
2. Check event counts (CV vs Judge)
3. Review breakdown (Striking/Grappling/Control)
4. Contact tech support if issue persists

### **If WebSocket Drops**:
1. System auto-reconnects within 5s
2. If not, toggle CV Mode OFF then ON
3. Scores are saved, no data loss

---

## 📞 Support

**Technical Issues**: Check `/app/ICVSS_API_DOCUMENTATION.md`
**Testing**: Run `/app/backend/tests/test_icvss.py`
**Demo**: Run `/app/backend/icvss/demo_client.py`

**Happy Scoring! 🥊**
