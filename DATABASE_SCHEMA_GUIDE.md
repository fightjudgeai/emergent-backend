# Production Database Schema Guide
## Complete Reference for All Tables, Relations & Indexes

---

## 🎯 Overview

Production-grade database schema with 5 main tables, 30+ indexes, and proper UPSERT-safe design for MongoDB.

**Tables:**
1. **fighters** - Fighter biographical and physical data
2. **events** - Individual fight events logged during rounds
3. **round_stats** - Aggregated per-round statistics
4. **fight_stats** - Aggregated per-fight statistics
5. **career_stats** - Lifetime aggregated statistics

**Total Indexes:** 28 (automatically created on startup)

---

## 📋 Table Schemas

### 1. fighters TABLE

**Purpose:** Store fighter profiles with biographical, physical, and record data

**Schema:**
```javascript
{
  "id": "uuid",  // Primary key
  "name": "string",  // Full name (REQUIRED)
  "nickname": "string | null",  // Fighter nickname
  "gym": "string | null",  // Training gym
  "record": "string | null",  // "W-L-D" format (e.g., "25-3-0")
  
  // Physical Attributes
  "division": "enum | null",  // Weight division
  "height_cm": "float | null",  // Height in centimeters
  "reach_cm": "float | null",  // Reach in centimeters
  "stance": "enum | null",  // orthodox | southpaw | switch
  
  // Metadata
  "created_at": "ISODate",
  "updated_at": "ISODate"
}
```

**Enums:**
- **division**: Flyweight, Bantamweight, Featherweight, Lightweight, Welterweight, Middleweight, Light Heavyweight, Heavyweight, Women's Strawweight, Women's Flyweight, Women's Bantamweight, Women's Featherweight
- **stance**: orthodox, southpaw, switch

**Indexes (5):**
1. `idx_fighters_id` - UNIQUE on (id)
2. `idx_fighters_name_text` - TEXT search on (name)
3. `idx_fighters_division` - on (division)
4. `idx_fighters_gym` - on (gym)
5. `idx_fighters_created_at` - on (created_at DESC)

**Example:**
```json
{
  "id": "fighter_mcgregor_123",
  "name": "Conor McGregor",
  "nickname": "The Notorious",
  "gym": "SBG Ireland",
  "record": "22-6-0",
  "division": "Lightweight",
  "height_cm": 175,
  "reach_cm": 188,
  "stance": "southpaw",
  "created_at": "2025-01-01T00:00:00Z",
  "updated_at": "2025-01-01T00:00:00Z"
}
```

---

### 2. events TABLE

**Purpose:** Store individual fight events logged during rounds (source of truth)

**Schema:**
```javascript
{
  "id": "uuid",  // Primary key
  
  // Relations
  "fight_id": "string",  // References bout/fight (REQUIRED)
  "fighter_id": "string",  // References fighters.id (REQUIRED)
  
  // Timing
  "round": "int",  // Round number 1-12 (REQUIRED)
  "timestamp_in_round": "float",  // Seconds into round 0-300 (REQUIRED)
  
  // Event Details
  "event_type": "string",  // Event type (REQUIRED)
  
  // Context
  "position": "enum | null",  // distance | clinch | ground
  "target": "enum | null",  // head | body | leg (for strikes)
  "source": "enum",  // judge_software | stat_operator | ai_cv | hybrid
  
  // Additional Data
  "metadata": {
    "significant": "bool",  // For strikes
    "landed": "bool",  // For strikes/takedowns
    "tier": "string",  // For KD: flash | hard | near_finish
    "depth": "string",  // For submissions
    "duration": "int",  // For control events (seconds)
    "type": "string"  // start | stop (for control)
  },
  
  // Metadata
  "created_at": "ISODate"
}
```

**Enums:**
- **position**: distance, clinch, ground
- **target**: head, body, leg
- **source**: judge_software, stat_operator, ai_cv, hybrid

**Event Types (examples):**
- Strikes: "Head Kick", "Body Kick", "Low Kick", "Elbow", "Knee", "Hook", "Cross", "Jab", "Uppercut"
- Damage: "KD", "Rocked/Stunned"
- Grappling: "Takedown Landed", "Takedown Stuffed", "Submission Attempt", "Sweep/Reversal"
- Control: "Ground Top Control", "Ground Back Control", "Cage Control Time"

