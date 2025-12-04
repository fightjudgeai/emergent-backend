# Public Stats API - UFCstats-Style Fight Statistics

## 🎯 Overview

The Public Stats API provides UFCstats-style fight statistics with round-by-round breakdowns. This endpoint is **PUBLIC** and does not require authentication, making it suitable for:

- Public fight stat displays
- Embedding in websites/apps
- Media and journalism use
- Fan engagement platforms

---

## 📍 Endpoint

```
GET /v1/public/fight/{fight_id}
```

**No authentication required** - This is a public endpoint.

---

## 🔑 Parameters

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `fight_id` | string | Fight UUID or fight code | `"UFC309_JONES_MIOCIC"` or UUID |

---

## 📊 Response Format

```json
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
                "sig": "24/55",
                "total": "39/88",
                "td": "2/5",
                "sub": 1,
                "kd": 1,
                "ctrl": "1:11",
                "acc_sig": 0.44,
                "acc_td": 0.40
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
        },
        {
            "round": 2,
            "red": { ... },
            "blue": { ... }
        }
    ],
    "_note": "Strike attempts are estimated. Takedown/submission data requires event normalization system (migration 005)."
}
```

---

## 📐 Field Definitions

### Fight Metadata

| Field | Type | Description |
|-------|------|-------------|
| `event` | string | Event name (e.g., "UFC 309") |
| `weight_class` | string | Weight class (e.g., "Heavyweight") |
| `rounds` | integer | Scheduled number of rounds |
| `result` | string | Fight result method (KO, SUB, DEC, U-DEC, S-DEC, M-DEC, DRAW, NC) |

### Fighter Info

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Fighter full name |
| `winner` | boolean | true if fighter won, false if lost, null if ongoing/draw |

### Round Statistics

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `sig` | string | Significant strikes (landed/attempted) | "24/55" |
| `total` | string | Total strikes (landed/attempted) | "39/88" |
| `td` | string | Takedowns (landed/attempted) | "2/5" |
| `sub` | integer | Submission attempts | 1 |
| `kd` | integer | Knockdowns | 1 |
| `ctrl` | string | Control time (M:SS format) | "1:11" |
| `acc_sig` | float | Significant strike accuracy (0.44 = 44%) | 0.44 |
| `acc_td` | float | Takedown accuracy (0.40 = 40%) | 0.40 |

---

## 🧪 Example Requests

### Using Fight Code

```bash
curl -X GET "http://localhost:8002/v1/public/fight/UFC309_JONES_MIOCIC"
```

### Using Fight UUID

```bash
curl -X GET "http://localhost:8002/v1/public/fight/550e8400-e29b-41d4-a716-446655440000"
```

### Production URL

```bash
curl -X GET "https://your-domain.com/v1/public/fight/UFC309_JONES_MIOCIC"
```

---

## ⚠️ Current Limitations

### Strike Attempts
**Status**: Estimated

Strike attempts are currently **estimated** from landed strikes using typical accuracy rates (40-45%). This is because the current `round_state` schema only tracks landed strikes.

**Solution**: Run migration `005_stat_engine_normalization.sql` to enable the event system, which tracks `STR_ATT` and `STR_LAND` events separately for accurate attempt counts.

### Takedowns & Submissions
**Status**: Not Tracked

Takedown and submission statistics are currently **not tracked** in the `round_state` table. These fields will return:
- `"td": "0/0"`
- `"sub": 0`
- `"acc_td": 0.00`

**Solution**: The event normalization system (migration 005) adds support for:
- `TD_ATT` and `TD_LAND` events for takedowns
- `SUB_ATT` events for submissions

Once implemented, these stats will be accurately calculated from the event stream.

---

## 🔄 Data Flow

```
┌─────────────────────────────────────────────────────────┐
│              Current Implementation                     │
└─────────────────────────────────────────────────────────┘

round_state table
    ↓
  (red_sig_strikes, red_strikes, red_knockdowns, red_control_sec)
    ↓
Public Stats Service
    ↓
  - Format control time (seconds → M:SS)
  - Estimate attempts from landed strikes
  - Calculate accuracy
    ↓
UFCstats-style JSON response
```

```
┌─────────────────────────────────────────────────────────┐
│           Future Implementation (After Migration)        │
└─────────────────────────────────────────────────────────┘

fight_events table
    ↓
  (STR_ATT, STR_LAND, TD_ATT, TD_LAND, SUB_ATT events)
    ↓
Event Service → Aggregate Stats
    ↓
Public Stats Service
    ↓
  - Accurate attempt counts
  - Real takedown data
  - Real submission data
    ↓
Full UFCstats-style JSON response
```

---

## 📊 Result Method Codes

| Code | Description |
|------|-------------|
| `KO` | Knockout or TKO |
| `SUB` | Submission |
| `DEC` | Decision (generic) |
| `U-DEC` | Unanimous Decision |
| `S-DEC` | Split Decision |
| `M-DEC` | Majority Decision |
| `DRAW` | Draw |
| `NC` | No Contest |

