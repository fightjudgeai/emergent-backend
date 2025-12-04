## Sportsbook Markets System - Complete Guide

## 🎯 Overview

The Sportsbook Markets system provides a complete betting infrastructure with automatic market settlement based on fight results and statistics.

---

## 📊 Market Types

### 1. WINNER
**Description:** Bet on fight winner (RED or BLUE corner)

**Parameters:**
```json
{
  "red_odds": 1.75,
  "blue_odds": 2.10
}
```

**Settlement:** Uses `fight_results.winner_side`

**Result Payload:**
```json
{
  "market_type": "WINNER",
  "winner_side": "RED",
  "method": "KO",
  "round": 2,
  "time": "3:15"
}
```

---

### 2. TOTAL_SIG_STRIKES
**Description:** Over/under on total significant strikes (both fighters combined)

**Parameters:**
```json
{
  "line": 50.5,
  "over_odds": 1.91,
  "under_odds": 1.91
}
```

**Settlement:** Uses `round_state` (latest): `red_sig_strikes + blue_sig_strikes`

**Result Payload:**
```json
{
  "market_type": "TOTAL_SIG_STRIKES",
  "line": 50.5,
  "actual_total": 64,
  "red_sig_strikes": 40,
  "blue_sig_strikes": 24,
  "winning_side": "OVER"
}
```

---

### 3. KD_OVER_UNDER
**Description:** Over/under on total knockdowns

**Parameters:**
```json
{
  "line": 0.5,
  "over_odds": 2.50,
  "under_odds": 1.50
}
```

**Settlement:** Uses `round_state` (latest): `red_knockdowns + blue_knockdowns`

**Result Payload:**
```json
{
  "market_type": "KD_OVER_UNDER",
  "line": 0.5,
  "actual_total": 1,
  "red_knockdowns": 1,
  "blue_knockdowns": 0,
  "winning_side": "OVER"
}
```

---

### 4. SUB_ATT_OVER_UNDER
**Description:** Over/under on submission attempts

**Parameters:**
```json
{
  "line": 1.5,
  "over_odds": 2.00,
  "under_odds": 1.80
}
```

**Settlement:** Uses submission attempts (when tracked in round_state)

**Status:** ⚠️ Requires `submission_attempts` field in `round_state` schema

---

## 🔄 Auto-Settlement

Markets automatically settle when **fight result is added/updated**.

**Trigger:** `auto_settle_markets_on_result` on `fight_results` table

**Process:**
1. Fight result inserted/updated
2. Trigger fires
3. All OPEN markets for that fight are settled
4. Settlement records created
5. Market status updated to SETTLED

**Example:**
```sql
-- Insert fight result
INSERT INTO fight_results (fight_id, winner_side, method, round, time)
VALUES ('...', 'RED', 'KO', 2, '3:15');
-- ✅ All markets auto-settle!
```

---

## 🔌 API Endpoints

### Create Market
```bash
POST /v1/markets/
Content-Type: application/json

{
  "fight_id": "uuid",
  "market_type": "TOTAL_SIG_STRIKES",
  "params": {"line": 50.5, "over_odds": 1.91, "under_odds": 1.91},
  "status": "OPEN"
}
```

### Create Standard Markets
```bash
POST /v1/markets/standard
Content-Type: application/json

{
  "fight_id": "uuid",
  "config": {
    "winner": {"red_odds": 1.75, "blue_odds": 2.10},
    "total_sig_strikes": {"line": 60.5, "over_odds": 1.85, "under_odds": 1.95}
  }
}
```

Creates:
- WINNER market
- TOTAL_SIG_STRIKES market
- KD_OVER_UNDER market

### Get Fight Markets
```bash
GET /v1/markets/fight/{fight_id}?status=OPEN
```

### Manually Settle Market
```bash
POST /v1/markets/settle/{market_id}
```

### Settle All Fight Markets
```bash
POST /v1/markets/settle/fight/{fight_id}
```

### Get Market Settlement
```bash
GET /v1/markets/settlements/{market_id}
```

### Market Statistics
```bash
GET /v1/markets/stats/overview
```

---

## 🧪 Testing with PFC50

### Step 1: Create Markets for PFC50-F1

```bash
# Get fight ID
FIGHT_ID=$(curl -s http://localhost:8002/v1/fights/PFC50-F1/live | jq -r '.fight.code')

# Create standard markets
curl -X POST http://localhost:8002/v1/markets/standard \
  -H "Content-Type: application/json" \
  -d '{
    "fight_id": "FIGHT_UUID_HERE",
    "config": {
      "winner": {"red_odds": 1.75, "blue_odds": 2.10},
      "total_sig_strikes": {"line": 50.5, "over_odds": 1.91, "under_odds": 1.91},
      "kd_over_under": {"line": 0.5, "over_odds": 2.50, "under_odds": 1.50}
    }
  }' | jq
```

### Step 2: View Markets
```bash
curl "http://localhost:8002/v1/markets/fight/FIGHT_UUID" | jq
```

### Step 3: Trigger Auto-Settlement

Auto-settlement already happened when `fight_results` was inserted during data seeding!

Check settlements:
```bash
curl "http://localhost:8002/v1/markets/settlements/fight/FIGHT_UUID" | jq
```

