# 🎯 Complete Fantasy Scoring System Reference

## Overview
Your system has **3 fantasy scoring profiles**, each with different weights and bonuses optimized for different use cases.

---

## 📊 Profile 1: Fantasy Basic (Casual Leagues)
**Profile ID:** `fantasy.basic`  
**Description:** Simple scoring for casual fantasy leagues

### Base Event Weights

| Event Type | Points per Unit | Notes |
|-----------|-----------------|-------|
| **Significant Strike** | 0.5 | Per strike landed |
| **Knockdown (KD)** | 5.0 | Any knockdown |
| **Takedown** | 2.0 | Successful takedown |
| **Control Time** | 1.0 | Per minute (60 seconds) |
| **Submission Attempt** | 3.0 | Per attempt |

### Bonuses

| Bonus Type | Points | Trigger Condition |
|-----------|--------|-------------------|
| **Win Bonus** | +10.0 | Fighter wins the fight |
| **Finish Bonus** | +15.0 | Fight ends by KO/TKO/Submission |
| **KO Bonus** | +5.0 | Win by KO/TKO |
| **Submission Bonus** | +5.0 | Win by Submission |

### Example Calculation
```
Fighter Stats:
- 45 Significant Strikes = 45 × 0.5 = 22.5 points
- 2 Knockdowns = 2 × 5.0 = 10.0 points
- 3 Takedowns = 3 × 2.0 = 6.0 points
- 180 seconds control = 3 minutes × 1.0 = 3.0 points
- 1 Sub Attempt = 1 × 3.0 = 3.0 points
- Win by Submission = +10.0 (win) + 15.0 (finish) + 5.0 (sub) = +30.0
--------------------------------------------------------------
TOTAL: 74.5 Fantasy Points
```

---

## 📊 Profile 2: Fantasy Advanced (AI-Enhanced Leagues)
**Profile ID:** `fantasy.advanced`  
**Description:** Advanced fantasy scoring with AI-weighted metrics

### Base Event Weights

| Event Type | Points per Unit | % Increase vs Basic | Notes |
|-----------|-----------------|---------------------|-------|
| **Significant Strike** | 0.6 | +20% | Per strike landed |
| **Knockdown (KD)** | 6.0 | +20% | Any knockdown |
| **Takedown** | 2.5 | +25% | Successful takedown |
| **Control Time** | 1.5 | +50% | Per minute (60 seconds) |
| **Submission Attempt** | 4.0 | +33% | Per attempt |

### AI Multipliers (New)

| Multiplier Type | Value | Applied To |
|----------------|-------|-----------|
| **AI Damage Multiplier** | 0.1 | Per AI-detected damage point |
| **AI Control Multiplier** | 0.05 | Per AI-detected control point |

### Bonuses

| Bonus Type | Points | % Increase vs Basic | Trigger Condition |
|-----------|--------|---------------------|-------------------|
| **Win Bonus** | +15.0 | +50% | Fighter wins the fight |
| **Finish Bonus** | +20.0 | +33% | Fight ends by KO/TKO/Submission |
| **KO Bonus** | +8.0 | +60% | Win by KO/TKO |
| **Submission Bonus** | +8.0 | +60% | Win by Submission |
| **Dominant Round Bonus** | +3.0 | NEW | Damage >15 OR Control >180s in a round |

### Thresholds

| Threshold | Value | Purpose |
|----------|-------|---------|
| **Dominant Damage** | 15.0 points | Triggers dominant round bonus |
| **Dominant Control** | 180 seconds | Triggers dominant round bonus |

### Example Calculation
```
Fighter Stats:
- 45 Significant Strikes = 45 × 0.6 = 27.0 points
- 2 Knockdowns = 2 × 6.0 = 12.0 points
- 3 Takedowns = 3 × 2.5 = 7.5 points
- 180 seconds control = 3 minutes × 1.5 = 4.5 points
- 1 Sub Attempt = 1 × 4.0 = 4.0 points
- AI Damage Score: 18 = 18 × 0.1 = 1.8 points
- AI Control Score: 25 = 25 × 0.05 = 1.25 points
- 2 Dominant Rounds = 2 × 3.0 = 6.0 points
- Win by Submission = +15.0 (win) + 20.0 (finish) + 8.0 (sub) = +43.0
--------------------------------------------------------------
TOTAL: 107.05 Fantasy Points
```

