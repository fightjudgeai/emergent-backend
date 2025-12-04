# Stat Engine Normalization - Implementation Guide

## 🎯 Overview

The Stat Engine Normalization system provides a **parallel, sportsbook-grade event tracking model** alongside the existing cumulative `round_state` system. This allows for:

- **UFCstats Parity**: Standardized event vocabulary matching industry standards
- **Deterministic Control Time**: Provable, auditable control time calculations
- **Event Stream API**: Granular event-by-event data feed
- **Backward Compatibility**: Existing `round_state` API continues to work

---

## 📊 Architecture

### Parallel System Design

```
┌─────────────────────────────────────────────────────────┐
│                    EXISTING SYSTEM                      │
│                   (round_state table)                   │
│                                                         │
│   Cumulative stats per round:                          │
│   - red_sig_strikes: 25                                │
│   - blue_control_sec: 120                              │
│   - etc.                                               │
└─────────────────────────────────────────────────────────┘
                         │
                         │ Bridge Function
                         ▼
┌─────────────────────────────────────────────────────────┐
│                    NEW SYSTEM                           │
│                 (fight_events table)                    │
│                                                         │
│   Granular event stream:                               │
│   - seq: 1, type: STR_LAND, corner: RED, round: 1     │
│   - seq: 2, type: CTRL_START, corner: RED, round: 1   │
│   - seq: 3, type: KD, corner: RED, round: 1           │
│   - seq: 4, type: CTRL_END, corner: RED, round: 1     │
│   - ...                                                │
└─────────────────────────────────────────────────────────┘
```

Both systems coexist during migration. The new system can be validated against the existing cumulative stats.

---

## 🗄️ Database Schema

### New Table: `fight_events`

Created by migration `005_stat_engine_normalization.sql`

```sql
CREATE TABLE fight_events (
    id UUID PRIMARY KEY,
    fight_id UUID REFERENCES fights(id),
    round INT NOT NULL,
    second_in_round INT NOT NULL,  -- 0-300 (5 minutes)
    event_type TEXT NOT NULL,      -- Controlled vocabulary
    corner TEXT NOT NULL,           -- RED, BLUE, NEUTRAL
    metadata JSONB DEFAULT '{}',   -- Event-specific data
    seq BIGINT NOT NULL,           -- Monotonic sequence
    created_at TIMESTAMPTZ,
    
    CONSTRAINT unique_event_seq UNIQUE (fight_id, seq)
);
```

**Key Concepts:**

- **seq**: Monotonically increasing sequence number for total ordering
- **second_in_round**: Event timestamp within the round (0-300 seconds)
- **event_type**: One of 12 standardized event types
- **metadata**: Flexible JSON field for event-specific data

---

## 📐 Event Type Vocabulary

The system enforces a **controlled vocabulary** aligned with UFCstats:

| Event Type | Description | Example Metadata |
|------------|-------------|------------------|
| `STR_ATT` | Strike attempt | `{"target": "head"}` |
| `STR_LAND` | Strike landed | `{"is_significant": true, "technique": "punch"}` |
| `KD` | Knockdown | `{}` |
| `TD_ATT` | Takedown attempt | `{"technique": "single_leg"}` |
| `TD_LAND` | Takedown landed | `{"slam": false}` |
| `CTRL_START` | Control period begins | `{"position": "mount"}` |
| `CTRL_END` | Control period ends | `{}` |
| `SUB_ATT` | Submission attempt | `{"technique": "rear_naked_choke"}` |
| `REVERSAL` | Position reversal | `{}` |
| `ROUND_START` | Round begins | `{}` |
| `ROUND_END` | Round ends | `{}` |
| `FIGHT_END` | Fight ends | `{}` |

### Legacy Alias Mapping

The system automatically normalizes legacy event types:

```
"strike" → STR_LAND
"takedown" → TD_LAND
"submission" → SUB_ATT
"knockdown" → KD
"control_start" → CTRL_START
"control_end" → CTRL_END
```

---

## 🧮 Deterministic Control Time Algorithm

**Problem**: How do we calculate control time in a provable, auditable way?

**Solution**: Pair `CTRL_START` events with the next `CTRL_END` event chronologically.

