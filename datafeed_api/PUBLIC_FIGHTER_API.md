# Public Fighter API - Career Statistics & History

## 🎯 Overview

The Public Fighter API provides comprehensive career statistics and fight history for individual fighters. This endpoint is **PUBLIC** and requires no authentication.

---

## 📍 Endpoint

```
GET /v1/public/fighter/{fighter_id}
```

**Authentication**: ❌ **NONE REQUIRED** (Public endpoint)

---

## 🔑 Parameters

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `fighter_id` | string | Fighter UUID | `"550e8400-e29b-41d4-a716-446655440000"` |

---

## 📊 Response Format

```json
{
    "fighter": {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "name": "John Doe",
        "nickname": "The Hammer",
        "country": "USA"
    },
    "record": {
        "wins": 15,
        "losses": 3,
        "draws": 0,
        "no_contests": 0
    },
    "career_totals": {
        "total_fights": 18,
        "kos": 8,
        "submissions": 3,
        "decisions": 4,
        "sig_strikes": "1250/2800",
        "knockdowns": 12,
        "total_control_time": "45:30",
        "avg_sig_strike_accuracy": 0.45,
        "avg_control_time_per_fight": "2:32"
    },
    "fight_history": [
        {
            "fight_code": "UFC309_DOE_SMITH",
            "event_id": "event-uuid",
            "result": "WIN",
            "method": "KO",
            "sig_strikes": "85/180",
            "knockdowns": 2,
            "control_time": "3:45"
        },
        {
            "fight_code": "UFC308_DOE_JONES",
            "event_id": "event-uuid",
            "result": "LOSS",
            "method": "DEC",
            "sig_strikes": "72/165",
            "knockdowns": 0,
            "control_time": "1:22"
        }
    ],
    "trends": {
        "strike_accuracy": [
            {"fight_code": "UFC309_DOE_SMITH", "accuracy": 0.47},
            {"fight_code": "UFC308_DOE_JONES", "accuracy": 0.44}
        ],
        "control_time": [
            {"fight_code": "UFC309_DOE_SMITH", "control_seconds": 225, "control_formatted": "3:45"},
            {"fight_code": "UFC308_DOE_JONES", "control_seconds": 82, "control_formatted": "1:22"}
        ]
    }
}
```

---

## 📐 Field Definitions

### Fighter Info

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Fighter UUID |
| `name` | string | Fighter full name |
| `nickname` | string | Fighter nickname |
| `country` | string | Country (ISO code or full name) |

### Record

| Field | Type | Description |
|-------|------|-------------|
| `wins` | integer | Total wins |
| `losses` | integer | Total losses |
| `draws` | integer | Total draws |
| `no_contests` | integer | Total no contests |

### Career Totals

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `total_fights` | integer | Total fights in career | 18 |
| `kos` | integer | Wins by KO/TKO | 8 |
| `submissions` | integer | Wins by submission | 3 |
| `decisions` | integer | Wins by decision | 4 |
| `sig_strikes` | string | Career sig strikes (landed/attempted) | "1250/2800" |
| `knockdowns` | integer | Career knockdowns scored | 12 |
| `total_control_time` | string | Career control time (M:SS format) | "45:30" |
| `avg_sig_strike_accuracy` | float | Average strike accuracy (0.45 = 45%) | 0.45 |
| `avg_control_time_per_fight` | string | Average control per fight (M:SS) | "2:32" |

### Fight History

| Field | Type | Description |
|-------|------|-------------|
| `fight_code` | string | Fight identifier |
| `event_id` | string | Event UUID |
| `result` | string | WIN, LOSS, DRAW, or NC |
| `method` | string | Finish method (KO, SUB, DEC, etc.) |
| `sig_strikes` | string | Significant strikes (landed/attempted) |
| `knockdowns` | integer | Knockdowns in fight |
| `control_time` | string | Control time (M:SS format) |

### Trends

**Strike Accuracy Trend:**
- `fight_code`: Fight identifier
- `accuracy`: Strike accuracy for that fight (0.0-1.0)

**Control Time Trend:**
- `fight_code`: Fight identifier
- `control_seconds`: Control time in seconds
- `control_formatted`: Control time in M:SS format