---

## 📊 Profile 3: Sportsbook Pro (Professional Markets)
**Profile ID:** `sportsbook.pro`  
**Description:** Sportsbook-grade scoring for market settlement

### Base Event Weights

| Event Type | Points per Unit | % Increase vs Basic | Notes |
|-----------|-----------------|---------------------|-------|
| **Significant Strike** | 0.8 | +60% | Per strike landed |
| **Knockdown (KD)** | 10.0 | +100% | Any knockdown |
| **Takedown** | 3.0 | +50% | Successful takedown |
| **Control Time** | 2.0 | +100% | Per minute (60 seconds) |
| **Submission Attempt** | 5.0 | +67% | Per attempt |

### Advanced Multipliers

| Multiplier Type | Value | Applied To |
|----------------|-------|-----------|
| **Strike Accuracy Multiplier** | 0.02 | Per percentage point of accuracy |
| **Defense Multiplier** | 0.01 | Per defensive action |

### Bonuses

| Bonus Type | Points | % Increase vs Basic | Trigger Condition |
|-----------|--------|---------------------|-------------------|
| **Win Bonus** | +25.0 | +150% | Fighter wins the fight |
| **Finish Bonus** | +35.0 | +133% | Fight ends by KO/TKO/Submission |
| **KO Bonus** | +15.0 | +200% | Win by KO/TKO |
| **Submission Bonus** | +15.0 | +200% | Win by Submission |
| **Dominant Round Bonus** | +5.0 | NEW | Damage >20 OR Control >240s |
| **Clean Sweep Bonus** | +10.0 | NEW | Win all 3+ rounds decisively |

### Penalties

| Penalty Type | Points | Trigger |
|-------------|--------|---------|
| **Point Deduction** | -5.0 | Official point deduction by referee |
| **Foul** | -3.0 | Foul committed |

### Thresholds

| Threshold | Value | Purpose |
|----------|-------|---------|
| **Dominant Damage** | 20.0 points | Higher bar for dominant round |
| **Dominant Control** | 240 seconds | Higher bar for dominant round |
| **Clean Sweep Rounds** | 3 rounds | Minimum rounds for clean sweep |

### Market Settlement Rules

| Rule | Value | Purpose |
|------|-------|---------|
| **Min Rounds for Decision** | 3 | Minimum rounds to settle decision markets |
| **Judge Score Weight** | 0.3 (30%) | Judge scoring influence on settlement |

### Example Calculation
```
Fighter Stats:
- 45 Significant Strikes = 45 × 0.8 = 36.0 points
- Strike Accuracy 60% = 60 × 0.02 = 1.2 points
- 2 Knockdowns = 2 × 10.0 = 20.0 points
- 3 Takedowns = 3 × 3.0 = 9.0 points
- 180 seconds control = 3 minutes × 2.0 = 6.0 points
- 1 Sub Attempt = 1 × 5.0 = 5.0 points
- 15 Defense Actions = 15 × 0.01 = 0.15 points
- 2 Dominant Rounds = 2 × 5.0 = 10.0 points
- 1 Clean Sweep (3 rounds) = +10.0 points
- Win by Submission = +25.0 (win) + 35.0 (finish) + 15.0 (sub) = +75.0
- Penalties: -5.0 (1 point deduction)
--------------------------------------------------------------
TOTAL: 167.35 Fantasy Points
```

---

## 📈 Weight Comparison Table

### Base Events

| Event | Basic | Advanced | Sportsbook Pro | % Diff (Pro vs Basic) |
|-------|-------|----------|----------------|----------------------|
| Sig Strike | 0.5 | 0.6 (+20%) | 0.8 (+60%) | **+60%** |
| Knockdown | 5.0 | 6.0 (+20%) | 10.0 (+100%) | **+100%** |
| Takedown | 2.0 | 2.5 (+25%) | 3.0 (+50%) | **+50%** |
| Control/Min | 1.0 | 1.5 (+50%) | 2.0 (+100%) | **+100%** |
| Sub Attempt | 3.0 | 4.0 (+33%) | 5.0 (+67%) | **+67%** |

