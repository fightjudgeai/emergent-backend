# Fantasy Scoring API Guide

## 🎯 Overview

The Fantasy Scoring System adds fantasy league and sportsbook functionality to the Fight Judge AI Data Feed. It calculates fantasy points for fighters based on configurable scoring profiles.

---

## 📊 Scoring Profiles

### 1. fantasy.basic
**Target:** Casual fantasy leagues

**Weights:**
- Significant Strike: 0.5 points
- Knockdown: 5.0 points
- Takedown: 2.0 points
- Control Time: 1.0 points per minute
- Submission Attempt: 3.0 points

**Bonuses:**
- Win: +10 points
- Finish (KO/TKO/SUB): +15 points
- KO/TKO: +5 points
- Submission: +5 points

---

### 2. fantasy.advanced
**Target:** Advanced fantasy leagues with AI metrics

**Weights:**
- Significant Strike: 0.6 points
- Knockdown: 6.0 points
- Takedown: 2.5 points
- Control Time: 1.5 points per minute
- Submission Attempt: 4.0 points
- AI Damage Multiplier: 0.1x
- AI Control Multiplier: 0.05x

**Bonuses:**
- Win: +15 points
- Finish: +20 points
- KO/TKO: +8 points
- Submission: +8 points
- Dominant Round: +3 points (damage > 15.0 or control > 180s)

---

### 3. sportsbook.pro
**Target:** Sportsbook market settlement

**Weights:**
- Significant Strike: 0.8 points
- Knockdown: 10.0 points
- Takedown: 3.0 points
- Control Time: 2.0 points per minute
- Submission Attempt: 5.0 points
- Strike Accuracy Multiplier: 0.02x
- Defense Multiplier: 0.01x

**Bonuses:**
- Win: +25 points
- Finish: +35 points
- KO/TKO: +15 points
- Submission: +15 points
- Dominant Round: +5 points
- Clean Sweep (3+ rounds): +10 points

**Penalties:**
- Point Deduction: -5 points
- Foul: -3 points

---

## 🔌 API Endpoints

### Get All Profiles
```bash
GET /v1/fantasy/profiles
```

**Response:**
```json
[
  {
    "id": "fantasy.basic",
    "name": "Fantasy Basic",
    "config": {...},
    "created_at": "2025-12-02T..."
  }
]
```

---

### Get Specific Profile
```bash
GET /v1/fantasy/profiles/fantasy.basic
```

---

### Calculate Fantasy Points (Single Fighter)
```bash
POST /v1/fantasy/calculate
Content-Type: application/json

{
  "fight_id": "uuid-here",
  "fighter_id": "uuid-here",
  "profile_id": "fantasy.basic"
}
```

**Response:**
```json
{
  "success": true,
  "fighter_id": "...",
  "fight_id": "...",
  "profile_id": "fantasy.basic",
  "fantasy_points": 45.5,
  "breakdown": {
    "sig_strikes": 20.0,
    "knockdowns": 5.0,
    "control": 2.5,
    "win_bonus": 10.0,
    "finish_bonus": 15.0,
    "ko_bonus": 5.0,
    "raw_stats": {
      "sig_strikes": 40,
      "knockdowns": 1,
      "control_seconds": 150,
      "is_winner": true
    }
  }
}
```

---

### Calculate for Entire Fight (Both Fighters)
```bash
POST /v1/fantasy/calculate/fight/{fight_id}?profile_ids=fantasy.basic&profile_ids=fantasy.advanced
```

Returns array of calculations for both fighters across specified profiles.

---

### Get Fight Fantasy Stats
```bash
GET /v1/fantasy/stats/fight/{fight_id}?profile_id=fantasy.basic
```

Returns saved fantasy stats for all fighters in a fight.

---

### Get Fighter Fantasy Stats
```bash
GET /v1/fantasy/stats/fighter/{fighter_id}?profile_id=fantasy.advanced
```

Returns all fantasy stats for a specific fighter.

---

### Get Fantasy Leaderboard
```bash
GET /v1/fantasy/leaderboard/fantasy.basic?event_code=PFC50&limit=10
```

