# Quick Stats Input - Update Summary

## Changes Made to Operator Panel

**File Modified:** `/app/frontend/src/components/OperatorPanel.jsx`

---

## ✅ New Quick Stats Fields

The Quick Stats Input dialog has been updated with the following fields:

| Field Name | Type | Description | Event Logged |
|-----------|------|-------------|--------------|
| **KD** | Number | Knockdowns | KD (Flash tier) |
| **Rocked** | Number | Rocked/Stunned events | Rocked/Stunned (significant) |
| **Total Strikes (Non-SS)** | Number | Non-significant strikes | Jab (non-significant) |
| **SS Strikes** | Number | Significant strikes | Cross (significant) |
| **Takedowns** | Number | Successful takedowns | Takedown Landed |
| **Sub Attempts** | Number | Submission attempts | Submission Attempt (Light tier) |
| **Control Time (seconds)** | Number | Control time in seconds | Ground Top Control |

---

## 📊 State Changes

### Old State Structure:
```javascript
{
  kd: 0,
  ts: 0,
  issHead: 0,
  issBody: 0,
  issLeg: 0,
  takedown: 0,
  pass: 0,
  reversal: 0,
  cageControl: 0
}
```

### New State Structure:
```javascript
{
  kd: 0,
  rocked: 0,
  totalStrikes: 0,
  ssStrikes: 0,
  takedowns: 0,
  subAttempts: 0,
  controlTime: 0
}
```

---

## 🎯 Event Mapping

### What Gets Logged:

1. **KD (n)** → Logs n × "KD" events with tier="Flash"
2. **Rocked (n)** → Logs n × "Rocked/Stunned" events with significant=true
3. **Total Strikes (n)** → Logs n × "Jab" events with significant=false
4. **SS Strikes (n)** → Logs n × "Cross" events with significant=true
5. **Takedowns (n)** → Logs n × "Takedown Landed" events
6. **Sub Attempts (n)** → Logs n × "Submission Attempt" events with tier="Light"
7. **Control Time (seconds)** → Logs 1 × "Ground Top Control" event with duration

All events are tagged with `source: 'quick-input'` for tracking.

---

## 🎨 UI Layout

The dialog now displays fields in a **2-column grid** layout:

```
┌─────────────────────────────────────────┐
│  Quick Stats Input                      │
├─────────────────────────────────────────┤
│  [Fighter Selection Dropdown]           │
├─────────────────────────────────────────┤
│  ⚡ Quick Stats                          │
│  ┌──────────────┬──────────────┐        │
│  │ KD           │ Rocked       │        │
│  ├──────────────┼──────────────┤        │
│  │ Total Strikes│ SS Strikes   │        │
│  ├──────────────┼──────────────┤        │
│  │ Takedowns    │ Sub Attempts │        │
│  ├──────────────┴──────────────┤        │
│  │ Control Time (seconds)      │        │
│  │ (spans full width)          │        │
│  └─────────────────────────────┘        │
│  [Cancel] [Log All Stats (n events)]    │
└─────────────────────────────────────────┘
```

---

## 🔄 Removed Fields

The following fields were removed from the old version:
- ~~ISS Head~~
- ~~ISS Body~~
- ~~ISS Leg~~
- ~~Passes~~
- ~~Reversals~~
- ~~TS (Total Strikes as separate)~~
- ~~Cage Control~~ (replaced with generic "Control Time")

---

## 💡 Usage Example

**Scenario:** Quick input for a busy round

Fighter A had:
- 2 Knockdowns
- 1 Rocked event
- 30 Non-significant strikes
- 15 Significant strikes
- 3 Takedowns
- 1 Submission attempt
- 90 seconds of control time

**Input:**
```
KD: 2
Rocked: 1
Total Strikes: 30
SS Strikes: 15
Takedowns: 3
Sub Attempts: 1
Control Time: 90
```

**Result:**
- Logs 52 individual events (2 KD + 1 Rocked + 30 Strikes + 15 SS + 3 TD + 1 Sub)
- Logs 1 control time event with 90 second duration
- Toast notification: "Logged 52 events + 90s control time for [Fighter Name]"

---

## 🎯 Benefits

1. **Simplified Input:** Consolidated from 9 fields to 7 fields
2. **Clearer Categories:** Removed body part breakdown for strikes
3. **Generic Control:** Control time now applies to any control type (not just cage)
4. **Aligned with Scoring:** Matches percentage-based scoring model better
5. **Faster Data Entry:** Reduced cognitive load for operators

---

## 🧪 Testing Checklist

- [ ] Dialog opens correctly
- [ ] All 7 input fields accept numeric input
- [ ] Fighter selection works (Red/Blue)
- [ ] Event counter updates correctly in button
- [ ] Events log successfully for both fighters
- [ ] Toast notification shows correct counts
- [ ] Dialog resets after submission
- [ ] Dialog closes properly

---

## 📝 Notes

- Default event types chosen for bulk logging:
  - **KD:** Flash (safest assumption for quick input)
  - **Sub Attempt:** Light (safest assumption)
  - **Total Strikes:** Jab (most common non-significant)
  - **SS Strikes:** Cross (most common significant power strike)
  - **Control:** Ground Top Control (most common position)

- Operators can still use individual event buttons for specific strike types or higher-tier KDs/subs

---

*Updated: December 2024*
