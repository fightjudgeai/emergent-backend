# 🎯 Dummy Data Loading Guide

## Method 1: Supabase Table UI (Recommended)

### Step 1 – Insert Event (PFC50)

1. Open **events** table in Supabase Table Editor
2. Click **"Insert row"**
3. Fill in:
   - `code`: **PFC50**
   - `name`: **PFC 50: Frisco**
   - `venue`: **Comerica Center**
   - `promotion`: **PFC**
   - `start_time_utc`: **2026-01-24 01:00:00+00**
4. Click **Save**
5. **📋 COPY THE EVENT ID** (you'll need it for fights)

---

### Step 2 – Insert 6 Fighters

Open **fighters** table and create 6 rows:

#### Fighter 1 (Red corner - Fight 1)
- `first_name`: **John**
- `last_name`: **Strike**
- `nickname`: **The Blade**
- `country`: **USA**
- **📋 Copy ID → FTR1**

#### Fighter 2 (Blue corner - Fight 1)
- `first_name`: **Mike**
- `last_name`: **Iron**
- `nickname`: **The Hammer**
- `country`: **USA**
- **📋 Copy ID → FTR2**

#### Fighter 3 (Red corner - Fight 2)
- `first_name`: **Carlos**
- `last_name`: **Rivera**
- `nickname`: **El Fuego**
- `country`: **MEX**
- **📋 Copy ID → FTR3**

#### Fighter 4 (Blue corner - Fight 2)
- `first_name`: **Alex**
- `last_name`: **Stone**
- `nickname`: **The Wall**
- `country`: **USA**
- **📋 Copy ID → FTR4**

#### Fighter 5 (Red corner - Fight 3)
- `first_name`: **David**
- `last_name`: **Lee**
- `nickname`: **Dragon**
- `country`: **USA**
- **📋 Copy ID → FTR5**

#### Fighter 6 (Blue corner - Fight 3)
- `first_name`: **Mark**
- `last_name`: **Torres**
- `nickname`: **The Tank**
- `country`: **USA**
- **📋 Copy ID → FTR6**

---

### Step 3 – Insert 3 Fights

Open **fights** table and create 3 rows:

#### Fight 1: PFC50-F1 (John Strike vs Mike Iron)
- `event_id`: **[PFC50 Event ID]**
- `bout_order`: **3** (main event)
- `code`: **PFC50-F1**
- `red_fighter_id`: **[FTR1 - John Strike ID]**
- `blue_fighter_id`: **[FTR2 - Mike Iron ID]**
- `scheduled_rounds`: **3**
- `weight_class`: **Lightweight**
- `rule_set`: **MMA Unified**
- **📋 Copy ID → FIGHT1**

#### Fight 2: PFC50-F2 (Carlos Rivera vs Alex Stone)
- `event_id`: **[PFC50 Event ID]**
- `bout_order`: **2**
- `code`: **PFC50-F2**
- `red_fighter_id`: **[FTR3 - Carlos Rivera ID]**
- `blue_fighter_id`: **[FTR4 - Alex Stone ID]**
- `scheduled_rounds`: **3**
- `weight_class`: **Featherweight**
- `rule_set`: **MMA Unified**
- **📋 Copy ID → FIGHT2**

#### Fight 3: PFC50-F3 (David Lee vs Mark Torres)
- `event_id`: **[PFC50 Event ID]**
- `bout_order`: **1**
- `code`: **PFC50-F3**
- `red_fighter_id`: **[FTR5 - David Lee ID]**
- `blue_fighter_id`: **[FTR6 - Mark Torres ID]**
- `scheduled_rounds`: **3**
- `weight_class`: **Welterweight**
- `rule_set`: **MMA Unified**
- **📋 Copy ID → FIGHT3**

---

### Step 4 – Insert Round States (2 per fight = 6 total)

Open **round_state** table.

#### Fight 1 (PFC50-F1) - Round 1 (Locked)
- `fight_id`: **[FIGHT1 ID]**
- `round`: **1**
- `ts_ms`: **1737761000000**
- `seq`: **1**
- `red_strikes`: **25**
- `blue_strikes`: **18**
- `red_sig_strikes`: **15**
- `blue_sig_strikes`: **10**
- `red_knockdowns`: **0**
- `blue_knockdowns`: **0**
- `red_control_sec`: **60**
- `blue_control_sec`: **30**
- `red_ai_damage`: **6.3**
- `blue_ai_damage`: **5.0**
- `red_ai_win_prob`: **0.62**
- `blue_ai_win_prob`: **0.38**
- `round_locked`: **true**

#### Fight 1 (PFC50-F1) - Round 2 (Live)
- `fight_id`: **[FIGHT1 ID]**
- `round`: **2**
- `ts_ms`: **1737761100000**
- `seq`: **2**
- `red_strikes`: **40**
- `blue_strikes`: **30**
- `red_sig_strikes`: **24**
- `blue_sig_strikes`: **18**
- `red_knockdowns`: **1**
- `blue_knockdowns`: **0**
- `red_control_sec`: **80**
- `blue_control_sec`: **40**
- `red_ai_damage`: **8.1**
- `blue_ai_damage`: **5.4**
- `red_ai_win_prob`: **0.78**
- `blue_ai_win_prob`: **0.22**
- `round_locked`: **false**

#### Fight 2 (PFC50-F2) - Round 1 (Locked)
- `fight_id`: **[FIGHT2 ID]**
- `round`: **1**
- `ts_ms`: **1737762000000**
- `seq`: **1**
- `red_strikes`: **22**
- `blue_strikes`: **20**
- `red_sig_strikes`: **13**
- `blue_sig_strikes`: **12**
- `red_knockdowns`: **0**
- `blue_knockdowns`: **0**
- `red_control_sec`: **55**
- `blue_control_sec`: **35**
- `red_ai_damage`: **5.8**
- `blue_ai_damage`: **6.2**
- `red_ai_win_prob`: **0.48**
- `blue_ai_win_prob`: **0.52**
- `round_locked`: **true**

#### Fight 2 (PFC50-F2) - Round 2 (Live)
- `fight_id`: **[FIGHT2 ID]**
- `round`: **2**
- `ts_ms`: **1737762100000**
- `seq`: **2**
- `red_strikes`: **35**
- `blue_strikes`: **38**
- `red_sig_strikes`: **20**
- `blue_sig_strikes**: **22**
- `red_knockdowns`: **0**
- `blue_knockdowns`: **1**
- `red_control_sec`: **70**
- `blue_control_sec`: **50**
- `red_ai_damage`: **7.2**
- `blue_ai_damage`: **8.8**
- `red_ai_win_prob`: **0.35**
- `blue_ai_win_prob`: **0.65**
- `round_locked`: **false**

#### Fight 3 (PFC50-F3) - Round 1 (Locked)
- `fight_id`: **[FIGHT3 ID]**
- `round`: **1**
- `ts_ms`: **1737763000000**
- `seq`: **1**
- `red_strikes`: **28**
- `blue_strikes`: **15**
- `red_sig_strikes`: **18**
- `blue_sig_strikes`: **8**
- `red_knockdowns`: **1**
- `blue_knockdowns`: **0**
- `red_control_sec`: **75**
- `blue_control_sec`: **25**
- `red_ai_damage`: **9.5**
- `blue_ai_damage`: **3.2**
- `red_ai_win_prob`: **0.85**
- `blue_ai_win_prob`: **0.15**
- `round_locked`: **true**

#### Fight 3 (PFC50-F3) - Round 2 (Live)
- `fight_id`: **[FIGHT3 ID]**
- `round`: **2**
- `ts_ms`: **1737763100000**
- `seq`: **2**
- `red_strikes**: **42**
- `blue_strikes`: **20**
- `red_sig_strikes`: **28**
- `blue_sig_strikes`: **12**
- `red_knockdowns`: **2**
- `blue_knockdowns`: **0**
- `red_control_sec`: **95**
- `blue_control_sec`: **25**
- `red_ai_damage`: **12.8**
- `blue_ai_damage`: **4.1**
- `red_ai_win_prob`: **0.92**
- `blue_ai_win_prob`: **0.08**
- `round_locked`: **false**

---

### Step 5 – Insert Fight Results (Optional)

Open **fight_results** table.

#### Fight 1 Result
- `fight_id`: **[FIGHT1 ID]**
- `winner_side`: **RED**
- `method`: **UD** (Unanimous Decision)
- `round`: **3**
- `time`: **5:00**

#### Fight 2 Result
- `fight_id`: **[FIGHT2 ID]**
- `winner_side`: **BLUE**
- `method`: **TKO**
- `round`: **2**
- `time`: **4:32**

#### Fight 3 Result
- `fight_id`: **[FIGHT3 ID]**
- `winner_side`: **RED**
- `method`: **KO**
- `round`: **2**
- `time`: **3:15**

---

## ✅ Verification

After loading all data, verify in Supabase SQL Editor:

```sql
-- Check event
SELECT * FROM events WHERE code = 'PFC50';

-- Check fighters
SELECT * FROM fighters ORDER BY created_at;

-- Check fights
SELECT code, bout_order FROM fights WHERE event_id IN (SELECT id FROM events WHERE code = 'PFC50');

-- Check round states
SELECT f.code, rs.round, rs.seq, rs.round_locked 
FROM round_state rs 
JOIN fights f ON rs.fight_id = f.id 
ORDER BY f.code, rs.seq;

-- Check results
SELECT f.code, fr.winner_side, fr.method 
FROM fight_results fr 
JOIN fights f ON fr.fight_id = f.id;
```

Expected counts:
- **1 event** (PFC50)
- **6 fighters**
- **3 fights** (PFC50-F1, PFC50-F2, PFC50-F3)
- **6 round_state** rows (2 per fight)
- **3 fight_results** rows (optional)

---

## 🎉 Ready to Test!

Once data is loaded, you can:

1. Start the API server
2. Get API keys: `SELECT name, api_key, scope FROM api_clients;`
3. Test REST endpoints
4. Test WebSocket subscriptions

See `/app/datafeed_api/README.md` for API usage examples.
