# 🥊 Complete Judge Scoring System Reference (Non-Fantasy)

## Overview
Your system has **2 primary judge scoring engines** that use the **10-Point Must System** with weighted categories and damage primacy rules. These are used for actual fight judging, not fantasy leagues.

---

## 🎯 System 1: FightJudge AI Weighted Scoring Engine
**Location:** `/app/backend/fjai/scoring_engine.py`  
**Purpose:** Production judge scoring combining manual + CV events

### Category Weights (Standard UFC Judging Criteria)

| Category | Weight | Percentage | Priority |
|---------|--------|------------|----------|
| **Damage** | 0.50 | **50%** | 🔴 Highest |
| **Control** | 0.25 | **25%** | 🟡 Medium |
| **Aggression** | 0.15 | **15%** | 🟢 Lower |
| **Defense** | 0.10 | **10%** | 🟢 Lower |

### Event Base Values

#### 💥 Knockdowns (Damage Category)
| Event | Base Points | Severity Multiplier | Typical Range |
|-------|-------------|---------------------|---------------|
| **KD - Flash** | 15.0 | 0.5 - 1.0 | 7.5 - 15.0 |
| **KD - Hard** | 25.0 | 0.5 - 1.0 | 12.5 - 25.0 |
| **KD - Near-Finish** | 35.0 | 0.5 - 1.0 | 17.5 - 35.0 |

#### 🥊 Damage Events
| Event | Base Points | Category | Notes |
|-------|-------------|----------|-------|
| **Rocked/Stunned** | 12.0 | Damage | Fighter visibly hurt |
| **High Impact Strike** | 5.0 | Damage | Clean, powerful strike |
| **Significant Strike** | 2.0 | Damage (50%) + Aggression (50%) | Split contribution |

#### 🤼 Grappling Events (Control Category)
| Event | Base Points | Category | Notes |
|-------|-------------|----------|-------|
| **Takedown Landed** | 4.0 | Control | Successful TD |
| **Takedown Attempt** | 0.5 | (Opponent Defense) | Failed TD |
| **Submission Attempt** | 6.0 | Control | Any sub attempt |

#### ⏱️ Control Time (Control Category)
| Event | Points per Second | Category | Calculation |
|-------|------------------|----------|-------------|
| **Control Time** | 0.3 pts/sec | Control | Duration × 0.3 |

**Example:** 60 seconds control = 60 × 0.3 = **18.0 points**

#### 📈 Momentum Events
| Event | Base Points | Category | Notes |
|-------|-------------|----------|-------|
| **Momentum Swing** | 8.0 | Aggression | Shift in fight dynamics |

---

### 🧮 Score Calculation Formula

```
Raw Score = (Damage × 0.50) + (Control × 0.25) + (Aggression × 0.15) + (Defense × 0.10)
```

**Example Round Calculation:**

```
Fighter A Events:
- 1 Hard KD = 25.0 × 0.5 severity = 12.5 damage
- 20 Sig Strikes = 20 × 2.0 = 40.0 (split: 20 damage, 20 aggression)
- 1 Takedown = 4.0 control
- 30s Control = 30 × 0.3 = 9.0 control

Category Totals:
- Damage: 12.5 + 20 = 32.5
- Control: 4.0 + 9.0 = 13.0
- Aggression: 20.0
- Defense: 0.0

Weighted Score:
= (32.5 × 0.50) + (13.0 × 0.25) + (20.0 × 0.15) + (0.0 × 0.10)
= 16.25 + 3.25 + 3.0 + 0.0
= 22.5 points
```

---

### 🚨 Damage Primacy Rule

**Trigger:** When one fighter has significantly more damage than the opponent (>30% of total damage)

**Effect:** Damage overrides other categories - the fighter with damage advantage wins the round regardless of control/aggression

```python
damage_ratio = max(damage_a, damage_b) / total_damage

if damage_ratio >= 0.80:  # One fighter has 80%+ of damage
    # Damage primacy applied
    winner_score += 20.0 bonus
```

**Example:**
- Fighter A: 40 damage points, 10 control, 5 aggression
- Fighter B: 5 damage points, 25 control, 20 aggression

Without damage primacy: Fighter B might win on points  
**With damage primacy:** Fighter A wins (80% of total damage)

---

### 🎴 10-Point Must System Mapping

The raw scores are mapped to standard 10-point must scorecards:

| Score Difference | Scorecard | Winner | Description |
|-----------------|-----------|--------|-------------|
| < 3.0 points | **10-10** | Draw | Extremely close round |
| 3.0 - 14.9 points | **10-9** | Winner | Clear winner |
| 15.0 - 29.9 points | **10-8** | Winner | Dominant round |
| 30.0+ points | **10-7** | Winner | Complete domination |

**Examples:**
```
Fighter A: 22.5 pts | Fighter B: 18.0 pts | Diff: 4.5 → 10-9 to Fighter A
Fighter A: 35.0 pts | Fighter B: 18.0 pts | Diff: 17.0 → 10-8 to Fighter A
Fighter A: 48.0 pts | Fighter B: 12.0 pts | Diff: 36.0 → 10-7 to Fighter A
```

