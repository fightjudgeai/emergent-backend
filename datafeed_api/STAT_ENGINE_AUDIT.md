# Stat Engine Audit & Normalization Plan

## 🎯 Objective

Refine the existing FightJudge.ai stat engine for:
- **UFCstats parity** - Controlled vocabulary alignment
- **Sportsbook-grade determinism** - Provable, auditable stat calculation

---

## 📊 Current System Analysis

### Existing Schema
**Table:** `round_state`
- Stores **cumulative stats** per round
- Fields: `red_strikes`, `red_sig_strikes`, `red_knockdowns`, `red_control_sec`, etc.
- **Issue:** No granular event tracking, no audit trail

**Current Approach:**
- Stats are inserted/updated as aggregate numbers
- Control time is a single integer (seconds)
- No event stream or deterministic calculation

---

## 🔧 Required Changes

### 1. Event Type Normalization

**Create Controlled Vocabulary:**
```
STR_ATT         - Strike attempt
STR_LAND        - Strike landed (sig or total)
KD              - Knockdown
TD_ATT          - Takedown attempt
TD_LAND         - Takedown landed
CTRL_START      - Control period begins
CTRL_END        - Control period ends
SUB_ATT         - Submission attempt
REVERSAL        - Position reversal
ROUND_START     - Round begins
ROUND_END       - Round ends
FIGHT_END       - Fight ends
```

**Legacy Alias Mapping:**
```
"strike" → STR_LAND
"takedown" → TD_LAND
"submission" → SUB_ATT
"knockdown" → KD
"control_start" → CTRL_START
"control_end" → CTRL_END
```

### 2. Deterministic Control Time

**Algorithm:**
```
For each fighter + round:
  control_seconds = 0
  
  FOR each CTRL_START event:
    Find matching CTRL_END event (next chronologically)
    
    IF CTRL_END found:
      duration = CTRL_END.second_in_round - CTRL_START.second_in_round
      control_seconds += duration
    ELSE:
      // Control continues to round end
      duration = round_duration - CTRL_START.second_in_round
      control_seconds += duration
  
  ASSERT: No overlapping control periods
  ASSERT: Red control + Blue control ≤ round_duration
```

---

## 🗄️ Proposed Schema Changes

### New Table: `fight_events`

```sql
CREATE TABLE fight_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    fight_id UUID NOT NULL REFERENCES fights(id),
    round INT NOT NULL,
    second_in_round INT NOT NULL,
    event_type TEXT NOT NULL CHECK (event_type IN (
        'STR_ATT', 'STR_LAND', 'KD', 'TD_ATT', 'TD_LAND',
        'CTRL_START', 'CTRL_END', 'SUB_ATT', 'REVERSAL',
        'ROUND_START', 'ROUND_END', 'FIGHT_END'
    )),
    corner TEXT NOT NULL CHECK (corner IN ('RED', 'BLUE')),
    metadata JSONB DEFAULT '{}',
    seq BIGINT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT unique_event_seq UNIQUE (fight_id, seq),
    CONSTRAINT ordered_events CHECK (second_in_round >= 0)
);

CREATE INDEX idx_fight_events_fight_round ON fight_events(fight_id, round);
CREATE INDEX idx_fight_events_type ON fight_events(event_type);
CREATE INDEX idx_fight_events_seq ON fight_events(fight_id, seq);
```

**Metadata Examples:**
```json
// STR_LAND
{
  "is_significant": true,
  "target": "head",
  "technique": "punch"
}

// CTRL_START
{
  "position": "mount",
  "transitioned_from": "half_guard"
}

// TD_LAND
{
  "technique": "double_leg",
  "slam": false
}
```

---

## 🔄 Migration Strategy

### Phase 1: Add Event Tracking (Parallel System)
1. Create `fight_events` table
2. Keep existing `round_state` table
3. Populate events alongside cumulative stats
4. Validate event-based calculations match cumulative

### Phase 2: Event Normalization
1. Implement event type validator
2. Add legacy alias mapper
3. Reject non-standard event types

### Phase 3: Deterministic Control Time
1. Implement paired CTRL_START/CTRL_END validator
2. Add control time calculator from events
3. Audit existing control times
4. Flag discrepancies

### Phase 4: Full Cutover
1. Make `fight_events` primary source of truth
2. Deprecate direct `round_state` updates
3. Generate `round_state` from events via trigger/function

---

## 📐 Control Time Validation Rules

### Rule 1: Pairing
```
For each CTRL_START:
  MUST have matching CTRL_END (or round end)
  
For each CTRL_END:
  MUST have matching CTRL_START
```

### Rule 2: Non-Overlapping
```
Fighter A control periods MUST NOT overlap
Fighter B control periods MUST NOT overlap
Fighter A and Fighter B MAY NOT control simultaneously
```

### Rule 3: Conservation
```
SUM(red_control) + SUM(blue_control) ≤ round_duration

Exception: Small buffer (±2 seconds) for simultaneous position changes
```

### Rule 4: Monotonicity
```
Events within a round MUST be ordered by second_in_round
CTRL_END.second_in_round > CTRL_START.second_in_round
```

---

## 🧮 Calculation Functions

