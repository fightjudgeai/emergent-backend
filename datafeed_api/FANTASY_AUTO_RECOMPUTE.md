# Fantasy Stats Auto-Recomputation System

## 🔄 Overview

The fantasy scoring system **automatically recomputes** fantasy stats whenever fight data changes. This ensures fantasy points are always up-to-date with the latest round states and fight results.

---

## ⚡ Auto-Trigger Events

Fantasy stats are automatically recomputed when:

### 1. Round State Changes
**Trigger:** `auto_recompute_fantasy_on_round_state`

Fires when:
- New round state is inserted
- Round state is updated AND:
  - Round is locked (`round_locked = TRUE`), OR
  - It's the latest state for the fight

**Monitored Columns:**
- `round_locked`
- `red_strikes`, `blue_strikes`
- `red_sig_strikes`, `blue_sig_strikes`
- `red_knockdowns`, `blue_knockdowns`
- `red_control_sec`, `blue_control_sec`

**Example:**
```sql
-- Inserting a new round state automatically triggers recomputation
INSERT INTO round_state (fight_id, round, ts_ms, seq, red_sig_strikes, blue_sig_strikes, ...)
VALUES (...);
-- ✅ Fantasy stats automatically updated for both fighters!

-- Locking a round triggers recomputation
UPDATE round_state SET round_locked = TRUE WHERE fight_id = '...' AND round = 1;
-- ✅ Fantasy stats recalculated with locked state!
```

---

### 2. Fight Result Added/Updated
**Trigger:** `auto_recompute_fantasy_on_result`

Fires when:
- Fight result is inserted
- Fight result is updated

This is critical because fight results affect:
- Win bonuses
- Finish bonuses (KO/TKO/SUB)
- Method-specific bonuses

**Example:**
```sql
-- Adding fight result automatically triggers recomputation
INSERT INTO fight_results (fight_id, winner_side, method, round, time)
VALUES ('...', 'RED', 'KO', 2, '3:15');
-- ✅ Fantasy stats updated with win and KO bonuses!
```

---

## 🧮 Computation Logic

### FantasyAggregator.compute_fantasy_points()

Located in: `/app/datafeed_api/services/fantasy_aggregator.py`

**Function Signature:**
```python
def compute_fantasy_points(
    fight_stats: FightStats,
    scoring_profile: Dict[str, Any]
) -> tuple[float, Dict[str, Any]]:
    """
    Returns: (total_points, breakdown)
    """
```

**Calculation Steps:**

1. **Base Points**
   ```python
   sig_strikes_landed * cfg["sig_strike"]
   + knockdowns * cfg["knockdown"]
   + takedowns_landed * cfg["takedown"]
   + (control_seconds / 60) * cfg["control_minute"]
   + submission_attempts * cfg["submission_attempt"]
   ```

2. **Advanced Multipliers** (fantasy.advanced, sportsbook.pro)
   - AI damage multiplier
   - AI control multiplier
   - Strike accuracy multiplier
   - Defense multiplier

3. **Bonuses**
   - Win bonus (if is_winner)
   - Finish bonus (if KO/TKO/SUB)
   - KO/TKO bonus
   - Submission bonus
   - Dominant round bonus

4. **Penalties** (sportsbook.pro)
   - Point deductions
   - Fouls

---

## 📊 JSON Breakdown Structure

Example breakdown output:

```json
{
  "base_points": {
    "sig_strikes": 20.0,
    "knockdowns": 5.0,
    "takedowns": 0.0,
    "control": 2.5,
    "submission_attempts": 0.0
  },
  "bonuses": {
    "win": 10.0,
    "finish": 15.0,
    "ko": 5.0
  },
  "multipliers": {
    "ai_damage": 1.5,
    "ai_control": 0.8
  },
  "penalties": {},
  "raw_stats": {
    "sig_strikes_landed": 40,
    "knockdowns": 1,
    "takedowns_landed": 0,
    "control_seconds": 150,
    "submission_attempts": 0,
    "total_strikes": 65,
    "is_winner": true,
    "finish_method": "KO",
    "ai_damage": 15.2,
    "ai_win_prob": 0.78,
    "strike_accuracy": 61.5
  },
  "summary": {
    "total_base_points": 27.5,
    "total_bonuses": 30.0,
    "total_multipliers": 2.3,
    "total_penalties": 0.0,
    "grand_total": 59.8
  }
}
```

---

## 🛠️ Manual Recomputation

### Via API Endpoint

**Recompute Specific Fight:**
```bash
curl -X POST "http://localhost:8002/v1/fantasy/recompute?fight_id=FIGHT_UUID" | jq
```

**Recompute Entire Event:**
```bash
curl -X POST "http://localhost:8002/v1/fantasy/recompute?event_code=PFC50" | jq
```

**Recompute All Fights:**
```bash
curl -X POST "http://localhost:8002/v1/fantasy/recompute" | jq
```

### Via SQL Function

**Recompute Specific Fight:**
```sql
SELECT * FROM recompute_all_fantasy_stats(
    p_fight_id := 'uuid-here'
);
```

**Recompute Event:**
```sql
SELECT * FROM recompute_all_fantasy_stats(
    p_event_code := 'PFC50'
);
```

**Recompute All:**
```sql
SELECT * FROM recompute_all_fantasy_stats();
```

**Response:**
```
fight_id | fighter_id | profile_id | fantasy_points | status
---------|------------|------------|----------------|--------
uuid...  | uuid...    | fantasy.basic | 45.50       | success
uuid...  | uuid...    | fantasy.advanced | 52.30    | success
...
```

---

## 🔍 Monitoring Auto-Recomputation