---

## 🎯 System 2: ICVSS Hybrid Scoring Engine
**Location:** `/app/backend/icvss/scoring_engine.py`  
**Purpose:** Computer Vision + Judge hybrid scoring with AI confidence

### Category Weights

| Category | Weight | Percentage | Notes |
|---------|--------|------------|-------|
| **Striking** | 0.50 | **50%** | Includes all strikes + damage |
| **Grappling** | 0.40 | **40%** | TDs, subs, positional control |
| **Control** | 0.10 | **10%** | Time-based control |

### Detailed Event Values

#### 🥊 Strikes (Striking Category)
| Event | Base Value | Notes |
|-------|-----------|-------|
| **Jab** | 1.0 | Basic strike |
| **Cross** | 2.0 | Power strike |
| **Hook** | 2.5 | Power strike |
| **Uppercut** | 2.5 | Power strike |
| **Elbow** | 3.0 | High impact |
| **Knee** | 4.0 | High impact |

#### 🦵 Kicks (Striking Category)
| Event | Base Value | Target |
|-------|-----------|--------|
| **Head Kick** | 5.0 | Head |
| **Body Kick** | 3.0 | Body/Torso |
| **Low Kick** | 1.5 | Legs |
| **Front Kick** | 2.0 | Push/Range |

#### 💥 Damage (Striking Category)
| Event | Base Value | Multiplier Effect |
|-------|-----------|-------------------|
| **Rocked/Stunned** | 20.0 | Visible hurt |
| **KD - Flash** | 30.0 | Quick KD |
| **KD - Hard** | 50.0 | Significant KD |
| **KD - Near-Finish** | 80.0 | Almost finished |

#### 🤼 Grappling (Grappling Category)
| Event | Base Value | Notes |
|-------|-----------|-------|
| **TD Landed** | 15.0 | Successful takedown |
| **TD Stuffed** | 5.0 | Defensive success |
| **Sub - Light** | 10.0 | Basic attempt |
| **Sub - Deep** | 25.0 | Dangerous position |
| **Sub - Near-Finish** | 60.0 | Almost finished |
| **Sweep/Reversal** | 8.0 | Position reversal |

#### ⏱️ Control (Control Category)
| Event | Points/Second | Position |
|-------|--------------|----------|
| **Top Control** | 0.5 | On top in guard/half-guard |
| **Back Control** | 0.7 | Back mount (higher value) |
| **Cage Control** | 0.3 | Against cage |

---

### 🔄 Hybrid Fusion System

ICVSS uses a weighted combination of CV-detected events and judge manual entries:

| Source | Default Weight | Contribution |
|--------|---------------|--------------|
| **CV System** | 0.70 | 70% |
| **Judge Manual** | 0.30 | 30% |

**Formula:**
```
Final Score = (CV_Score × 0.70) + (Judge_Score × 0.30)
```

### CV Confidence Multiplier

Each CV-detected event includes confidence and severity multipliers:

```
Actual Points = Base_Value × Severity × Confidence
```

**Example:**
- Head Kick (base: 5.0)
- Severity: 0.8 (pretty hard)
- Confidence: 0.92 (92% sure)
- **Actual Points:** 5.0 × 0.8 × 0.92 = **3.68 points**

---

### 🎴 ICVSS 10-Point Must Mapping

| Score Difference | Scorecard | Description |
|-----------------|-----------|-------------|
| ≤ 3.0 points | **10-10** | Even round |
| < 100.0 points | **10-9** | Standard win |
| < 200.0 points | **10-8** | Dominant (with near-finish) |
| ≥ 200.0 points | **10-7** | Complete domination |

---

## 📊 Comparison: System 1 vs System 2

| Feature | FightJudge AI | ICVSS Hybrid |
|---------|--------------|--------------|
| **Category Count** | 4 (Damage, Control, Aggression, Defense) | 3 (Striking, Grappling, Control) |
| **Damage Priority** | 50% | 50% (as Striking) |
| **Control Weight** | 25% | 10% |
| **CV Integration** | Optional | Primary (70% weight) |
| **Confidence Adjustment** | Yes | Yes (CV events only) |
| **Damage Primacy** | Yes (30% threshold) | Yes (>30pt diff) |
| **10-8 Threshold** | 15-30pt diff | Near-finish events + large diff |
| **Use Case** | Judge scoring | Hybrid AI+Judge |

---

## 🎯 Practical Scoring Examples

### Example 1: Striking-Heavy Round

**Fighter A Events:**
- 30 Significant Strikes = 30 × 2.0 = 60.0 striking
- 1 Rocked = 20.0 striking
- 0 Grappling
- 15s Control = 15 × 0.5 = 7.5 control

**Fighter B Events:**
- 15 Significant Strikes = 30.0 striking
- 0 Damage events
- 2 TDs = 30.0 grappling
- 45s Control = 22.5 control

**ICVSS Scoring:**
```
Fighter A:
- Striking: 80.0 × 0.50 = 40.0
- Grappling: 0.0 × 0.40 = 0.0
- Control: 7.5 × 0.10 = 0.75
- Total: 40.75

Fighter B:
- Striking: 30.0 × 0.50 = 15.0
- Grappling: 30.0 × 0.40 = 12.0
- Control: 22.5 × 0.10 = 2.25
- Total: 29.25

Difference: 11.5 points → 10-9 to Fighter A
```