### Algorithm

```python
control_time = 0

for each CTRL_START event (in chronological order):
    Find next CTRL_END event for same corner
    
    if CTRL_END found:
        duration = CTRL_END.second_in_round - CTRL_START.second_in_round
        control_time += duration
    else:
        # Control continues to round end
        duration = 300 - CTRL_START.second_in_round
        control_time += duration

return control_time
```

### Validation Rules

1. **Pairing**: Each `CTRL_START` must have a matching `CTRL_END` (or continue to round end)
2. **Non-Overlapping**: Fighter A and Fighter B cannot control simultaneously
3. **Conservation**: `red_control + blue_control ≤ 300 seconds`
4. **Monotonicity**: Events must be ordered by `second_in_round`

---

## 🔄 Migration Strategy

### Phase 1: Parallel System (Current)

✅ **Complete**: The new `fight_events` table exists alongside `round_state`

### Phase 2: Generate Events from Existing Data

Use the bridge function to convert cumulative stats to events:

```python
POST /v1/events/generate-from-round-state
{
    "fight_id": "uuid",
    "round_num": 1,
    "round_state": {
        "red_sig_strikes": 25,
        "blue_sig_strikes": 18,
        "red_knockdowns": 1,
        "blue_knockdowns": 0,
        "red_control_sec": 120,
        "blue_control_sec": 45
    }
}
```

This creates granular events distributed evenly across the round.

### Phase 3: Validation

Compare aggregated stats from events against cumulative stats:

```python
GET /v1/events/{fight_id}/round/{round_num}/aggregate
```

Should match the original `round_state` data.

### Phase 4: Live Event Ingestion

For new fights, insert events directly via the `insert_event()` method:

```python
event_service.insert_event(
    fight_id=UUID("..."),
    round_num=1,
    second_in_round=45,
    event_type="STR_LAND",
    corner="RED",
    metadata={"is_significant": True, "target": "head"}
)
```

---

## 🚀 API Endpoints

### 1. Get Event Stream

```http
GET /v1/events/{fight_id}?round=1&event_type=STR_LAND
Authorization: Bearer <API_KEY>
```

**Response:**
```json
{
    "fight_id": "uuid",
    "round": 1,
    "event_type_filter": "STR_LAND",
    "total_events": 43,
    "events": [
        {
            "id": "uuid",
            "fight_id": "uuid",
            "round": 1,
            "second_in_round": 12,
            "event_type": "STR_LAND",
            "corner": "RED",
            "seq": 1,
            "metadata": {"is_significant": true, "generated": true},
            "created_at": "2025-01-15T10:30:00Z"
        },
        ...
    ]
}
```

### 2. Get Event Summary

```http
GET /v1/events/{fight_id}/summary
Authorization: Bearer <API_KEY>
```

**Response:**
```json
{
    "fight_id": "uuid",
    "total_events": 287,
    "event_counts": {
        "STR_LAND": 120,
        "KD": 3,
        "CTRL_START": 8,
        "CTRL_END": 8,
        "TD_LAND": 4
    },
    "rounds": [1, 2, 3],
    "first_event_seq": 1,
    "last_event_seq": 287
}
```

### 3. Aggregate Stats from Events

```http
GET /v1/events/{fight_id}/round/{round_num}/aggregate
Authorization: Bearer <API_KEY>
```

**Response:**
```json
{
    "fight_id": "uuid",
    "round": 1,
    "stats": {
        "red": {
            "strikes": 48,
            "sig_strikes": 25,
            "knockdowns": 1,
            "control_sec": 120,
            "takedowns": 2,
            "sub_attempts": 1
        },
        "blue": {
            "strikes": 35,
            "sig_strikes": 18,
            "knockdowns": 0,
            "control_sec": 45,
            "takedowns": 0,
            "sub_attempts": 0
        }
    }
}
```

### 4. Validate Control Time

```http
GET /v1/events/{fight_id}/round/{round_num}/control-validation
Authorization: Bearer <API_KEY>
```

