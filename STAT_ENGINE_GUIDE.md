# Stat Engine - Production-Grade Statistics Aggregation
## Complete Documentation

---

## 🎯 Overview

The **Stat Engine** is a production-grade microservice that aggregates fight event data into normalized statistics at three levels:

1. **Round Stats** - Per-round statistics for each fighter
2. **Fight Stats** - Aggregated statistics for entire fights
3. **Career Stats** - Lifetime statistics across all fights

**CRITICAL RULE:** The Stat Engine ONLY reads from the `events` table. It NEVER creates events. All statistics are derived from judge logging.

---

## 📊 What Does It Track?

### Strike Statistics:
- Total strikes (attempted & landed)
- Significant strikes (attempted & landed)
- Breakdown by target (head, body, leg)
- Knockdowns
- Rocked/stunned events

### Grappling Statistics:
- Takedown attempts, landed, stuffed
- Submission attempts
- Ground control time
- Back control time
- Mount time
- Clinch control time
- Cage control time

### Computed Metrics:
- Significant strike accuracy percentage
- Takedown accuracy percentage
- Strikes per minute
- Control time percentage
- Knockdowns per 15 minutes
- Average stats across career

---

## 🔧 Architecture

### Module 1: Event Reader
**File:** `/app/backend/stat_engine/event_reader.py`

**Purpose:** Reads events from the existing `events` table (READ-ONLY)

**Key Methods:**
```python
# Get all events for a fight/round/fighter
get_fight_events(fight_id, round_num=None, fighter_id=None, event_type=None)

# Get control events for time calculation
get_control_events(fight_id, round_num, fighter_id)

# Classify events
classify_strike(event_type, metadata)
is_knockdown(event_type)
is_takedown(event_type, metadata)
```

**Features:**
- Filters by fight_id, round, fighter, event type, source
- Classifies strikes (significant, target, landed)
- Detects knockdowns, rocked events, takedowns, submissions
- Extracts control time from START/STOP events

---

### Module 2: Round Stats Aggregator
**File:** `/app/backend/stat_engine/round_aggregator.py`

**Purpose:** Computes per-round statistics for each fighter

**Key Methods:**
```python
# Aggregate stats for one fighter in one round
aggregate_round(fight_id, round_num, fighter_id)

# Aggregate all fighters in a round
aggregate_all_fighters_in_round(fight_id, round_num)

# Save to database (UPSERT)
save_round_stats(stats)
```

**Output:** `RoundStats` object stored in `round_stats` collection

**Control Time Calculation:**
- Parses CONTROL_START/STOP events
- Sums durations by control type
- Handles multiple control periods
- Tracks ground, clinch, cage, back, mount time

---

### Module 3: Fight Stats Aggregator
**File:** `/app/backend/stat_engine/fight_aggregator.py`

**Purpose:** Sums all round stats into fight-level totals

**Key Methods:**
```python
# Aggregate all rounds for a fighter in a fight
aggregate_fight(fight_id, fighter_id)

# Aggregate all fighters in a fight
aggregate_all_fighters_in_fight(fight_id)
```

**Computed Metrics:**
- Significant strike accuracy: `(landed / total) * 100`
- Takedown accuracy: `(landed / attempts) * 100`
- Strikes per minute: `landed / (rounds * 5)`
- Control time percentage: `(control_time / total_time) * 100`

**Output:** `FightStats` object stored in `fight_stats` collection

---

### Module 4: Career Stats Aggregator
**File:** `/app/backend/stat_engine/career_aggregator.py`

**Purpose:** Aggregates all fight stats into lifetime career metrics

**Key Methods:**
```python
# Aggregate career stats for one fighter
aggregate_career(fighter_id)

# Aggregate all fighters (nightly job)
aggregate_all_fighters()
```

**Advanced Metrics:**
- Average sig strikes per minute (across all rounds)
- Average sig strike accuracy (career-wide)
- Average takedown accuracy
- Average control time per fight
- Knockdowns per 15 minutes
- Takedown defense percentage

**Output:** `CareerStats` object stored in `career_stats` collection

---

### Module 5: Scheduler
**File:** `/app/backend/stat_engine/scheduler.py`

**Purpose:** Orchestrates aggregation with multiple trigger types

**Trigger Types:**

1. **Manual Trigger**
   - On-demand via API
   - Use for testing or fixing data

2. **Round-Locked Trigger**
   - When a round is locked/finalized
   - Aggregates stats for that round

3. **Post-Fight Trigger**
   - When a fight completes
   - Aggregates all rounds + fight stats

