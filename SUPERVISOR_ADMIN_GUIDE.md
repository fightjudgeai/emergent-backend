# Supervisor Admin Panel - Complete Guide
## Stat Recalculation with Audit Logging

---

## 🎯 Overview

The **Supervisor Admin Panel** provides three supervisor-only actions for recalculating statistics with full audit logging and real-time results display.

**All actions are:**
- ✅ **Idempotent** - Safe to run multiple times
- ✅ **Audit Logged** - Every action tracked for compliance
- ✅ **Real-Time** - Returns updated stats immediately
- ✅ **Supervisor-Only** - Protected access

---

## 🔐 Access Control

### Who Can Access:
- **Supervisors** - Full access to all recalculation actions
- **Administrators** - Same as supervisors

### Who Cannot Access:
- **Judges** - View-only access
- **Stat Operators** - Limited to event entry

**Access URL:** `/admin/supervisor` (requires supervisor role)

---

## 🎛️ Three Admin Actions

### BUTTON 1: Recalculate Round Stats

**Purpose:** Recalculate statistics for a specific round

**Inputs:**
- `fight_id` (required) - Fight identifier (e.g., "ufc301_main")
- `round` (required) - Round number (1-12)

**When to Use:**
- After correcting events in a specific round
- When a judge reports incorrect round stats
- After fixing timing issues in events

**What It Does:**
1. Reads all events for the specified fight & round
2. Aggregates strikes, takedowns, control time
3. Computes accuracy, control %, etc.
4. UPSERTs to `round_stats` table
5. Returns updated stats payload

**Example:**
```
fight_id: ufc301_main
round: 1

Result:
✓ Success
- Status: completed
- Updated: 2 fighters
- Sig Strikes: 18
- Knockdowns: 1
- Control: 120s
```

---

### BUTTON 2: Recalculate Fight Stats

**Purpose:** Recalculate statistics for an entire fight

**Inputs:**
- `fight_id` (required) - Fight identifier

**When to Use:**
- After recalculating multiple rounds
- When fight-level stats don't match round totals
- After major event corrections
- For post-fight verification

**What It Does:**
1. Recalculates ALL rounds in the fight first
2. Sums round stats into fight-level totals
3. Computes per-minute rates
4. Computes accuracy percentages
5. UPSERTs to `fight_stats` table
6. Returns stats for all fighters

**Example:**
```
fight_id: ufc301_main

Result:
✓ Success
- Status: completed
- Updated: 2 fighters
- Fighter 1: 3 rounds, 64.3% accuracy
- Fighter 2: 3 rounds, 58.1% accuracy
```

---

### BUTTON 3: Recalculate Career Stats

**Purpose:** Recalculate lifetime career statistics

**Inputs:**
- `fighter_id` (optional) - Specific fighter, or leave empty for ALL

**When to Use:**
- After updating multiple fight stats for a fighter
- For nightly career stat updates
- When a fighter's career stats appear incorrect
- After data migration or fixes

**What It Does:**

**Single Fighter Mode:**
1. Gets all fight stats for the fighter
2. Aggregates into career totals
3. Computes advanced metrics (avg SS/min, KD/15min)
4. Computes career averages
5. UPSERTs to `career_stats` table
6. Returns fighter's career stats

**All Fighters Mode:**
1. Gets list of all fighters with fight stats
2. For each fighter:
   - Aggregates all their fights
   - Computes career metrics
   - Saves to database
3. Returns count of fighters updated

**Example (Single Fighter):**
```
fighter_id: fighter_mcgregor_123

Result:
✓ Success
- Status: completed
- Updated: 1 fighter
- Total Fights: 25
- Avg SS/min: 4.2
- Accuracy: 58.3%
```

**Example (All Fighters):**
```
fighter_id: (empty)

Result:
✓ Success
- Status: completed
- Updated: 250 fighters
- Scope: all fighters
```

---

## 📊 Result Display

Each action shows real-time results:

### Success Result:
```
✓ Success                    [⏰ 10:35:42 AM]

Status: completed
Updated: 2

Round Stats Preview:
- Sig Strikes: 18
- Knockdowns: 1
- TD Landed: 2
- Control: 120s

Job ID: abc123...
```

### Failure Result:
```
✗ Failed                     [⏰ 10:35:42 AM]

Error: Database connection timeout
```

---

## 🔍 Audit Logging

Every action is automatically logged to `audit_logs` collection:

### Audit Log Entry:
```javascript
{
  "action_type": "round_aggregation",
  "trigger": "manual",
  "user": "supervisor_john",
  "timestamp": "2025-01-01T10:35:42Z",
  
  // Scope
  "fight_id": "ufc301_main",
  "round_num": 1,
  "fighter_id": null,
  
  // Result
  "result": {
    "job_id": "abc123...",
    "status": "completed",
    "rows_updated": 2,
    "message": "Round 1 aggregation completed"
  },
  
  // Metadata
  "ip_address": "192.168.1.100",
  "user_agent": "Mozilla/5.0..."
}
```

### View Audit Logs:

**Recent Actions:**
```bash
GET /api/stats/audit-logs?limit=50
```

**By Fight:**
```bash
GET /api/stats/audit-logs/fight/ufc301_main
```

**Response:**
```json
{
  "audit_logs": [
    {
      "action_type": "round_aggregation",
      "trigger": "manual",
      "user": "supervisor_john",
      "timestamp": "2025-01-01T10:35:42Z",
      "fight_id": "ufc301_main",
      "round_num": 1,
      "result": {...}
    }
  ],
  "count": 15
}
```

---

## 🔄 Idempotency Guarantee

All actions are **100% idempotent** - running them multiple times produces the same result.

### How It Works:

**Round Stats:**
```python
# UPSERT by (fight_id, round, fighter_id)
query = {"fight_id": "ufc301", "round": 1, "fighter_id": "fighter1"}
db.round_stats.update_one(query, {"$set": stats}, upsert=True)
```

**Fight Stats:**
```python
# UPSERT by (fight_id, fighter_id)
query = {"fight_id": "ufc301", "fighter_id": "fighter1"}
db.fight_stats.update_one(query, {"$set": stats}, upsert=True)
```

**Career Stats:**
```python
# UPSERT by (fighter_id) - UNIQUE
query = {"fighter_id": "fighter1"}
db.career_stats.update_one(query, {"$set": stats}, upsert=True)
```

**Result:** No matter how many times you click the button, only one record exists per scope.

---

## 📈 Use Cases

### Use Case 1: Fix Incorrect Round Stats

**Scenario:** Judge reports round 2 stats are wrong

**Steps:**
1. Fix the events in Firebase/MongoDB
2. Open Supervisor Admin Panel
3. Click "Recalculate Round Stats"
4. Enter fight_id and round: 2
5. Click button
6. Verify updated stats in result display

**Result:** Round 2 stats now reflect corrected events

---

### Use Case 2: Post-Fight Verification

**Scenario:** Want to verify all stats are correct after a fight

**Steps:**
1. Click "Recalculate Fight Stats"
2. Enter fight_id
3. Click button
4. Review stats for both fighters
5. Compare with live broadcast stats
6. If issues found, drill down to specific rounds

**Result:** Confidence in stat accuracy before publishing

---

### Use Case 3: Nightly Career Updates

**Scenario:** Update all fighters' career stats (automated)

**Steps:**
1. Click "Recalculate Career Stats"
2. Leave fighter_id empty
3. Click button
4. Wait for all fighters to process
5. Review count of fighters updated

**Result:** All career stats updated across the system

---

### Use Case 4: Data Migration

**Scenario:** Imported legacy fight data, need to rebuild stats

**Steps:**
1. For each fight:
   - Recalculate Fight Stats
2. Then:
   - Recalculate Career Stats (all fighters)