---

### Example 2: Knockdown Triggers Damage Primacy

**Fighter A:**
- 1 Hard KD = 25.0 damage
- 10 Sig Strikes = 20.0 (10 damage, 10 aggression)
- Total Damage: 35.0

**Fighter B:**
- 0 KDs
- 5 Sig Strikes = 10.0 (5 damage, 5 aggression)
- 3 TDs = 12.0 control
- 60s Control = 18.0 control
- Total Damage: 5.0

**FightJudge AI Scoring:**
```
Total Damage: 35.0 + 5.0 = 40.0
Fighter A damage ratio: 35.0 / 40.0 = 87.5%

Damage Primacy Triggered! (>80%)
Fighter A automatically wins with +20.0 bonus

Result: 10-9 to Fighter A (could be 10-8 with near-finish KD)
```

---

### Example 3: 10-8 Round

**Fighter A:**
- 2 Hard KDs = 50.0 damage
- 1 Near-Finish Sub = 60.0 grappling
- 40 Sig Strikes = 80.0 (40 damage, 40 aggression)
- Total weighted: ~100+ points

**Fighter B:**
- 8 Sig Strikes = 16.0 (8 damage, 8 aggression)
- 1 TD Stuffed = 5.0 defense
- Total weighted: ~15 points

**Difference:** 85+ points → **10-8 to Fighter A**

---

## 🔧 Configuration & Tuning

### Adjustable Weights

Both systems allow weight customization:

**FightJudge AI:**
```python
from fjai.models import ScoringWeights

custom_weights = ScoringWeights(
    damage=0.55,      # Increase damage importance
    control=0.20,     # Decrease control
    aggression=0.15,
    defense=0.10,
    damage_primacy_threshold=0.25  # Lower threshold
)
```

**ICVSS Hybrid:**
```python
engine = HybridScoringEngine(
    cv_weight=0.80,     # Trust CV more
    judge_weight=0.20   # Trust judge less
)
```

---

## 📁 Database Schema

### Round State Table
```sql
round_state (
    id UUID PRIMARY KEY,
    fight_id UUID,
    round INT,
    seq BIGINT,  -- Monotonic sequence
    
    -- Red Corner
    red_strikes INT DEFAULT 0,
    red_sig_strikes INT DEFAULT 0,
    red_knockdowns INT DEFAULT 0,
    red_control_sec INT DEFAULT 0,
    red_ai_damage NUMERIC(5,2),
    red_ai_win_prob NUMERIC(4,3),
    
    -- Blue Corner
    blue_strikes INT DEFAULT 0,
    blue_sig_strikes INT DEFAULT 0,
    blue_knockdowns INT DEFAULT 0,
    blue_control_sec INT DEFAULT 0,
    blue_ai_damage NUMERIC(5,2),
    blue_ai_win_prob NUMERIC(4,3),
    
    -- Lock state
    round_locked BOOLEAN DEFAULT FALSE
)
```

---

## 🎮 Scoring Summary Table

### Quick Reference: Point Values

| Event | FightJudge AI | ICVSS | Category |
|-------|--------------|-------|----------|
| **Flash KD** | 15.0 | 30.0 | Damage/Striking |
| **Hard KD** | 25.0 | 50.0 | Damage/Striking |
| **Near-Finish KD** | 35.0 | 80.0 | Damage/Striking |
| **Sig Strike** | 2.0 | 2.0 | Damage+Aggression/Striking |
| **TD Landed** | 4.0 | 15.0 | Control/Grappling |
| **Sub Attempt** | 6.0 | 10-60 (tier) | Control/Grappling |
| **Control/sec** | 0.3 | 0.3-0.7 | Control |
| **Rocked** | 12.0 | 20.0 | Damage/Striking |

---

## 💡 Key Takeaways

1. **Damage is King** - Both systems prioritize damage (50% weight)
2. **Knockdowns are Game-Changers** - Can trigger 10-8s and damage primacy
3. **Control Matters Less** - Only 10-25% of total score
4. **10-8 Threshold** - Typically requires 15+ point difference OR near-finish events
5. **Damage Primacy** - Can override other categories when one fighter dominates damage
6. **CV Confidence** - ICVSS adjusts scores based on detection confidence

---

## 📝 Files Reference

**Scoring Engines:**
- `/app/backend/fjai/scoring_engine.py` - FightJudge AI
- `/app/backend/icvss/scoring_engine.py` - ICVSS Hybrid

**Models:**
- `/app/backend/fjai/models.py` - Scoring weights, event types
- `/app/backend/icvss/models.py` - CV event types

**Database:**
- `/app/datafeed_api/migrations/001_initial_schema.sql` - Round state schema

---

## Version Information
- **FightJudge AI Version:** 1.0
- **ICVSS Version:** 2.0
- **Last Updated:** December 2024
- **Scoring Standard:** Unified Rules of MMA + 10-Point Must System
