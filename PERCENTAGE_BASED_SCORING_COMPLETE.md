# 📊 Complete Percentage-Based Scoring System
## Every Event with Exact Values

**System Location:** `/app/backend/server.py` (Main Judge Scoring App)

---

## Category Weights

| Category | Weight | Percentage of Total Score |
|----------|--------|---------------------------|
| **Striking** | 50.0 | 50% |
| **Grappling** | 40.0 | 40% |
| **Other** | 10.0 | 10% |

---

## 🥊 STRIKING CATEGORY (50% Weight)

### Damage Events

| Event | Tier | Base Value | Percentage | Notes |
|-------|------|-----------|------------|-------|
| **Knockdown (KD)** | Near-Finish | 1.00 | 100% | Most impactful - near stoppage |
| **Knockdown (KD)** | Hard | 0.70 | 70% | Significant damage, clear knockdown |
| **Knockdown (KD)** | Flash | 0.40 | 40% | Brief knockdown, quick recovery |
| **Rocked/Stunned** | - | 0.30 | 30% | Visible damage, wobbled |

---

### Individual Strike Types

| Strike Type | Significant Strike | Non-Significant Strike |
|-------------|-------------------|------------------------|
| **Jab** | **0.10** (10%) | **0.05** (5%) |
| **SS Jab** | **0.10** (10%) | N/A |
| **Cross** | **0.14** (14%) | **0.07** (7%) |
| **SS Cross** | **0.14** (14%) | N/A |
| **Hook** | **0.14** (14%) | **0.07** (7%) |
| **SS Hook** | **0.14** (14%) | N/A |
| **Uppercut** | **0.14** (14%) | **0.07** (7%) |
| **SS Uppercut** | **0.14** (14%) | N/A |
| **Elbow** | **0.14** (14%) | **0.07** (7%) |
| **SS Elbow** | **0.14** (14%) | N/A |
| **Knee** | **0.10** (10%) | **0.05** (5%) |
| **SS Knee** | **0.10** (10%) | N/A |
| **Kick** | **0.14** (14%) | **0.07** (7%) |
| **SS Kick** | **0.14** (14%) | N/A |

**Note:** SS = Significant Strike (the "significant" metadata is true)

---

### Volume Dampening Rule (Striking)

| Parameter | Value | Description |
|-----------|-------|-------------|
| **Non-Sig Strike Threshold** | 20 | After +20 strike advantage |
| **Dampening Factor** | 0.70 | Excess strikes count at 70% |

**Example:**
- Fighter A has 50 non-sig strikes
- Fighter B has 20 non-sig strikes
- Advantage: 30 strikes
- First 20 strikes: full value (20 × 0.07 = 1.40)
- Next 10 strikes (excess): dampened (10 × 0.07 × 0.70 = 0.49)
- Total: 1.89 instead of 2.10

---

## 🤼 GRAPPLING CATEGORY (40% Weight)

### Submission Attempts

| Event | Tier | Base Value | Percentage | Description |
|-------|------|-----------|------------|-------------|
| **Submission Attempt** | Near-Finish | 1.00 | 100% | Almost tapped, fight nearly ended |
| **Submission Attempt** | Deep | 0.60 | 60% | Submission locked in, significant threat |
| **Submission Attempt** | Light | 0.25 | 25% | Attempted but not threatening |

---

### Positional Events

| Event | Value Type | Base Value | Percentage | Notes |
|-------|-----------|-----------|------------|-------|
| **Takedown Landed** | Per Occurrence | **0.25** | **25%** | Successfully taking opponent down |
| **Sweep/Reversal** | Per Occurrence | **0.05** | **5%** | Reversing position |
| **Guard Passing** | Per Occurrence | **0.05** | **5%** | Passing opponent's guard |

---

### Control Time (Time-Based)

| Event | Value per Second | Value per Minute | Percentage/Sec | Notes |
|-------|-----------------|------------------|----------------|-------|
| **Ground Back Control** | **0.012** | **0.72** | **1.2%/sec** | Most dominant position |
| **Ground Top Control** | **0.010** | **0.60** | **1.0%/sec** | Dominant ground position |