4. **Nightly Trigger**
   - Scheduled background job (default 3am UTC)
   - Aggregates career stats for all fighters

**Key Methods:**
```python
# Trigger specific aggregations
trigger_round_aggregation(fight_id, round_num, trigger)
trigger_fight_aggregation(fight_id, trigger)
trigger_career_aggregation(fighter_id=None, trigger)

# Full recalculation (rounds + fight + career)
trigger_full_recalculation(fight_id)

# Background scheduler
start_nightly_aggregation(hour=3)
stop_nightly_aggregation()
```

**Fault Tolerance:**
- Job tracking in `aggregation_jobs` collection
- Records status (pending, running, completed, failed)
- Tracks errors
- Idempotent operations (safe to run multiple times)

---

## 🚀 API Endpoints

Base URL: `/api/stats`

### Aggregation Triggers

#### 1. Aggregate Round
```bash
POST /api/stats/aggregate/round?fight_id=ufc301_main&round_num=1&trigger=manual
```

**Response:**
```json
{
  "job_id": "uuid",
  "status": "completed",
  "rows_updated": 2,
  "message": "Round 1 aggregation completed"
}
```

---

#### 2. Aggregate Fight
```bash
POST /api/stats/aggregate/fight?fight_id=ufc301_main&trigger=post_fight
```

**Response:**
```json
{
  "job_id": "uuid",
  "status": "completed",
  "rows_updated": 2,
  "message": "Fight aggregation completed"
}
```

---

#### 3. Aggregate Career (Single Fighter)
```bash
POST /api/stats/aggregate/career?fighter_id=fighter_1&trigger=manual
```

---

#### 4. Aggregate Career (All Fighters)
```bash
POST /api/stats/aggregate/career?trigger=nightly
```

---

#### 5. Full Recalculation
```bash
POST /api/stats/aggregate/full/ufc301_main
```

**Response:**
```json
{
  "fight_id": "ufc301_main",
  "jobs_executed": 8,
  "successful": 8,
  "failed": 0,
  "message": "Full recalculation completed: 8 jobs"
}
```

---

### Statistics Retrieval

#### 6. Get Round Stats
```bash
GET /api/stats/round/{fight_id}/{round_num}/{fighter_id}
```

**Example:**
```bash
GET /api/stats/round/ufc301_main/1/fighter_1
```

**Response:**
```json
{
  "id": "uuid",
  "fight_id": "ufc301_main",
  "round_num": 1,
  "fighter_id": "fighter_1",
  "total_strikes_attempted": 45,
  "total_strikes_landed": 28,
  "sig_strikes_attempted": 30,
  "sig_strikes_landed": 18,
  "sig_head_landed": 12,
  "sig_body_landed": 4,
  "sig_leg_landed": 2,
  "knockdowns": 1,
  "rocked_events": 0,
  "td_attempts": 2,
  "td_landed": 1,
  "td_stuffed": 1,
  "sub_attempts": 1,
  "ground_control_secs": 45,
  "clinch_control_secs": 20,
  "cage_control_secs": 15,
  "back_control_secs": 30,
  "mount_secs": 15,
  "total_control_secs": 125,
  "computed_at": "2025-01-01T00:00:00Z",
  "last_updated": "2025-01-01T00:00:00Z",
  "source_event_count": 67
}
```

---

#### 7. Get Fight Stats
```bash
GET /api/stats/fight/{fight_id}/{fighter_id}
```

**Response:**
```json
{
  "fight_id": "ufc301_main",
  "fighter_id": "fighter_1",
  "total_rounds": 3,
  "sig_strikes_landed": 54,
  "sig_strike_accuracy": 64.3,
  "td_landed": 3,
  "td_accuracy": 60.0,
  "strikes_per_minute": 5.6,
  "control_time_percentage": 35.2,
  ...
}
```

---

#### 8. Get Career Stats
```bash
GET /api/stats/career/{fighter_id}
```

**Response:**
```json
{
  "fighter_id": "fighter_1",
  "total_fights": 15,
  "total_rounds": 42,
  "sig_strikes_landed": 782,
  "avg_sig_strikes_per_min": 3.7,
  "avg_sig_strike_accuracy": 62.8,
  "avg_td_accuracy": 58.3,
  "avg_control_time_per_fight": 180.5,
  "knockdowns_per_15min": 0.42,
  ...
}
```

---

#### 9. Get All Fight Stats
```bash
GET /api/stats/fight/{fight_id}/all
```