---

## 🚀 Use Cases

### 1. Public Fight Stats Display
Embed live or historical fight statistics on your website:

```javascript
fetch('https://api.fightjudge.ai/v1/public/fight/UFC309_JONES_MIOCIC')
  .then(res => res.json())
  .then(data => {
    console.log(`Winner: ${data.fighters.red.winner ? data.fighters.red.name : data.fighters.blue.name}`);
    console.log(`Result: ${data.fight.result}`);
    
    data.rounds.forEach(round => {
      console.log(`Round ${round.round}:`);
      console.log(`  Red Sig Strikes: ${round.red.sig} (${round.red.acc_sig * 100}% accuracy)`);
      console.log(`  Blue Sig Strikes: ${round.blue.sig} (${round.blue.acc_sig * 100}% accuracy)`);
    });
  });
```

### 2. Media & Journalism
Generate fight summaries for articles:

```python
import requests

response = requests.get('https://api.fightjudge.ai/v1/public/fight/UFC309_JONES_MIOCIC')
fight = response.json()

print(f"{fight['fighters']['red']['name']} vs {fight['fighters']['blue']['name']}")
print(f"Result: {fight['fight']['result']} - {fight['rounds'][-1]['round']} rounds")

# Calculate total stats
total_red_sig = sum(int(r['red']['sig'].split('/')[0]) for r in fight['rounds'])
total_blue_sig = sum(int(r['blue']['sig'].split('/')[0]) for r in fight['rounds'])

print(f"Total Significant Strikes: {total_red_sig} - {total_blue_sig}")
```

### 3. Fantasy Sports Platforms
Calculate fantasy points from public stats:

```javascript
async function calculateFantasyPoints(fightId) {
  const res = await fetch(`/v1/public/fight/${fightId}`);
  const fight = await res.json();
  
  let redPoints = 0;
  fight.rounds.forEach(round => {
    const sigLanded = parseInt(round.red.sig.split('/')[0]);
    redPoints += sigLanded * 0.5;  // 0.5 points per sig strike
    redPoints += round.red.kd * 5;  // 5 points per knockdown
  });
  
  return redPoints;
}
```

---

## 🔗 Related Endpoints

- **Authenticated Live Feed**: `GET /v1/fights/{fight_code}/live` (requires API key)
- **Event Stream**: `GET /v1/events/{fight_id}` (requires API key, provides granular events)
- **Fantasy Stats**: `GET /v1/fantasy/{fight_id}/{profile_id}` (requires API key)

---

## 📝 Integration Steps

1. **Test the Endpoint**
   ```bash
   curl "http://localhost:8002/v1/public/fight/{your_fight_id}"
   ```

2. **Parse the Response**
   - Extract fight metadata
   - Loop through rounds array
   - Display stats in your UI

3. **Handle Edge Cases**
   - Check for 404 if fight not found
   - Handle null `winner` for ongoing fights
   - Display `_note` to inform users about data limitations

4. **(Optional) Upgrade to Event System**
   - Run migration `005_stat_engine_normalization.sql`
   - Get accurate attempt counts
   - Access takedown and submission data

---

## 🔐 Public vs Authenticated APIs

| Feature | Public API | Authenticated API |
|---------|------------|-------------------|
| **Authentication** | ❌ None required | ✅ API key required |
| **Fight Stats** | ✅ Basic stats | ✅ Full stats with AI metrics |
| **Real-time Feed** | ❌ No | ✅ WebSocket available |
| **Fantasy Points** | ❌ No | ✅ Yes |
| **Sportsbook Markets** | ❌ No | ✅ Yes |
| **Event Stream** | ❌ No | ✅ Yes (granular events) |
| **Rate Limiting** | ✅ Generous | ✅ Based on plan |

---

## 📚 Additional Resources

- **Service Code**: `/app/datafeed_api/services/public_stats_service.py`
- **API Routes**: `/app/datafeed_api/api/public_routes.py`
- **Event Normalization Guide**: `/app/datafeed_api/STAT_ENGINE_NORMALIZATION_GUIDE.md`

---

## ✅ Status

| Component | Status | Notes |
|-----------|--------|-------|
| Public Stats Endpoint | ✅ Live | Working with estimated attempts |
| Basic Fight Data | ✅ Complete | Event, fighters, rounds |
| Strike Stats | ✅ Complete | With estimated attempts |
| Knockdown Stats | ✅ Complete | Accurate from round_state |
| Control Time | ✅ Complete | Formatted M:SS |
| Takedown Stats | ⏳ Pending | Requires event system |
| Submission Stats | ⏳ Pending | Requires event system |

---

**🎉 Public Stats API is live and ready to use!**

For accurate attempt counts and full stats (takedowns, submissions), run migration 005 to enable the event normalization system.
