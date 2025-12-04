# Run Fantasy Scoring Migration

## Step 1: Open Supabase SQL Editor

https://supabase.com/dashboard/project/yymuzbgipozkaxqabtxb/sql/new

## Step 2: Copy and Run Migration SQL

Copy the entire contents of this file:
```
/app/datafeed_api/migrations/002_fantasy_scoring.sql
```

Or copy the SQL below:

---

**COPY FROM HERE** ⬇️

```sql
[See the file /app/datafeed_api/migrations/002_fantasy_scoring.sql]
```

**TO HERE** ⬆️

---

## Step 3: Verify Tables Created

Run this query to verify:

```sql
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
  AND table_name IN ('fantasy_scoring_profiles', 'fantasy_fight_stats')
ORDER BY table_name;
```

You should see:
- fantasy_fight_stats
- fantasy_scoring_profiles

## Step 4: Verify Profiles Created

```sql
SELECT id, name FROM fantasy_scoring_profiles ORDER BY id;
```

You should see 3 profiles:
1. fantasy.basic
2. fantasy.advanced
3. sportsbook.pro

## Step 5: Test Fantasy Calculation

Calculate fantasy points for a fighter:

```sql
SELECT * FROM calculate_fantasy_points(
    (SELECT id FROM fights WHERE code = 'PFC50-F1'),
    (SELECT red_fighter_id FROM fights WHERE code = 'PFC50-F1'),
    'fantasy.basic'
);
```

This should return fantasy points and breakdown!

---

## After Migration Complete

Reply with: **"Migration done"** and I'll restart the API server to activate the fantasy endpoints.