**Examples:**
- 30 seconds Back Control = 30 × 0.012 = **0.36 points**
- 60 seconds Back Control = 60 × 0.012 = **0.72 points**
- 120 seconds Back Control = 120 × 0.012 = **1.44 points**
- 30 seconds Top Control = 30 × 0.010 = **0.30 points**
- 60 seconds Top Control = 60 × 0.010 = **0.60 points**

---

## 🎯 OTHER CATEGORY (10% Weight)

### Defensive & Control Events

| Event | Value Type | Base Value | Percentage | Notes |
|-------|-----------|-----------|------------|-------|
| **Takedown Stuffed** | Per Occurrence | **0.04** | **4%** | Successfully defending takedown |
| **Cage Control Time** | Per Second | **0.006** | **0.6%/sec** | Controlling opponent against cage |

**Examples:**
- 45 seconds Cage Control = 45 × 0.006 = **0.27 points**
- 60 seconds Cage Control = 60 × 0.006 = **0.36 points**
- 120 seconds Cage Control = 120 × 0.006 = **0.72 points**
- 1 TD Stuffed = **0.04 points**

---

## 📋 Complete Event List (Alphabetical)

| Event Name | Significant | Non-Significant | Per Second | Tier Options |
|------------|-------------|-----------------|------------|--------------|
| **Cage Control Time** | - | - | 0.006 | - |
| **Cross** | 0.14 | 0.07 | - | - |
| **Elbow** | 0.14 | 0.07 | - | - |
| **Ground Back Control** | - | - | 0.012 | - |
| **Ground Top Control** | - | - | 0.010 | - |
| **Guard Passing** | 0.05 | - | - | - |
| **Hook** | 0.14 | 0.07 | - | - |
| **Jab** | 0.10 | 0.05 | - | - |
| **Kick** | 0.14 | 0.07 | - | - |
| **Knee** | 0.10 | 0.05 | - | - |
| **Knockdown (KD)** | - | - | - | Flash: 0.40, Hard: 0.70, Near-Finish: 1.00 |
| **Rocked/Stunned** | 0.30 | - | - | - |
| **Submission Attempt** | - | - | - | Light: 0.25, Deep: 0.60, Near-Finish: 1.00 |
| **Sweep/Reversal** | 0.05 | - | - | - |
| **Takedown Landed** | 0.25 | - | - | - |
| **Takedown Stuffed** | 0.04 | - | - | - |
| **Uppercut** | 0.14 | 0.07 | - | - |

---

## 🎯 Quick Reference: Most Common Events

### Striking Values (Per Strike)
```
Jab (non-sig):        0.05
Jab (sig):            0.10
Cross (non-sig):      0.07
Cross (sig):          0.14
Hook (non-sig):       0.07
Hook (sig):           0.14
Uppercut (non-sig):   0.07
Uppercut (sig):       0.14
Elbow (non-sig):      0.07
Elbow (sig):          0.14
Knee (non-sig):       0.05
Knee (sig):           0.10
Kick (non-sig):       0.07
Kick (sig):           0.14
```

### Damage Values (Per Event)
```
Rocked:               0.30
KD Flash:             0.40
KD Hard:              0.70
KD Near-Finish:       1.00
```

### Grappling Values (Per Event)
```
Takedown Landed:      0.25
Sweep/Reversal:       0.05
Sub Light:            0.25
Sub Deep:             0.60
Sub Near-Finish:      1.00
```

### Control Values (Per Second)
```
Top Control:          0.010/sec
Back Control:         0.012/sec
Cage Control:         0.006/sec
```

### Defense Values (Per Event)
```
Takedown Stuffed:     0.04
```

---

## 💯 Percentage Breakdown by Category