**Response:**
```json
{
  "fight_id": "ufc301_main",
  "fighters": [
    { "fighter_id": "fighter_1", ... },
    { "fighter_id": "fighter_2", ... }
  ],
  "count": 2
}
```

---

### Job Management

#### 10. Get Recent Jobs
```bash
GET /api/stats/jobs?limit=20
```

**Response:**
```json
{
  "jobs": [
    {
      "id": "uuid",
      "job_type": "round",
      "trigger": "manual",
      "fight_id": "ufc301_main",
      "round_num": 1,
      "status": "completed",
      "rows_processed": 2,
      "rows_updated": 2,
      "started_at": "2025-01-01T00:00:00Z",
      "completed_at": "2025-01-01T00:00:05Z"
    }
  ],
  "count": 20
}
```

---

## 🔄 Common Workflows

### Workflow 1: Real-Time Event to Stats

**When a judge logs events during a fight:**

1. Judge logs strike → Event saved to `events` table
2. Round completes → Trigger round aggregation
   ```bash
   POST /api/stats/aggregate/round?fight_id=X&round_num=1&trigger=round_locked
   ```
3. Stats computed and saved to `round_stats`
4. Dashboard queries `round_stats` for display

---

### Workflow 2: Post-Fight Statistics

**After a fight ends:**

1. Fight completes → Trigger fight aggregation
   ```bash
   POST /api/stats/aggregate/fight?fight_id=X&trigger=post_fight
   ```
2. All rounds aggregated → Fight stats computed
3. Stats saved to `fight_stats`
4. Optionally trigger career update:
   ```bash
   POST /api/stats/aggregate/career?fighter_id=Y&trigger=manual
   ```

---

### Workflow 3: Nightly Career Update

**Automated nightly job (runs at 3am UTC):**

1. Scheduler wakes up at configured time
2. Gets all fighters from `fight_stats`
3. For each fighter:
   - Aggregate all their fight stats
   - Compute career averages
   - Save to `career_stats`
4. Job tracked in `aggregation_jobs`

**To start nightly aggregation:**
```python
# In server.py startup
scheduler.start_nightly_aggregation(hour=3)  # 3am UTC
```

---

### Workflow 4: Data Correction

**If events are corrected/deleted:**

1. Fix events in `events` table
2. Trigger full recalculation:
   ```bash
   POST /api/stats/aggregate/full/{fight_id}
   ```
3. System recalculates:
   - All rounds
   - Fight stats
   - Career stats for both fighters

---

## 📐 Database Schema

### round_stats Collection
```javascript
{
  "_id": ObjectId,
  "id": "uuid",
  "fight_id": "ufc301_main",
  "round_num": 1,
  "fighter_id": "fighter_1",
  "total_strikes_attempted": 45,
  "total_strikes_landed": 28,
  "sig_strikes_attempted": 30,
  "sig_strikes_landed": 18,
  "sig_head_landed": 12,
  "sig_body_landed": 4,
  "sig_leg_landed": 2,
  "knockdowns": 1,
  "rocked_events": 0,
  "td_attempts": 2,
  "td_landed": 1,
  "td_stuffed": 1,
  "sub_attempts": 1,
  "ground_control_secs": 45,
  "clinch_control_secs": 20,
  "cage_control_secs": 15,
  "back_control_secs": 30,
  "mount_secs": 15,
  "total_control_secs": 125,
  "computed_at": ISODate,
  "last_updated": ISODate,
  "source_event_count": 67
}

// Index
{fight_id: 1, round_num: 1, fighter_id: 1} unique
```

---

### fight_stats Collection
```javascript
{
  "_id": ObjectId,
  "id": "uuid",
  "fight_id": "ufc301_main",
  "fighter_id": "fighter_1",
  "total_rounds": 3,
  // ... all aggregated stats ...
  "sig_strike_accuracy": 64.3,
  "td_accuracy": 60.0,
  "strikes_per_minute": 5.6,
  "control_time_percentage": 35.2,
  "computed_at": ISODate,
  "last_updated": ISODate,
  "rounds_aggregated": 3
}

// Index
{fight_id: 1, fighter_id: 1} unique
```

---

### career_stats Collection
```javascript
{
  "_id": ObjectId,
  "id": "uuid",
  "fighter_id": "fighter_1",
  "total_fights": 15,
  "total_rounds": 42,
  // ... all aggregated stats ...
  "avg_sig_strikes_per_min": 3.7,
  "avg_sig_strike_accuracy": 62.8,
  "knockdowns_per_15min": 0.42,
  "computed_at": ISODate,
  "last_updated": ISODate,
  "fights_aggregated": 15
}

// Index
{fighter_id: 1} unique
```