---

## 🧪 Example Requests

### Basic Request

```bash
curl -X GET "http://localhost:8002/v1/public/fighter/550e8400-e29b-41d4-a716-446655440000"
```

### Production URL

```bash
curl -X GET "https://api.fightjudge.ai/v1/public/fighter/550e8400-e29b-41d4-a716-446655440000"
```

---

## 🎯 Use Cases

### 1. Fighter Profile Page

```javascript
fetch(`/v1/public/fighter/${fighterId}`)
  .then(res => res.json())
  .then(fighter => {
    console.log(`${fighter.fighter.name} (${fighter.fighter.nickname})`);
    console.log(`Record: ${fighter.record.wins}-${fighter.record.losses}-${fighter.record.draws}`);
    console.log(`Strike Accuracy: ${(fighter.career_totals.avg_sig_strike_accuracy * 100).toFixed(1)}%`);
    
    // Display fight history
    fighter.fight_history.forEach(fight => {
      console.log(`${fight.fight_code}: ${fight.result} via ${fight.method}`);
    });
  });
```

### 2. Career Statistics Dashboard

```python
import requests
import matplotlib.pyplot as plt

# Get fighter data
response = requests.get(f'/v1/public/fighter/{fighter_id}')
fighter = response.json()

# Extract accuracy trend
fight_codes = [t['fight_code'] for t in fighter['trends']['strike_accuracy']]
accuracies = [t['accuracy'] for t in fighter['trends']['strike_accuracy']]

# Plot accuracy over time
plt.plot(accuracies)
plt.title(f"{fighter['fighter']['name']} - Strike Accuracy Trend")
plt.xlabel('Fight')
plt.ylabel('Accuracy')
plt.ylim(0, 1)
plt.show()
```

### 3. Fighter Comparison Tool

```javascript
async function compareFighters(fighterId1, fighterId2) {
  const [f1, f2] = await Promise.all([
    fetch(`/v1/public/fighter/${fighterId1}`).then(r => r.json()),
    fetch(`/v1/public/fighter/${fighterId2}`).then(r => r.json())
  ]);
  
  return {
    fighter1: {
      name: f1.fighter.name,
      record: `${f1.record.wins}-${f1.record.losses}`,
      accuracy: f1.career_totals.avg_sig_strike_accuracy,
      ko_rate: f1.career_totals.kos / f1.career_totals.total_fights
    },
    fighter2: {
      name: f2.fighter.name,
      record: `${f2.record.wins}-${f2.record.losses}`,
      accuracy: f2.career_totals.avg_sig_strike_accuracy,
      ko_rate: f2.career_totals.kos / f2.career_totals.total_fights
    }
  };
}
```

### 4. Trend Analysis

```python
def analyze_fighter_trends(fighter_id):
    response = requests.get(f'/v1/public/fighter/{fighter_id}')
    fighter = response.json()
    
    # Calculate accuracy trend direction
    accuracies = [t['accuracy'] for t in fighter['trends']['strike_accuracy']]
    
    if len(accuracies) >= 5:
        recent_avg = sum(accuracies[-5:]) / 5
        career_avg = fighter['career_totals']['avg_sig_strike_accuracy']
        
        if recent_avg > career_avg:
            print(f"{fighter['fighter']['name']} is improving (recent: {recent_avg:.2f} vs career: {career_avg:.2f})")
        else:
            print(f"{fighter['fighter']['name']} accuracy declining (recent: {recent_avg:.2f} vs career: {career_avg:.2f})")
    
    # Analyze control time
    control_times = [t['control_seconds'] for t in fighter['trends']['control_time']]
    avg_recent_control = sum(control_times[-5:]) / 5 if len(control_times) >= 5 else 0
    
    print(f"Recent avg control time: {avg_recent_control//60}:{avg_recent_control%60:02d}")
```

---

## 📊 Data Insights

### Win Methods Breakdown

The API provides a breakdown of how a fighter wins:
- **KOs**: Knockouts and TKOs
- **Submissions**: Submission victories
- **Decisions**: Decision wins (unanimous, split, majority)