**Indexes (7):**
1. `idx_events_fight_round_timestamp` - on (fight_id, round, timestamp_in_round)
2. `idx_events_fighter_id` - on (fighter_id)
3. `idx_events_fight_fighter` - on (fight_id, fighter_id)
4. `idx_events_event_type` - on (event_type)
5. `idx_events_source` - on (source)
6. `idx_events_created_at` - on (created_at DESC)
7. `idx_events_aggregation` - on (fight_id, round, fighter_id, event_type)

**Example:**
```json
{
  "id": "event_12345",
  "fight_id": "ufc301_main",
  "fighter_id": "fighter_mcgregor_123",
  "round": 1,
  "timestamp_in_round": 45.5,
  "event_type": "Head Kick",
  "position": "distance",
  "target": "head",
  "source": "judge_software",
  "metadata": {
    "significant": true,
    "landed": true
  },
  "created_at": "2025-01-01T00:05:45Z"
}
```

---

### 3. round_stats TABLE

**Purpose:** Aggregated statistics for each fighter in each round

**Schema:**
```javascript
{
  "id": "uuid",
  
  // Relations (UNIQUE together)
  "fight_id": "string",
  "round": "int",
  "fighter_id": "string",  // References fighters.id
  
  // Strike Statistics
  "total_strikes_attempted": "int",
  "total_strikes_landed": "int",
  "sig_strikes_attempted": "int",
  "sig_strikes_landed": "int",
  
  // Sig Strikes by Target
  "sig_head_attempted": "int",
  "sig_head_landed": "int",
  "sig_body_attempted": "int",
  "sig_body_landed": "int",
  "sig_leg_attempted": "int",
  "sig_leg_landed": "int",
  
  // Sig Strikes by Position
  "sig_distance_attempted": "int",
  "sig_distance_landed": "int",
  "sig_clinch_attempted": "int",
  "sig_clinch_landed": "int",
  "sig_ground_attempted": "int",
  "sig_ground_landed": "int",
  
  // Power Strikes
  "knockdowns": "int",
  "knockdown_tiers": {  // Breakdown by severity
    "flash": "int",
    "hard": "int",
    "near_finish": "int"
  },
  "rocked_events": "int",
  
  // Takedown Statistics
  "td_attempts": "int",
  "td_landed": "int",
  "td_stuffed": "int",
  
  // Submission Attempts
  "sub_attempts": "int",
  "sub_attempts_by_type": {  // Breakdown by submission type
    "armbar": "int",
    "guillotine": "int",
    "rear_naked_choke": "int"
  },
  
  // Control Time (seconds)
  "ground_control_secs": "int",
  "clinch_control_secs": "int",
  "cage_control_secs": "int",
  "back_control_secs": "int",
  "mount_secs": "int",
  "total_control_secs": "int",
  
  // Position Time (seconds)
  "distance_time_secs": "int",
  "clinch_time_secs": "int",
  "ground_time_secs": "int",
  
  // Computed Metrics (cached)
  "sig_strike_accuracy": "float",  // percentage
  "sig_strike_defense": "float",  // percentage
  "td_accuracy": "float",  // percentage
  "control_time_percentage": "float",  // of 300 seconds
  
  // Metadata
  "source_event_count": "int",  // Number of events processed
  "computed_at": "ISODate",
  "created_at": "ISODate",
  "updated_at": "ISODate"
}
```

**Indexes (5):**
1. `idx_round_stats_unique` - UNIQUE on (fight_id, round, fighter_id)
2. `idx_round_stats_fighter_id` - on (fighter_id)
3. `idx_round_stats_fight_id` - on (fight_id)
4. `idx_round_stats_fight_round` - on (fight_id, round)
5. `idx_round_stats_updated_at` - on (updated_at DESC)

**Example:**
```json
{
  "id": "round_stat_123",
  "fight_id": "ufc301_main",
  "round": 1,
  "fighter_id": "fighter_mcgregor_123",
  "sig_strikes_landed": 18,
  "sig_head_landed": 12,
  "sig_body_landed": 4,
  "sig_leg_landed": 2,
  "knockdowns": 1,
  "total_control_secs": 120,
  "sig_strike_accuracy": 64.3,
  "source_event_count": 67,
  "updated_at": "2025-01-01T00:10:00Z"
}
```

---

### 4. fight_stats TABLE

**Purpose:** Aggregated statistics for entire fights (sum of all rounds)