---

### aggregation_jobs Collection
```javascript
{
  "_id": ObjectId,
  "id": "uuid",
  "job_type": "round|fight|career|manual",
  "trigger": "manual|round_locked|post_fight|nightly",
  "fight_id": "ufc301_main",
  "round_num": 1,
  "fighter_id": "fighter_1",
  "status": "pending|running|completed|failed",
  "started_at": ISODate,
  "completed_at": ISODate,
  "rows_processed": 2,
  "rows_updated": 2,
  "errors": [],
  "created_at": ISODate
}

// Index
{created_at: -1}
```

---

## ⚡ Performance & Optimization

### Idempotent Operations
All aggregations are **idempotent** - running multiple times produces the same result:
- Uses UPSERT operations
- Safe to retry on failure
- No duplicate stats created

### Batch Processing
For large-scale updates:
```bash
# Aggregate all fighters in a fight
POST /api/stats/aggregate/fight/{fight_id}

# Aggregate all fighters career-wide (nightly)
POST /api/stats/aggregate/career
```

### Query Optimization
Indexes on:
- `round_stats`: (fight_id, round_num, fighter_id)
- `fight_stats`: (fight_id, fighter_id)
- `career_stats`: (fighter_id)

---

## 🛠️ Development & Testing

### Run Tests
```bash
cd /app/backend
pytest tests/test_stat_engine.py -v -s
```

### Manual Testing
```bash
# 1. Check health
curl http://backend-url/api/stats/health

# 2. Aggregate a round
curl -X POST "http://backend-url/api/stats/aggregate/round?fight_id=test_001&round_num=1&trigger=manual"

# 3. Get round stats
curl http://backend-url/api/stats/round/test_001/1/fighter_1

# 4. Full recalculation
curl -X POST http://backend-url/api/stats/aggregate/full/test_001
```

---

## 🚨 Error Handling

### Common Errors

**404 - Stats Not Found**
- No events exist for that fight/round/fighter
- Run aggregation first

**500 - Aggregation Failed**
- Check `aggregation_jobs` for error details
- Verify events table has data
- Check backend logs

**Failed Jobs**
- Query `/api/stats/jobs` to see recent failures
- Check `errors` array in job record
- Retry with full recalculation

---

## 📊 Integration with Frontend

### Display Round Stats
```javascript
// Fetch round stats
const response = await fetch(
  `/api/stats/round/${fightId}/${roundNum}/${fighterId}`
);
const stats = await response.json();

// Display
console.log(`Sig Strikes: ${stats.sig_strikes_landed}`);
console.log(`Knockdowns: ${stats.knockdowns}`);
console.log(`Control Time: ${stats.total_control_secs}s`);
```

### Trigger After Round Lock
```javascript
// When judge locks a round
async function lockRound(fightId, roundNum) {
  // 1. Lock the round (existing functionality)
  await lockRoundInFirebase(fightId, roundNum);
  
  // 2. Trigger stat aggregation
  await fetch(
    `/api/stats/aggregate/round?fight_id=${fightId}&round_num=${roundNum}&trigger=round_locked`,
    { method: 'POST' }
  );
  
  // 3. Display stats
  const stats = await fetchRoundStats(fightId, roundNum, fighterId);
  displayStats(stats);
}
```

---

## ✅ Production Checklist

Before deploying to production:

- [ ] Database indexes created
- [ ] Nightly aggregation scheduled
- [ ] Monitoring setup for failed jobs
- [ ] Frontend integrated with stat endpoints
- [ ] Round-lock triggers configured
- [ ] Post-fight triggers configured
- [ ] Career stats updated nightly
- [ ] Backup strategy for stats tables
- [ ] Error alerting configured

---

## 🎯 Summary

**What It Does:**
- Reads events from judge logging (READ-ONLY)
- Aggregates into round/fight/career statistics
- Provides normalized data for dashboards
- Supports multiple trigger types
- Fault-tolerant with job tracking
- Idempotent operations (safe to retry)

**What It Doesn't Do:**
- Create or modify events
- Replace judge logging
- Real-time event streaming (use existing WebSocket for that)

**Use Cases:**
- Real-time round statistics
- Post-fight analysis
- Fighter career profiles
- Broadcast overlays
- Public fight pages
- Historical data analysis

---

**🥊 Your statistics engine is production-ready!**
