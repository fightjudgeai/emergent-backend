# Supabase Integration Guide

## Overview

This guide will help you set up Supabase as the fight/judgment database for the Emergent backend. Supabase provides a PostgreSQL database with a simple REST/JSON API, perfect for storing fight and judgment data.

## Step 1: Create a Supabase Project

1. Go to https://supabase.com
2. Click **"Start your project"** or sign in if you have an account
3. Create a new organization (or use existing)
4. Click **"New project"**
5. Fill in:
   - **Project Name**: `emergent-fights` (or your choice)
   - **Database Password**: Create a strong password
   - **Region**: Select closest to your location
6. Click **"Create new project"**
7. Wait for the project to be created (2-3 minutes)

## Step 2: Get Your API Credentials

Once your project is ready:

1. Click on **Settings** (bottom left gear icon)
2. Go to **API** tab
3. Copy the following and save them:
   - **Project URL** → `SUPABASE_URL`
   - **anon public** → `SUPABASE_ANON_KEY`
   - **service_role secret** → `SUPABASE_SERVICE_ROLE_KEY`

⚠️ **IMPORTANT**: Keep your service_role key secret! Never commit it to git.

## Step 3: Create Database Tables

In your Supabase project:

1. Click on **SQL Editor** (left sidebar)
2. Click **"New query"**
3. Paste the SQL below:

```sql
-- Create fights table
CREATE TABLE IF NOT EXISTS fights (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  description TEXT NOT NULL,
  user_id TEXT,
  metadata JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create judgments table
CREATE TABLE IF NOT EXISTS judgments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  fight_id UUID NOT NULL REFERENCES fights(id) ON DELETE CASCADE,
  winner TEXT,
  scores JSONB NOT NULL,
  reasoning TEXT,
  ai_model TEXT,
  user_id TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX idx_fights_user_id ON fights(user_id);
CREATE INDEX idx_fights_created_at ON fights(created_at DESC);
CREATE INDEX idx_judgments_fight_id ON judgments(fight_id);
CREATE INDEX idx_judgments_user_id ON judgments(user_id);
CREATE INDEX idx_judgments_created_at ON judgments(created_at DESC);

-- Enable Row Level Security (optional but recommended)
ALTER TABLE fights ENABLE ROW LEVEL SECURITY;
ALTER TABLE judgments ENABLE ROW LEVEL SECURITY;
```

4. Click **"Run"** button
5. You should see `✓` indicators for all queries

## Step 4: Update Backend Configuration

1. Open `.env` in the backend folder
2. Fill in your Supabase credentials:

```env
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_ANON_KEY=your-anon-key-here
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key-here
```

## Step 5: Install Python Supabase Client

The package is already added to `requirements.txt`. Install it:

```powershell
pip install supabase
```

Or reinstall all dependencies:
```powershell
pip install -r requirements.txt --upgrade
```

## Step 6: Initialize Supabase in Your Backend

In your `server.py` or startup code, add:

```python
from supabase_client import init_supabase

@app.on_event("startup")
async def startup_supabase():
    """Initialize Supabase on startup"""
    init_supabase()
    logger.info("✓ Supabase initialized")
```

## Step 7: Use Supabase in Your Routes

Example in your API routes:

```python
from supabase_client import create_fight, get_fight_judgments, create_judgment

@app.post("/api/fights")
async def create_new_fight(description: str, user_id: str):
    """Create a new fight"""
    fight = await create_fight(description, user_id)
    return fight

@app.get("/api/fights/{fight_id}/judgments")
async def get_judgments(fight_id: str):
    """Get all judgments for a fight"""
    judgments = await get_fight_judgments(fight_id)
    return judgments

@app.post("/api/judgments")
async def submit_judgment(
    fight_id: str,
    winner: str,
    scores: dict,
    reasoning: str,
    ai_model: str = None,
    user_id: str = None
):
    """Submit a judgment for a fight"""
    judgment = await create_judgment(
        fight_id=fight_id,
        winner=winner,
        scores=scores,
        reasoning=reasoning,
        ai_model=ai_model,
        user_id=user_id
    )
    return judgment
```

## Available Functions in `supabase_client.py`

### Fights
- `create_fight(description, user_id, metadata)` - Create a new fight
- `get_fight(fight_id)` - Get a specific fight
- `list_fights(user_id, limit)` - List fights (optionally filtered by user)
- `update_fight(fight_id, updates)` - Update a fight

### Judgments
- `create_judgment(fight_id, winner, scores, reasoning, ai_model, user_id)` - Create judgment
- `get_judgment(judgment_id)` - Get a specific judgment
- `get_fight_judgments(fight_id)` - Get all judgments for a fight
- `list_judgments(user_id, limit)` - List judgments
- `update_judgment(judgment_id, updates)` - Update a judgment

### Utilities
- `init_supabase()` - Initialize Supabase clients
- `check_supabase_health()` - Check if Supabase is accessible

## Testing Supabase Connection

After configuring credentials and installing the package:

```python
from supabase_client import init_supabase, check_supabase_health

# Initialize
init_supabase()

# Test health
is_healthy = await check_supabase_health()
print(f"Supabase healthy: {is_healthy}")
```

## Supabase UI Features

In Supabase dashboard, you can:

1. **Browse Data** - Click table name to view all rows
2. **Edit Data** - Click on rows to edit
3. **Run Queries** - SQL Editor tab for custom queries
4. **View Logs** - Database activity in Logs tab
5. **Manage Users** - Auth tab (if you add authentication later)
6. **Setup Backups** - Settings → Backup configuration

## Common Field Formats

### Scores Object
```json
{
  "fighter_a": {"round1": 10, "round2": 9, "round3": 8},
  "fighter_b": {"round1": 9, "round2": 9, "round3": 10},
  "total_fighter_a": 27,
  "total_fighter_b": 28
}
```

### Metadata Object (fights)
```json
{
  "event_name": "Fight Night #1",
  "location": "Texas",
  "fighter_a": "John Doe",
  "fighter_b": "Jane Smith",
  "rules": "MMA"
}
```

## Troubleshooting

### "Invalid API key"
- Check that you copied the full key from Supabase
- Verify no extra spaces in `.env`
- Make sure you're using the right key (anon vs service_role)

### "Table does not exist"
- Run the SQL setup script again
- Check table names are spelled correctly (case-sensitive)
- Verify you're in the right Supabase project

### "Connection refused"
- Check your internet connection
- Verify SUPABASE_URL is correct
- Check if Supabase project is active (not paused)

### "Row level security denied"
- If you enabled RLS, you need to create policies
- Or disable RLS for testing: `ALTER TABLE fights DISABLE ROW LEVEL SECURITY;`

## Security Best Practices

1. **Never commit `.env`** - Add to `.gitignore`
2. **Service role key is secret** - Only use server-side
3. **Anon key for client** - If creating frontend, use this key
4. **RLS policies** - Enable Row Level Security for production
5. **Audit logs** - Supabase logs all queries automatically

## Next Steps

1. ✅ Create Supabase project
2. ✅ Run SQL setup script
3. ✅ Configure `.env`
4. ✅ Install `supabase` package
5. ✅ Initialize in `server.py`
6. ✅ Add routes using `supabase_client.py`
7. ✅ Test with Swagger UI

## Resources

- Supabase Docs: https://supabase.com/docs
- Python Client: https://github.com/supabase-community/supabase-py
- SQL Editor Guide: https://supabase.com/docs/reference/sql
- Row Level Security: https://supabase.com/docs/guides/auth/row-level-security

---

Questions? Check the Supabase docs or the `supabase_client.py` file for all available functions!