**Schema:**
```javascript
{
  "id": "uuid",
  
  // Relations (UNIQUE together)
  "fight_id": "string",
  "fighter_id": "string",  // References fighters.id
  
  // Fight Metadata
  "total_rounds": "int",
  "fight_duration_secs": "int",  // Total seconds fought
  
  // All strike/grappling stats (same as round_stats but aggregated)
  "sig_strikes_landed": "int",
  "knockdowns": "int",
  "td_landed": "int",
  "total_control_secs": "int",
  // ... (all fields from round_stats)
  
  // Computed Metrics
  "sig_strike_accuracy": "float",  // percentage
  "td_accuracy": "float",  // percentage
  "control_time_percentage": "float",  // of total fight time
  
  // Per-Minute Rates
  "sig_strikes_per_minute": "float",
  "total_strikes_per_minute": "float",
  "td_per_15min": "float",
  
  // Metadata
  "rounds_aggregated": "int",
  "computed_at": "ISODate",
  "created_at": "ISODate",
  "updated_at": "ISODate"
}
```

**Indexes (5):**
1. `idx_fight_stats_unique` - UNIQUE on (fight_id, fighter_id)
2. `idx_fight_stats_fighter_id` - on (fighter_id)
3. `idx_fight_stats_fight_id` - on (fight_id)
4. `idx_fight_stats_updated_at` - on (updated_at DESC)
5. `idx_fight_stats_performance` - on (sig_strikes_landed DESC, knockdowns DESC)

---

### 5. career_stats TABLE

**Purpose:** Lifetime aggregated statistics across all fights

**Schema:**
```javascript
{
  "id": "uuid",
  
  // Relations (UNIQUE)
  "fighter_id": "string",  // References fighters.id - UNIQUE
  
  // Career Summary
  "total_fights": "int",
  "total_rounds": "int",
  "total_fight_time_secs": "int",
  
  // Win/Loss
  "wins": "int",
  "losses": "int",
  "draws": "int",
  
  // All lifetime stats (same structure as fight_stats)
  "sig_strikes_landed": "int",
  "knockdowns": "int",
  // ... (all aggregated lifetime stats)
  
  // Advanced Career Metrics
  "avg_sig_strike_accuracy": "float",
  "avg_td_accuracy": "float",
  "avg_sig_strikes_per_min": "float",
  "knockdowns_per_15min": "float",
  "avg_control_time_per_fight": "float",
  
  // Derived JSON (custom metrics)
  "derived_metrics": {
    "finish_rate": "float",
    "ko_rate": "float",
    "submission_rate": "float",
    "early_pressure_rate": "float"
  },
  
  // Metadata
  "fights_aggregated": "int",
  "last_fight_date": "ISODate | null",
  "computed_at": "ISODate",
  "created_at": "ISODate",
  "updated_at": "ISODate"
}
```

**Indexes (6):**
1. `idx_career_stats_unique` - UNIQUE on (fighter_id)
2. `idx_career_stats_updated_at` - on (updated_at DESC)
3. `idx_career_stats_total_fights` - on (total_fights DESC)
4. `idx_career_stats_sig_strikes_leader` - on (avg_sig_strikes_per_min DESC)
5. `idx_career_stats_kd_leader` - on (knockdowns_per_15min DESC)
6. `idx_career_stats_accuracy_leader` - on (avg_sig_strike_accuracy DESC)

---

## 🔗 Relations & Foreign Keys

### Relationships:

```
fighters (1) ──────< (many) events
fighters (1) ──────< (many) round_stats
fighters (1) ──────< (many) fight_stats
fighters (1) ──────── (1) career_stats

fight_id ──────< (many) events
fight_id ──────< (many) round_stats
fight_id ──────< (many) fight_stats
```

**Key Relations:**
- `events.fighter_id` → `fighters.id`
- `round_stats.fighter_id` → `fighters.id`
- `fight_stats.fighter_id` → `fighters.id`
- `career_stats.fighter_id` → `fighters.id` (UNIQUE)

---

## 🔒 UPSERT-Safe Design

All aggregation tables use **UPSERT** operations to ensure idempotency:

### round_stats:
```python
query = {"fight_id": X, "round": Y, "fighter_id": Z}
db.round_stats.update_one(query, {"$set": stats}, upsert=True)
```

### fight_stats:
```python
query = {"fight_id": X, "fighter_id": Y}
db.fight_stats.update_one(query, {"$set": stats}, upsert=True)
```

### career_stats:
```python
query = {"fighter_id": X}
db.career_stats.update_one(query, {"$set": stats}, upsert=True)
```

**Benefit:** Running aggregation multiple times is safe and will not create duplicates.

---

## 📊 Index Performance Guide

### Query Patterns & Indexes:

**1. Get all events for a fight, sorted by time:**
```javascript
// Uses: idx_events_fight_round_timestamp
db.events.find({fight_id: "ufc301", round: 1}).sort({timestamp_in_round: 1})
```

**2. Get round stats for a specific fighter:**
```javascript
// Uses: idx_round_stats_unique
db.round_stats.findOne({fight_id: "ufc301", round: 1, fighter_id: "fighter_123"})
```

**3. Get all fights for a fighter:**
```javascript
// Uses: idx_fight_stats_fighter_id
db.fight_stats.find({fighter_id: "fighter_123"})
```

**4. Get career stats:**
```javascript
// Uses: idx_career_stats_unique
db.career_stats.findOne({fighter_id: "fighter_123"})
```

**5. Leaderboard - Top strikers:**
```javascript
// Uses: idx_career_stats_sig_strikes_leader
db.career_stats.find().sort({avg_sig_strikes_per_min: -1}).limit(10)
```

---

## 🚀 API Endpoints

### Database Management:

```bash
# Health check
GET /api/database/health

# Initialize database (create indexes)
POST /api/database/initialize?force_recreate_indexes=false

# Get all indexes
GET /api/database/indexes

# Recreate indexes (caution!)
POST /api/database/indexes/recreate

# Get collection counts
GET /api/database/collections
```

### Example Response:
```json
{
  "status": "healthy",
  "database_name": "fightjudge_prod",
  "collections": {
    "fighters": 250,
    "events": 125000,
    "round_stats": 3500,
    "fight_stats": 1200,
    "career_stats": 250
  },
  "indexes": {
    "fighters": 5,
    "events": 7,
    "round_stats": 5,
    "fight_stats": 5,
    "career_stats": 6
  },
  "total_documents": 130200
}
```

---

## 🔧 Maintenance

### On Application Startup:

The database automatically:
1. Creates all collections if they don't exist
2. Creates all 28 indexes
3. Verifies index creation
4. Logs collection counts

**Backend logs will show:**
```
🚀 Initializing MongoDB with production schemas...
✅ Created 5 indexes for fighters
✅ Created 7 indexes for events
✅ Created 5 indexes for round_stats
✅ Created 5 indexes for fight_stats
✅ Created 6 indexes for career_stats
✓ MongoDB initialized with production schemas
  Collections: 5
  Total indexes: 28
```

### Manual Index Recreation:

If indexes need to be recreated (after schema changes):

```bash
curl -X POST http://backend-url/api/database/indexes/recreate
```

**⚠️ Warning:** This will temporarily impact query performance during recreation.

---

## 📈 Performance Characteristics

### Index Sizes (estimated):

- **fighters**: ~1MB per 10,000 fighters
- **events**: ~50MB per 1 million events (largest table)
- **round_stats**: ~5MB per 10,000 rounds
- **fight_stats**: ~2MB per 10,000 fights
- **career_stats**: ~1MB per 10,000 fighters

### Query Performance:

With proper indexes:
- Single event lookup: <1ms
- Round stats retrieval: <1ms
- Fight stats retrieval: <1ms
- Career stats retrieval: <1ms
- Event aggregation (100 events): 5-10ms
- Leaderboard queries: 10-50ms

---

## 🎓 Best Practices

### 1. Always Use Indexes
```python
# ✅ Good - Uses index
db.events.find({"fight_id": "ufc301", "round": 1})

# ❌ Bad - No index on random field
db.events.find({"metadata.custom_field": "value"})
```

### 2. UPSERT for Idempotency
```python
# ✅ Good - Safe to run multiple times
db.round_stats.update_one(query, {"$set": stats}, upsert=True)

# ❌ Bad - Creates duplicates
db.round_stats.insert_one(stats)
```

### 3. Use Projections
```python
# ✅ Good - Only fetch needed fields
db.fighters.find({}, {"name": 1, "division": 1})

# ❌ Bad - Fetches all fields
db.fighters.find({})
```

### 4. Batch Operations
```python
# ✅ Good - Bulk insert
db.events.insert_many(event_list)

# ❌ Bad - Individual inserts
for event in event_list:
    db.events.insert_one(event)
```

---

## 📚 Summary

**Production Database Features:**
- ✅ 5 production tables with proper schemas
- ✅ 28 optimized indexes for query performance
- ✅ UPSERT-safe design for idempotency
- ✅ Proper foreign key relations
- ✅ Automatic initialization on startup
- ✅ Management API for health checks
- ✅ Enums for type safety
- ✅ Pydantic validation
- ✅ MongoDB-optimized queries

**Ready for production deployment!**