### Step 4: Manually Settle (if needed)
```bash
curl -X POST "http://localhost:8002/v1/markets/settle/fight/FIGHT_UUID" | jq
```

---

## 📈 Expected Results for PFC50-F1

Based on existing data:
- **RED:** John "The Blade" Strike
- **BLUE:** Mike "The Hammer" Iron
- **Result:** RED wins by UD

**Round 2 State (latest):**
- Red sig strikes: 24
- Blue sig strikes: 18
- **Total sig strikes: 42**
- Red knockdowns: 1
- Blue knockdowns: 0
- **Total knockdowns: 1**

**Market Settlements:**

1. **WINNER**
   - Winning Side: RED ✅
   - Method: UD
   
2. **TOTAL_SIG_STRIKES (line: 50.5)**
   - Actual Total: 42
   - Winning Side: UNDER ✅
   
3. **KD_OVER_UNDER (line: 0.5)**
   - Actual Total: 1
   - Winning Side: OVER ✅

---

## 🔍 Database Schema

### markets table
```sql
CREATE TABLE markets (
    id UUID PRIMARY KEY,
    fight_id UUID REFERENCES fights(id),
    market_type TEXT,
    params JSONB,
    status TEXT CHECK (status IN ('OPEN', 'SUSPENDED', 'SETTLED', 'CANCELLED')),
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ,
    UNIQUE(fight_id, market_type)
);
```

### market_settlements table
```sql
CREATE TABLE market_settlements (
    id UUID PRIMARY KEY,
    market_id UUID REFERENCES markets(id),
    result_payload JSONB,
    settled_at TIMESTAMPTZ,
    UNIQUE(market_id)
);
```

---

## 🛠️ Manual Operations

### Create Markets for All Fights in Event

```sql
-- For each fight in PFC50
DO $$
DECLARE
    v_fight RECORD;
BEGIN
    FOR v_fight IN 
        SELECT f.id 
        FROM fights f
        JOIN events e ON f.event_id = e.id
        WHERE e.code = 'PFC50'
    LOOP
        -- Create WINNER market
        INSERT INTO markets (fight_id, market_type, params, status)
        VALUES (
            v_fight.id,
            'WINNER',
            '{"red_odds": 1.91, "blue_odds": 1.91}'::jsonb,
            'OPEN'
        ) ON CONFLICT DO NOTHING;
        
        -- Create TOTAL_SIG_STRIKES market
        INSERT INTO markets (fight_id, market_type, params, status)
        VALUES (
            v_fight.id,
            'TOTAL_SIG_STRIKES',
            '{"line": 50.5, "over_odds": 1.91, "under_odds": 1.91}'::jsonb,
            'OPEN'
        ) ON CONFLICT DO NOTHING;
        
        -- Create KD_OVER_UNDER market
        INSERT INTO markets (fight_id, market_type, params, status)
        VALUES (
            v_fight.id,
            'KD_OVER_UNDER',
            '{"line": 0.5, "over_odds": 2.50, "under_odds": 1.50}'::jsonb,
            'OPEN'
        ) ON CONFLICT DO NOTHING;
    END LOOP;
END $$;
```

### Manually Settle All Markets for Fight

```sql
SELECT * FROM settle_market(market_id)
FROM markets
WHERE fight_id = (SELECT id FROM fights WHERE code = 'PFC50-F1')
  AND status = 'OPEN';
```

### Re-settle Market (delete existing settlement first)

```sql
-- Delete existing settlement
DELETE FROM market_settlements WHERE market_id = 'uuid';

-- Update market status
UPDATE markets SET status = 'OPEN' WHERE id = 'uuid';

-- Re-settle
SELECT settle_market('uuid');
```

---

## ⚠️ Important Notes

1. **One Market Per Type Per Fight:** Constraint prevents duplicate market types for same fight

2. **Auto-Settlement:** Markets settle automatically when fight results are added - no manual intervention needed for production

3. **Settlement Immutability:** Once settled, markets cannot be re-settled without deleting the settlement record

4. **Error Handling:** Failed settlements mark market as SUSPENDED instead of breaking the trigger

5. **SUB_ATT_OVER_UNDER:** Requires `submission_attempts` field to be added to `round_state` schema for accurate settlement

---

## 📊 Market Status Flow

```
OPEN ──┐
       │
       ├──> [Fight Result Added] ──> SETTLED
       │
       └──> [Manual Suspension] ──> SUSPENDED
                                      │
                                      └──> [Reopen] ──> OPEN
```

**CANCELLED:** Manual cancellation (void all bets)

---

## ✅ Summary

**Markets:**
- ✅ 4 market types (WINNER, TOTAL_SIG_STRIKES, KD_OVER_UNDER, SUB_ATT_OVER_UNDER)
- ✅ Configurable parameters (lines, odds)
- ✅ Status management (OPEN, SUSPENDED, SETTLED, CANCELLED)

**Settlement:**
- ✅ Automatic settlement on fight result
- ✅ Manual settlement via API
- ✅ Batch settlement for fight/event
- ✅ Detailed result payloads

**Integration:**
- ✅ Works with existing round_state and fight_results data
- ✅ REST API for market management
- ✅ SQL functions for programmatic access
- ✅ Trigger-based automation

The system provides a complete sportsbook infrastructure ready for production use!