**Response:**
```json
{
    "fight_id": "uuid",
    "round": 1,
    "validation": {
        "has_overlap": false,
        "overlap_details": {
            "red_control": 120,
            "blue_control": 45,
            "total_control": 165,
            "round_duration": 300,
            "remaining_neutral": 135
        }
    }
}
```

### 5. Generate Events from Round State

```http
POST /v1/events/generate-from-round-state
Authorization: Bearer <API_KEY>
Content-Type: application/json

{
    "fight_id": "uuid",
    "round_num": 1,
    "round_state": {
        "red_sig_strikes": 25,
        "blue_sig_strikes": 18,
        "red_knockdowns": 1,
        "blue_knockdowns": 0,
        "red_control_sec": 120,
        "blue_control_sec": 45
    }
}
```

**Response:**
```json
{
    "fight_id": "uuid",
    "round": 1,
    "events_created": 48,
    "status": "success"
}
```

---

## 🧪 Testing & Validation

### Test Case 1: Basic Control Time

```sql
-- Insert paired CTRL_START/CTRL_END events
INSERT INTO fight_events (fight_id, round, second_in_round, event_type, corner, seq)
VALUES
    ('uuid', 1, 30, 'CTRL_START', 'RED', 1),
    ('uuid', 1, 90, 'CTRL_END', 'RED', 2);

-- Calculate control time
SELECT calculate_control_time_from_events('uuid', 1, 'RED');
-- Expected: 60 seconds
```

### Test Case 2: Control to Round End

```sql
-- CTRL_START at 250 seconds, no CTRL_END
INSERT INTO fight_events (fight_id, round, second_in_round, event_type, corner, seq)
VALUES ('uuid', 1, 250, 'CTRL_START', 'RED', 1);

-- Calculate control time
SELECT calculate_control_time_from_events('uuid', 1, 'RED');
-- Expected: 50 seconds (300 - 250)
```

### Test Case 3: Overlapping Control (Should Fail)

```sql
-- RED controls 30-90
-- BLUE controls 60-120
-- Overlap: 60-90 (30 seconds)

SELECT validate_no_control_overlap('uuid', 1);
-- Expected: has_overlap = true, overlap_seconds = 30
```

---

## 📊 Benefits

### UFCstats Parity
✅ Standardized event vocabulary  
✅ Granular event tracking  
✅ Audit trail for every stat

### Sportsbook-Grade Determinism
✅ Provable control time calculation  
✅ No overlapping control periods  
✅ Validation rules enforced  
✅ Immutable event log

### Developer Experience
✅ Clear API contracts  
✅ Self-documenting events  
✅ Easy to add new stat types  
✅ Event stream for real-time feeds

---

## ⚠️ Important Notes

1. **User Must Run Migration**: The `005_stat_engine_normalization.sql` migration must be run manually in Supabase SQL Editor. The application will start, but event-related features will fail until the migration is complete.

2. **Backward Compatibility**: The existing `round_state` API continues to work unchanged. The new event system is additive.

3. **Generated Events**: Events created from cumulative stats have `metadata.generated = true`. Events from live ingestion will not have this flag.

4. **Performance**: The `fight_events` table will grow quickly. Consider partitioning by `fight_id` or `created_at` for large-scale deployments.

5. **Control Time Edge Cases**: If control periods overlap (data error), the validation endpoint will flag it, but the calculation will still return a best-effort result.

---

## 📝 Next Steps

1. ✅ **Complete**: Event service implementation
2. ✅ **Complete**: API endpoints for event stream
3. ⏳ **Pending**: User runs migration `005_stat_engine_normalization.sql`
4. ⏳ **Pending**: Generate events from existing `round_state` data
5. ⏳ **Pending**: Validate event-based stats match cumulative stats
6. ⏳ **Future**: Migrate live event ingestion to new system
7. ⏳ **Future**: Deprecate direct `round_state` updates

---

## 🔗 Related Documentation

- **Migration File**: `/app/datafeed_api/migrations/005_stat_engine_normalization.sql`
- **Audit Report**: `/app/datafeed_api/STAT_ENGINE_AUDIT.md`
- **Service Code**: `/app/datafeed_api/services/event_service.py`
- **API Routes**: `/app/datafeed_api/api/event_routes.py`