**Response:**
```json
{
  "profile_id": "fantasy.basic",
  "profile_name": "Fantasy Basic",
  "event_code": "PFC50",
  "leaderboard": [
    {
      "fighter_id": "...",
      "fighter_name": "John Strike",
      "fighter_nickname": "The Blade",
      "fantasy_points": 45.5,
      "fights_count": 1,
      "avg_points_per_fight": 45.5
    }
  ],
  "total_fighters": 6
}
```

---

### Calculate for Entire Event
```bash
POST /v1/fantasy/calculate/event/PFC50?profile_ids=fantasy.basic
```

Batch calculation for all fights in an event.

---

## 🧪 Testing with PFC50 Data

### Step 1: Calculate Fantasy Points for Fight 1

```bash
# Get fight ID first
curl http://localhost:8002/v1/fights/PFC50-F1/live | jq '.fight.code'

# Calculate for red corner (John Strike)
curl -X POST http://localhost:8002/v1/fantasy/calculate \
  -H "Content-Type: application/json" \
  -d '{
    "fight_id": "FIGHT_UUID_HERE",
    "fighter_id": "FIGHTER_UUID_HERE",
    "profile_id": "fantasy.basic"
  }' | jq
```

### Step 2: Calculate for Entire Fight

```bash
curl -X POST "http://localhost:8002/v1/fantasy/calculate/fight/FIGHT_UUID?profile_ids=fantasy.basic&profile_ids=fantasy.advanced&profile_ids=sportsbook.pro" | jq
```

### Step 3: View Leaderboard

```bash
# Event leaderboard
curl "http://localhost:8002/v1/fantasy/leaderboard/fantasy.basic?event_code=PFC50&limit=10" | jq

# Overall leaderboard
curl "http://localhost:8002/v1/fantasy/leaderboard/sportsbook.pro?limit=10" | jq
```

### Step 4: Calculate for Entire Event

```bash
curl -X POST "http://localhost:8002/v1/fantasy/calculate/event/PFC50" | jq
```

This will calculate fantasy points for all 6 fighters across all 3 profiles!

---

## 📈 Expected Results for PFC50-F1

**Fighter:** John "The Blade" Strike (RED)
**Result:** Won by UD in Round 3

**Fantasy Basic (~45-50 points):**
- Sig Strikes: 40 × 0.5 = 20.0
- Knockdowns: 1 × 5.0 = 5.0
- Control: 2.5 min × 1.0 = 2.5
- Win Bonus: 10.0
- Finish Bonus: 15.0 (if by finish)
- **Total: ~45-50 points**

**Fantasy Advanced (~55-65 points):**
- Higher weights + AI multipliers
- Dominant round bonuses
- **Total: ~55-65 points**

**Sportsbook Pro (~70-85 points):**
- Highest weights
- All bonuses active
- **Total: ~70-85 points**

---

## 🔧 Database Schema

### fantasy_scoring_profiles
```sql
CREATE TABLE fantasy_scoring_profiles (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    config JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### fantasy_fight_stats
```sql
CREATE TABLE fantasy_fight_stats (
    id UUID PRIMARY KEY,
    fight_id UUID REFERENCES fights(id),
    fighter_id UUID REFERENCES fighters(id),
    profile_id TEXT REFERENCES fantasy_scoring_profiles(id),
    fantasy_points NUMERIC(10,2),
    breakdown JSONB,
    updated_at TIMESTAMPTZ,
    UNIQUE(fight_id, fighter_id, profile_id)
);
```

---

## 📝 Notes

1. **Calculation Function:** The `calculate_fantasy_points()` SQL function does the heavy lifting
2. **Idempotent:** Recalculating updates existing stats (upsert behavior)
3. **Real-time:** Stats can be recalculated after each round or at fight end
4. **Extensible:** Add custom profiles by inserting into `fantasy_scoring_profiles`

---

## 🚀 Next Steps

1. Run the migration (see RUN_FANTASY_MIGRATION.md)
2. Restart the API server
3. Calculate fantasy points for PFC50
4. View leaderboards
5. Test with your own scoring profiles!