3. Verify audit logs show all operations

**Result:** Complete stat rebuild with full audit trail

---

## ⚡ Performance

### Response Times:

**Round Stats:**
- Single round: 100-500ms
- With real-time display: +200ms

**Fight Stats:**
- 3-round fight: 500ms-1s
- 5-round fight: 800ms-2s

**Career Stats:**
- Single fighter: 200-800ms
- All fighters (250): 30-60 seconds

### Optimization Tips:

1. **Round Stats** - Fast, do anytime
2. **Fight Stats** - Medium, do as needed
3. **Career Stats (single)** - Fast, do as needed
4. **Career Stats (all)** - Slow, schedule during off-hours

---

## 🚨 Error Handling

### Common Errors:

**"Fight not found"**
- Check fight_id spelling
- Verify fight exists in events table

**"No events found"**
- Fight has no logged events yet
- Check if events were properly saved

**"Database timeout"**
- High server load
- Retry in a few seconds

**"Validation error"**
- Invalid round number (must be 1-12)
- Missing required field

---

## 🔧 Integration

### Frontend Component:

```jsx
import SupervisorAdminPanel from '@/components/SupervisorAdminPanel';

// In your admin route
<Route path="/admin/supervisor" element={<SupervisorAdminPanel />} />
```

### API Endpoints:

```bash
# Recalculate round
POST /api/stats/aggregate/round?fight_id=X&round_num=Y&trigger=manual

# Recalculate fight
POST /api/stats/aggregate/fight?fight_id=X&trigger=manual

# Recalculate career (single)
POST /api/stats/aggregate/career?fighter_id=X&trigger=manual

# Recalculate career (all)
POST /api/stats/aggregate/career?trigger=manual

# Get audit logs
GET /api/stats/audit-logs?limit=50
GET /api/stats/audit-logs/fight/{fight_id}
```

---

## 📊 Monitoring

### Audit Log Dashboard:

Create a dashboard to monitor supervisor actions:

```sql
-- Most active supervisors
SELECT user, COUNT(*) as actions
FROM audit_logs
GROUP BY user
ORDER BY actions DESC

-- Recent recalculations
SELECT action_type, fight_id, timestamp
FROM audit_logs
ORDER BY timestamp DESC
LIMIT 50

-- Failed actions
SELECT *
FROM audit_logs
WHERE result.status = 'failed'
```

---

## ✅ Best Practices

### For Supervisors:

1. **Verify Before Recalculating**
   - Check if stats actually need recalculation
   - Review what changed in events

2. **Use Smallest Scope**
   - Fix one round? Use Round Stats
   - Fix multiple rounds? Use Fight Stats
   - Don't recalculate career unless needed

3. **Document Reason**
   - Add comment in audit log
   - Note ticket number if applicable

4. **Verify Results**
   - Check the real-time display
   - Compare before/after values
   - Validate against expected values

5. **Monitor Audit Logs**
   - Periodically review who's doing what
   - Look for suspicious patterns
   - Ensure compliance

### For Developers:

1. **Never Bypass Audit Logging**
   - Always use the API endpoints
   - Don't write directly to stat tables

2. **Add Context to Logs**
   - Include user info if available
   - Log IP address and user agent
   - Add custom metadata fields

3. **Monitor Performance**
   - Track aggregation times
   - Alert on slow operations
   - Optimize queries as needed

4. **Test Idempotency**
   - Run actions multiple times
   - Verify results are identical
   - Check no duplicates created

---

## 📚 Summary

**Supervisor Admin Panel Features:**
- ✅ 3 recalculation actions (Round/Fight/Career)
- ✅ Real-time result display
- ✅ Full audit logging
- ✅ Idempotent operations
- ✅ Error handling
- ✅ Supervisor-only access
- ✅ Production-ready

**Use for:**
- Fixing incorrect stats
- Post-fight verification
- Nightly career updates
- Data migration
- Compliance audits

**System is production-ready for supervisor stat management!**