### Trend Analysis

**Strike Accuracy Trend:**
Shows how a fighter's accuracy changes over time. Useful for:
- Identifying improving or declining fighters
- Predicting future performance
- Matchup analysis

**Control Time Trend:**
Shows grappling dominance over career. Useful for:
- Identifying style changes
- Predicting grappling-heavy strategies
- Matchup predictions

---

## ⚠️ Current Limitations

### Strike Attempts: Estimated
- Attempts are **estimated** from landed strikes
- Once migration 005 is run, this will use actual event data

### Takedowns & Submissions: Limited
- Only submission **wins** are counted (from fight results)
- Submission **attempts** per fight not available
- Takedown statistics not available

### Solution
Run migration `005_stat_engine_normalization.sql` to enable:
- Accurate strike attempt tracking
- Per-fight submission attempts
- Takedown statistics

---

## 🚀 Integration Guide

### Step 1: Fetch Fighter Data

```javascript
const fighterId = '550e8400-e29b-41d4-a716-446655440000';
const response = await fetch(`/v1/public/fighter/${fighterId}`);
const fighter = await response.json();
```

### Step 2: Display Fighter Card

```html
<div class="fighter-card">
  <h1>${fighter.fighter.name}</h1>
  <p class="nickname">"${fighter.fighter.nickname}"</p>
  <p class="record">
    Record: ${fighter.record.wins}-${fighter.record.losses}-${fighter.record.draws}
  </p>
  <div class="stats">
    <div>Strike Accuracy: ${(fighter.career_totals.avg_sig_strike_accuracy * 100).toFixed(1)}%</div>
    <div>KO Rate: ${((fighter.career_totals.kos / fighter.career_totals.total_fights) * 100).toFixed(1)}%</div>
    <div>Total Fights: ${fighter.career_totals.total_fights}</div>
  </div>
</div>
```

### Step 3: Display Fight History

```javascript
fighter.fight_history.forEach(fight => {
  const resultClass = fight.result === 'WIN' ? 'win' : 'loss';
  
  document.getElementById('fight-history').innerHTML += `
    <div class="fight ${resultClass}">
      <span>${fight.fight_code}</span>
      <span>${fight.result} via ${fight.method}</span>
      <span>Strikes: ${fight.sig_strikes}</span>
    </div>
  `;
});
```

### Step 4: Visualize Trends

```javascript
// Using Chart.js
const accuracyData = fighter.trends.strike_accuracy.map(t => t.accuracy);
const fightLabels = fighter.trends.strike_accuracy.map((t, i) => `Fight ${i+1}`);

new Chart(ctx, {
  type: 'line',
  data: {
    labels: fightLabels,
    datasets: [{
      label: 'Strike Accuracy',
      data: accuracyData,
      borderColor: 'rgb(75, 192, 192)',
      tension: 0.1
    }]
  }
});
```

---

## 🔗 Related Endpoints

- **Fight Stats**: `GET /v1/public/fight/{fight_id}` - Detailed fight statistics
- **Fight with Fantasy**: `GET /v1/public/fight/{fight_id}?fantasy_profile=fantasy.basic` - Fight stats with fantasy points

---

## 📚 Documentation

- **Public Stats API Guide**: `/app/datafeed_api/PUBLIC_STATS_API.md`
- **Service Code**: `/app/datafeed_api/services/public_stats_service.py`
- **API Routes**: `/app/datafeed_api/api/public_routes.py`

---

## ✅ Status

| Feature | Status | Notes |
|---------|--------|-------|
| Fighter Profile | ✅ Complete | Name, nickname, country |
| Win/Loss Record | ✅ Complete | Accurate from fight results |
| Career Totals | ✅ Complete | All major stats |
| Win Methods | ✅ Complete | KO, SUB, DEC breakdown |
| Fight History | ✅ Complete | Per-fight results |
| Strike Accuracy Trend | ✅ Complete | Estimated attempts |
| Control Time Trend | ✅ Complete | Accurate |
| Takedown Stats | ⏳ Pending | Requires event system |

---

**🎉 Public Fighter API is live and ready to use!**
