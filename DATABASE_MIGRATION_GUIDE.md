# 🚨 CRITICAL: Database Migration Guide

## Status: PENDING USER ACTION - BLOCKING ALL BACKEND FEATURES

### Why This is Critical
All new backend features developed in recent sessions are **completely non-functional** because the required database tables, columns, and functions do not exist in your Supabase database. This includes:

- ❌ API Key Authentication System
- ❌ Public Stats API (`/api/public/fight/{id}`, `/api/public/fighter/{id}`)
- ❌ WebSocket JWT Authentication
- ❌ Usage & Billing Metering
- ❌ Admin Control Panel
- ❌ Security Audit Logging
- ❌ Emergency Kill-Switch

**Without running these migrations, attempting to use any of these features will result in "Internal server error" or database errors.**

---

## Migration Files to Run (In Order)

You need to run **8 SQL migration scripts** in your Supabase SQL Editor. They are located at:
```
/app/datafeed_api/migrations/
```

### Required Migrations:
1. `001_initial_schema.sql` - ⚠️ May already be applied (base tables)
2. `002_fantasy_scoring.sql` - Fantasy points system
3. `003_fantasy_auto_triggers.sql` - Auto-calculation triggers
4. `004_sportsbook_markets.sql` - Betting markets
5. `005_stat_engine_normalization.sql` - Event stream normalization
6. `006_api_key_system.sql` - **CRITICAL** API authentication
7. `007_websocket_auth_billing.sql` - **CRITICAL** WebSocket auth & billing
8. `008_security_audit_killswitch.sql` - **CRITICAL** Security features

---

## Step-by-Step Instructions

### Step 1: Access Supabase SQL Editor
1. Go to https://supabase.com
2. Select your project
3. Navigate to **SQL Editor** (in left sidebar)

### Step 2: Run Migrations One by One

**IMPORTANT**: Run them **in order** (001 → 008). Some migrations depend on earlier ones.

For each migration file:

1. **Open the migration file** on this system:
   ```bash
   cat /app/datafeed_api/migrations/001_initial_schema.sql
   ```

2. **Copy the entire SQL content**

3. **Paste into Supabase SQL Editor**

4. **Click "Run"** (bottom right)

5. **Verify success** - Look for:
   - ✅ "Success. No rows returned" (for DDL statements)
   - ✅ Green success banner
   - ❌ If you see red error, **STOP** and report the error

6. **Repeat for next migration**

### Step 3: Check Which Migrations Are Already Applied

Before starting, check which tables already exist:

```sql
-- Run this in Supabase SQL Editor
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
ORDER BY table_name;
```

**Compare the output with expected tables:**

| Migration File | Creates These Tables |
|---------------|----------------------|
| 001 | `events`, `fantasy_profiles`, `market_types`, `odds_movements` |
| 002 | Adds fantasy scoring columns |
| 003 | Creates triggers (no new tables) |
| 004 | `sportsbook_markets`, `market_settlements` |
| 005 | `stat_events_normalized` |
| 006 | **`api_clients`** |
| 007 | **`api_usage_logs`, `billing_usage`** |
| 008 | **`security_audit_log`, `system_killswitch`** |

**If you see `api_clients`, `api_usage_logs`, `billing_usage`, `security_audit_log` tables**, then migrations 006-008 are already applied.

**If these tables are missing**, you MUST run migrations 006-008.

---

## Quick Verification After Migrations

Run this query to confirm the critical tables exist:

```sql
-- Check for API Key tables
SELECT EXISTS (
    SELECT FROM information_schema.tables 
    WHERE table_schema = 'public' 
    AND table_name = 'api_clients'
) as api_clients_exists,
EXISTS (
    SELECT FROM information_schema.tables 
    WHERE table_schema = 'public' 
    AND table_name = 'api_usage_logs'
) as usage_logs_exists,
EXISTS (
    SELECT FROM information_schema.tables 
    WHERE table_schema = 'public' 
    AND table_name = 'security_audit_log'
) as security_log_exists;
```

**Expected result after successful migration:**
```
api_clients_exists | usage_logs_exists | security_log_exists
true               | true              | true
```

---

## What Happens Next?

After you confirm migrations are complete:

1. **I will restart the datafeed_api service**
2. **I will run comprehensive backend testing** using the backend testing agent
3. **Fix any issues found during testing**
4. **Verify all features are working**

---

## Common Issues & Solutions

### Issue: "relation already exists"
**Solution**: That table is already created. Skip that specific CREATE TABLE statement or the entire migration if all its tables exist.

### Issue: "syntax error near..."
**Solution**: Make sure you copied the ENTIRE file content. SQL scripts often have dependencies between statements.

### Issue: "permission denied"
**Solution**: Ensure you're logged in as the project owner in Supabase. Only owners can run DDL statements.

---

## Need Help?

If you encounter any errors during migration:
1. **Copy the exact error message**
2. **Note which migration file caused it**
3. **Share with me** and I'll help debug

---

## Files Reference

All migration files are in: `/app/datafeed_api/migrations/`

To view any file:
```bash
cat /app/datafeed_api/migrations/006_api_key_system.sql
```

Or view all files:
```bash
ls -la /app/datafeed_api/migrations/
```