### Win Bonuses

| Bonus Type | Basic | Advanced | Sportsbook Pro | % Diff (Pro vs Basic) |
|-----------|-------|----------|----------------|----------------------|
| Win | +10.0 | +15.0 (+50%) | +25.0 (+150%) | **+150%** |
| Finish | +15.0 | +20.0 (+33%) | +35.0 (+133%) | **+133%** |
| KO | +5.0 | +8.0 (+60%) | +15.0 (+200%) | **+200%** |
| Submission | +5.0 | +8.0 (+60%) | +15.0 (+200%) | **+200%** |

---

## 🎮 Profile Recommendations

### Use Fantasy Basic When:
- Running casual office leagues
- New to fantasy MMA
- Want simple, easy-to-understand scoring
- Prefer balanced scoring without heavy bonuses

### Use Fantasy Advanced When:
- Want AI-enhanced metrics
- Running competitive leagues
- Value technical performance
- Need dominant round detection

### Use Sportsbook Pro When:
- Running professional betting markets
- Need high accuracy for settlements
- Want to heavily reward finishes
- Require strict accounting with penalties
- Need judge score integration

---

## 💡 Key Insights

### Scoring Philosophy by Profile

**Basic (Casual):**
- Balanced weights
- Moderate bonuses
- Rewards consistent performance
- Easy to predict

**Advanced (Competitive):**
- Higher weights across the board
- AI multipliers add complexity
- Rewards dominant rounds
- More variance in scoring

**Sportsbook Pro (Professional):**
- Maximum weight on impactful events
- Heavy bonus rewards for finishes
- Penalties for fouls
- Designed for betting market accuracy
- Judge integration for decisions

### Score Range Examples (Typical 3-Round Fight)

| Profile | Losing Fighter | Decision Winner | Finish Winner |
|---------|----------------|-----------------|---------------|
| Basic | 20-40 pts | 50-70 pts | 70-100 pts |
| Advanced | 30-55 pts | 65-95 pts | 95-140 pts |
| Sportsbook Pro | 40-75 pts | 90-130 pts | 140-200 pts |

---

## 📁 Database Schema Reference

### Scoring Profiles Table
```sql
fantasy_scoring_profiles (
    id TEXT PRIMARY KEY,           -- 'fantasy.basic', 'fantasy.advanced', etc.
    name TEXT,                     -- Display name
    config JSONB,                  -- Full configuration as JSON
    created_at TIMESTAMPTZ
)
```

### Fantasy Stats Table
```sql
fantasy_fight_stats (
    id UUID PRIMARY KEY,
    fight_id UUID,                 -- References fights table
    fighter_id UUID,               -- References fighters table
    profile_id TEXT,               -- References fantasy_scoring_profiles
    fantasy_points NUMERIC(10,2),  -- Total calculated points
    breakdown JSONB,               -- Detailed point breakdown
    updated_at TIMESTAMPTZ
)
```

### Database Function
```sql
calculate_fantasy_points(
    p_fight_id UUID,
    p_fighter_id UUID,
    p_profile_id TEXT
) RETURNS TABLE (
    fantasy_points NUMERIC,
    breakdown JSONB
)
```

---

## 🔧 API Access

### Get All Profiles
```bash
GET /api/fantasy/profiles
```

### Calculate Points for a Fighter
```bash
POST /api/fantasy/calculate
{
    "fight_id": "uuid",
    "fighter_id": "uuid",
    "profile_id": "fantasy.basic"
}
```

### Get Fantasy Leaderboard
```bash
GET /api/fantasy/leaderboard/{profile_id}?event_code=UFC300&limit=10
```

---

## 📝 Notes

1. **Control Time** is measured in seconds but scored per minute (divide by 60)
2. **AI Multipliers** (Advanced profile) require AI scoring data to be populated
3. **Penalties** (Sportsbook Pro) require event logging for fouls and deductions
4. **Dominant Round Bonuses** are calculated per round and accumulate
5. **Clean Sweep Bonus** requires winning ALL rounds of a minimum 3-round fight

---

## Version Information
- **Schema Version:** 1.0
- **Migration File:** `002_fantasy_scoring.sql`
- **Last Updated:** December 2024