### Striking Events (50% of Total)
- **Highest Value:** KD Near-Finish = 1.00 (100%)
- **High Value:** KD Hard = 0.70 (70%)
- **Medium-High:** KD Flash = 0.40 (40%)
- **Medium:** Rocked = 0.30 (30%)
- **Power Strikes (Sig):** Cross/Hook/Uppercut/Elbow/Kick = 0.14 (14%)
- **Basic Strikes (Sig):** Jab/Knee = 0.10 (10%)
- **Power Strikes (Non-Sig):** Cross/Hook/Uppercut/Elbow/Kick = 0.07 (7%)
- **Basic Strikes (Non-Sig):** Jab/Knee = 0.05 (5%)

### Grappling Events (40% of Total)
- **Highest Value:** Sub Near-Finish = 1.00 (100%)
- **High Value:** Sub Deep = 0.60 (60%)
- **Medium:** Takedown Landed = 0.25 (25%), Sub Light = 0.25 (25%)
- **Per Second:** Back Control = 0.012/sec (1.2%/sec), Top Control = 0.010/sec (1.0%/sec)
- **Low:** Sweep/Reversal = 0.05 (5%)

### Other Events (10% of Total)
- **Per Second:** Cage Control = 0.006/sec (0.6%/sec)
- **Per Event:** TD Stuffed = 0.04 (4%)

---

## 🧮 Sample Calculation

**Fighter A - Round Performance:**

**Striking:**
- 10 SS Jabs = 10 × 0.10 = 1.00
- 5 SS Crosses = 5 × 0.14 = 0.70
- 3 SS Hooks = 3 × 0.14 = 0.42
- 1 Hard KD = 1 × 0.70 = 0.70
- 15 Non-Sig Jabs = 15 × 0.05 = 0.75
- **Striking Raw Total:** 3.57

**Grappling:**
- 2 Takedowns = 2 × 0.25 = 0.50
- 45 sec Back Control = 45 × 0.012 = 0.54
- 1 Deep Sub = 1 × 0.60 = 0.60
- **Grappling Raw Total:** 1.64

**Other:**
- 30 sec Cage Control = 30 × 0.006 = 0.18
- 1 TD Stuffed = 1 × 0.04 = 0.04
- **Other Raw Total:** 0.22

**Weighted Score:**
```
= (3.57 × 50%) + (1.64 × 40%) + (0.22 × 10%)
= 1.785 + 0.656 + 0.022
= 2.463 points
```

---

## 🎴 10-Point Must Mapping

After calculating weighted scores for both fighters, the differential determines the scorecard:

| Score Differential | Score Card | Requirements |
|-------------------|-----------|--------------|
| ≤ 3.0 | **10-10** (Draw) | Virtually identical |
| 3.0 - 140.0 | **10-9** | Clear winner |
| 140.0 - 200.0 | **10-8** | + Must have 2+ KDs OR 100+ strike diff |
| 250.0+ | **10-7** | + Must have 2+ KDs OR 100+ strike diff |

**Critical:** 10-8 and 10-7 require guardrails (2+ KD advantage OR 100+ total strike differential)

---

## 📁 Implementation Location

**File:** `/app/backend/server.py`  
**Lines:** 22-53 (SCORING_CONFIG dictionary)

```python
SCORING_CONFIG = {
    "categories": {
        "striking": 50.0,
        "grappling": 40.0,
        "other": 10.0
    },
    "base_values": {
        "Cross": {"category": "striking", "sig": 0.14, "non_sig": 0.07},
        "Hook": {"category": "striking", "sig": 0.14, "non_sig": 0.07},
        # ... etc
    }
}
```

---

## 🔑 Key Insights

1. **Significant strikes are worth 2x non-significant** (0.14 vs 0.07 for power strikes)
2. **KD Near-Finish = 100%** = Maximum single-event value
3. **Power strikes (Cross/Hook/Uppercut/Elbow/Kick) worth 40% more than Jab/Knee**
4. **Back Control (0.012/sec) worth 20% more than Top Control (0.010/sec)**
5. **Control time accumulates quickly:** 2.5 min back control = 1.8 points
6. **Volume dampening prevents point-fighting** after +20 strike advantage

---

*This is the active percentage-based scoring system used in the main judge scoring application.*