### Calculate Control Time
```sql
CREATE FUNCTION calculate_control_time(
    p_fight_id UUID,
    p_round INT,
    p_corner TEXT
)
RETURNS INT AS $$
DECLARE
    v_total_control INT := 0;
    v_ctrl_start RECORD;
    v_ctrl_end RECORD;
    v_duration INT;
BEGIN
    -- Get all CTRL_START events for this fighter/round
    FOR v_ctrl_start IN
        SELECT * FROM fight_events
        WHERE fight_id = p_fight_id
          AND round = p_round
          AND corner = p_corner
          AND event_type = 'CTRL_START'
        ORDER BY second_in_round
    LOOP
        -- Find matching CTRL_END
        SELECT * INTO v_ctrl_end
        FROM fight_events
        WHERE fight_id = p_fight_id
          AND round = p_round
          AND corner = p_corner
          AND event_type = 'CTRL_END'
          AND second_in_round > v_ctrl_start.second_in_round
        ORDER BY second_in_round
        LIMIT 1;
        
        IF FOUND THEN
            v_duration := v_ctrl_end.second_in_round - v_ctrl_start.second_in_round;
            v_total_control := v_total_control + v_duration;
        ELSE
            -- Control continues to round end (assume 300 seconds = 5 min)
            v_duration := 300 - v_ctrl_start.second_in_round;
            v_total_control := v_total_control + v_duration;
        END IF;
    END LOOP;
    
    RETURN v_total_control;
END;
$$ LANGUAGE plpgsql;
```

### Aggregate Stats from Events
```sql
CREATE FUNCTION aggregate_round_stats(
    p_fight_id UUID,
    p_round INT
)
RETURNS TABLE (
    red_strikes INT,
    red_sig_strikes INT,
    red_knockdowns INT,
    red_control_sec INT,
    blue_strikes INT,
    blue_sig_strikes INT,
    blue_knockdowns INT,
    blue_control_sec INT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COUNT(*) FILTER (WHERE corner = 'RED' AND event_type = 'STR_LAND')::INT,
        COUNT(*) FILTER (WHERE corner = 'RED' AND event_type = 'STR_LAND' AND (metadata->>'is_significant')::boolean = true)::INT,
        COUNT(*) FILTER (WHERE corner = 'RED' AND event_type = 'KD')::INT,
        calculate_control_time(p_fight_id, p_round, 'RED'),
        COUNT(*) FILTER (WHERE corner = 'BLUE' AND event_type = 'STR_LAND')::INT,
        COUNT(*) FILTER (WHERE corner = 'BLUE' AND event_type = 'STR_LAND' AND (metadata->>'is_significant')::boolean = true)::INT,
        COUNT(*) FILTER (WHERE corner = 'BLUE' AND event_type = 'KD')::INT,
        calculate_control_time(p_fight_id, p_round, 'BLUE')
    FROM fight_events
    WHERE fight_id = p_fight_id
      AND round = p_round;
END;
$$ LANGUAGE plpgsql;
```

---

## ✅ Validation & Testing

### Test Cases

**Test 1: Basic Control Time**
```sql
-- Insert paired events
INSERT INTO fight_events (fight_id, round, second_in_round, event_type, corner, seq)
VALUES
    ('...', 1, 30, 'CTRL_START', 'RED', 1),
    ('...', 1, 90, 'CTRL_END', 'RED', 2);

-- Calculate
SELECT calculate_control_time('...', 1, 'RED');
-- Expected: 60 seconds
```

**Test 2: Overlapping Control (Should Fail)**
```sql
-- RED controls 30-90
-- BLUE controls 60-120
-- Overlap: 60-90 (30 seconds)
-- Should be rejected or flagged
```

**Test 3: Control to Round End**
```sql
-- CTRL_START at 250 seconds
-- No CTRL_END
-- Expected: 50 seconds (300 - 250)
```

**Test 4: Event Type Normalization**
```sql
-- Legacy input: "strike"
-- Normalized: "STR_LAND"

-- Legacy input: "submission_attempt"
-- Normalized: "SUB_ATT"
```

---

## 🚀 Implementation Plan

### Step 1: Schema Migration
- [ ] Create `fight_events` table
- [ ] Add event type enum/check constraint
- [ ] Create indexes for performance

### Step 2: Event Ingestion
- [ ] Create event insertion API
- [ ] Implement event type validator with alias mapping
- [ ] Add event sequencing

### Step 3: Control Time Calculator
- [ ] Implement `calculate_control_time()` function
- [ ] Add pairing validation
- [ ] Add overlap detection

### Step 4: Stat Aggregation
- [ ] Implement `aggregate_round_stats()` function
- [ ] Add triggers to auto-update `round_state` from events
- [ ] Validate against existing data

### Step 5: Audit & Migration
- [ ] Audit existing `round_state` data
- [ ] Generate events from existing cumulative stats (best effort)
- [ ] Flag data quality issues

### Step 6: API Updates
- [ ] Add event stream API endpoints
- [ ] Update WebSocket to broadcast events
- [ ] Maintain backward compatibility with `round_state` API

---

## 📊 Benefits

**UFCstats Parity:**
- ✅ Standardized event vocabulary
- ✅ Granular event tracking
- ✅ Audit trail for every stat

**Sportsbook-Grade Determinism:**
- ✅ Provable control time calculation
- ✅ No overlapping control periods
- ✅ Validation rules enforced
- ✅ Immutable event log

**Developer Experience:**
- ✅ Clear API contracts
- ✅ Self-documenting events
- ✅ Easy to add new stat types

---

## ⚠️ Considerations

1. **Backward Compatibility:** Maintain `round_state` API during transition
2. **Performance:** Event table will grow quickly - need partitioning/archiving
3. **Data Quality:** Existing data may not be recoverable to event granularity
4. **Operator Interface:** Need UI to input events (vs. cumulative stats)

---

## 📝 Next Steps

**For Discussion:**
1. Approve schema design?
2. Parallel migration or full cutover?
3. Operator interface requirements?
4. Historical data migration strategy?

**Implementation Priority:**
1. **P0:** Create event table and ingestion API
2. **P0:** Implement control time calculator
3. **P1:** Add event stream to WebSocket
4. **P2:** Migrate historical data
5. **P3:** Deprecate direct `round_state` updates