### Check Trigger Status
```sql
SELECT 
    trigger_name,
    event_manipulation,
    action_timing,
    event_object_table
FROM information_schema.triggers
WHERE trigger_name LIKE '%fantasy%';
```

### View Recent Recomputations
```sql
SELECT 
    f.code as fight_code,
    fi.first_name || ' ' || fi.last_name as fighter_name,
    ffs.profile_id,
    ffs.fantasy_points,
    ffs.updated_at
FROM fantasy_fight_stats ffs
JOIN fights f ON ffs.fight_id = f.id
JOIN fighters fi ON ffs.fighter_id = fi.id
ORDER BY ffs.updated_at DESC
LIMIT 20;
```

### Check for Computation Errors
Check server logs for NOTICE messages:
```bash
tail -f /var/log/supervisor/datafeed_api.log | grep "fantasy"
```

---

## 🧪 Testing Auto-Recomputation

### Test 1: Insert New Round State
```sql
-- Before
SELECT fantasy_points FROM fantasy_fight_stats 
WHERE fight_id = (SELECT id FROM fights WHERE code = 'PFC50-F1')
  AND profile_id = 'fantasy.basic';

-- Insert new round with higher stats
INSERT INTO round_state (
    fight_id,
    round,
    ts_ms,
    seq,
    red_sig_strikes,
    blue_sig_strikes,
    red_knockdowns,
    blue_knockdowns,
    red_control_sec,
    blue_control_sec
) VALUES (
    (SELECT id FROM fights WHERE code = 'PFC50-F1'),
    3,
    1737761200000,
    3,
    60,  -- More strikes
    45,
    2,   -- More knockdowns
    0,
    120,
    60
);

-- After (should see updated points)
SELECT fantasy_points FROM fantasy_fight_stats 
WHERE fight_id = (SELECT id FROM fights WHERE code = 'PFC50-F1')
  AND profile_id = 'fantasy.basic';
-- ✅ Points increased!
```

### Test 2: Lock a Round
```sql
-- Lock round 2 for PFC50-F1
UPDATE round_state
SET round_locked = TRUE
WHERE fight_id = (SELECT id FROM fights WHERE code = 'PFC50-F1')
  AND round = 2;

-- Check that fantasy stats were updated
SELECT updated_at FROM fantasy_fight_stats
WHERE fight_id = (SELECT id FROM fights WHERE code = 'PFC50-F1')
ORDER BY updated_at DESC;
-- ✅ Updated timestamp should be very recent!
```

### Test 3: Add Fight Result
```sql
-- Update result to change winner
UPDATE fight_results
SET winner_side = 'BLUE', method = 'SUB'
WHERE fight_id = (SELECT id FROM fights WHERE code = 'PFC50-F1');

-- Check fantasy stats for both fighters
SELECT 
    fi.first_name || ' ' || fi.last_name as fighter,
    ffs.fantasy_points,
    ffs.breakdown->'bonuses'->>'win' as win_bonus,
    ffs.breakdown->'bonuses'->>'submission' as sub_bonus
FROM fantasy_fight_stats ffs
JOIN fighters fi ON ffs.fighter_id = fi.id
WHERE ffs.fight_id = (SELECT id FROM fights WHERE code = 'PFC50-F1')
  AND ffs.profile_id = 'fantasy.basic';
-- ✅ Winner changed, bonuses updated!
```

---

## ⚙️ Configuration

### Disable Auto-Recomputation (if needed)
```sql
ALTER TABLE round_state DISABLE TRIGGER auto_recompute_fantasy_on_round_state;
ALTER TABLE fight_results DISABLE TRIGGER auto_recompute_fantasy_on_result;
```

### Re-enable
```sql
ALTER TABLE round_state ENABLE TRIGGER auto_recompute_fantasy_on_round_state;
ALTER TABLE fight_results ENABLE TRIGGER auto_recompute_fantasy_on_result;
```

---

## 🚨 Error Handling

Triggers use `EXCEPTION WHEN OTHERS` blocks to prevent failures from breaking round_state or fight_results inserts/updates.

**Errors are logged as NOTICE:**
```
NOTICE: Error computing RED fantasy stats for profile fantasy.basic: division by zero
```

**Check for errors:**
```bash
# In PostgreSQL logs
grep "Error computing" /var/log/postgresql/postgresql-*.log

# In application logs
tail -f /var/log/supervisor/datafeed_api.err.log | grep -i "fantasy"
```

---

## 📈 Performance Considerations

- **Async Triggers:** Computation runs after transaction commits
- **Upsert Logic:** Uses `ON CONFLICT DO UPDATE` for efficiency
- **Selective Firing:** Only fires on specific column changes or locked rounds
- **Batch Operations:** Use manual recompute for bulk historical data

**Optimization Tips:**
1. Lock rounds only when finalized (reduces trigger frequency)
2. Use manual recompute for historical data migration
3. Index on `fight_id`, `fighter_id`, `profile_id` already in place

---

## ✅ Summary

**Automatic Recomputation Triggers:**
- ✅ Round state changes (insert/update)
- ✅ Round locks
- ✅ Fight results (insert/update)

**Manual Recomputation:**
- ✅ API endpoint: `/v1/fantasy/recompute`
- ✅ SQL function: `recompute_all_fantasy_stats()`

**Output:**
- ✅ Total fantasy points
- ✅ Detailed JSON breakdown by category
- ✅ Raw stats included for transparency

**Monitoring:**
- ✅ Check trigger status in information_schema
- ✅ View recent updates via fantasy_fight_stats
- ✅ Error logs in NOTICE messages

The system ensures fantasy stats are **always current** without manual intervention!
