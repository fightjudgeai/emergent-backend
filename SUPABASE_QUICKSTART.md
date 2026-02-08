# Supabase Integration - Quick Start

## ✅ What's Ready

- ✅ `supabase_client.py` - Supabase database client
- ✅ `supabase_routes.py` - FastAPI routes for fights & judgments
- ✅ `SUPABASE_SETUP.md` - Complete setup guide
- ✅ Supabase Python package installed
- ✅ `.env` configured with placeholders

## 📋 Quick Setup Steps

### 1. Create Supabase Project

1. Go to https://supabase.com
2. Click "Start your project"
3. Create new project (choose region, set password)
4. Wait for project to be created (~3 minutes)

### 2. Get API Credentials

1. In Supabase: Settings → API
2. Copy these three values:
   - **Project URL** → `SUPABASE_URL`
   - **anon public** → `SUPABASE_ANON_KEY`
   - **service_role secret** → `SUPABASE_SERVICE_ROLE_KEY`

### 3. Create Database Tables

In Supabase SQL Editor, run this script:

```sql
-- Fights table
CREATE TABLE IF NOT EXISTS fights (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  description TEXT NOT NULL,
  user_id TEXT,
  metadata JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Judgments table
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

-- Indexes
CREATE INDEX idx_fights_user_id ON fights(user_id);
CREATE INDEX idx_fights_created_at ON fights(created_at DESC);
CREATE INDEX idx_judgments_fight_id ON judgments(fight_id);
CREATE INDEX idx_judgments_user_id ON judgments(user_id);
CREATE INDEX idx_judgments_created_at ON judgments(created_at DESC);
```

### 4. Update `.env` File

Edit `c:\Users\ericg\Downloads\emergent-backend\backend\.env`:

```env
MONGO_URL=mongodb://localhost:27017
DB_NAME=emergent_test

# Supabase Configuration
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_ANON_KEY=eyJhbGc...(your-full-anon-key-here)
SUPABASE_SERVICE_ROLE_KEY=eyJhbGc...(your-full-service-role-key-here)
```

### 5. Integrate Routes into Server

Edit `server.py` and add these imports at the top (after other imports):

```python
from supabase_client import init_supabase
from supabase_routes import get_supabase_router
```

Then in your app setup (around line 82 where app is created), add:

```python
# Include Supabase routes
supabase_router = get_supabase_router()
app.include_router(supabase_router)
```

And in the startup events section, add:

```python
@app.on_event("startup")
async def startup_supabase():
    """Initialize Supabase on startup"""
    init_supabase()
    logger.info("✓ Supabase initialized")
```

### 6. Test the Integration

Once your backend is running, test the new Supabase endpoints:

**Visit API docs:**
```
http://localhost:8000/docs
```

Look for `/api/supabase/*` endpoints - you should see:
- POST `/api/supabase/fights` - Create fight
- GET `/api/supabase/fights` - List fights
- GET `/api/supabase/fights/{id}` - Get fight details
- POST `/api/supabase/judgments` - Submit judgment
- GET `/api/supabase/fights/{id}/judgments` - Get fight's judgments
- And more...

**Test with curl:**
```powershell
# Create a fight (open new terminal while server is running)
$body = @{
    description = "Test Fight"
    user_id = "user123"
    metadata = @{ event = "Test Event" }
} | ConvertTo-Json

Invoke-WebRequest -Uri http://localhost:8000/api/supabase/fights `
  -Method POST `
  -Headers @{ "Content-Type" = "application/json" } `
  -Body $body
```

## 📁 Files Created

```
backend/
├── supabase_client.py       ← Database client functions
├── supabase_routes.py       ← FastAPI routes (add to server.py)
├── SUPABASE_SETUP.md        ← Detailed setup guide
├── requirements.txt         ← Updated with supabase package
└── .env                     ← Updated with Supabase placeholders
```

## 🔗 Available Endpoints

### Fights
| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/supabase/fights` | Create fight |
| GET | `/api/supabase/fights` | List fights |
| GET | `/api/supabase/fights/{id}` | Get fight |
| PUT | `/api/supabase/fights/{id}` | Update fight |

### Judgments
| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/supabase/judgments` | Submit judgment |
| GET | `/api/supabase/judgments` | List judgments |
| GET | `/api/supabase/judgments/{id}` | Get judgment |
| GET | `/api/supabase/fights/{id}/judgments` | Get fight's judgments |
| PUT | `/api/supabase/judgments/{id}` | Update judgment |

### Analytics
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/supabase/stats/fights` | Fight statistics |
| GET | `/api/supabase/stats/judgments` | Judgment statistics |

## 🚀 Example Usage

### Create a Fight
```python
from supabase_client import create_fight

fight = await create_fight(
    description="UFC 300: Main Event",
    user_id="judge_001",
    metadata={
        "event": "UFC 300",
        "fighter_a": "Anderson Silva",
        "fighter_b": "Israel Adesanya",
        "location": "Madison Square Garden"
    }
)
print(fight)
```

### Submit a Judgment
```python
from supabase_client import create_judgment

judgment = await create_judgment(
    fight_id="550e8400-e29b-41d4-a716-446655440000",
    winner="Anderson Silva",
    scores={
        "round1": {"anderson": 10, "israel": 9},
        "round2": {"anderson": 9, "israel": 10},
        "round3": {"anderson": 10, "israel": 9}
    },
    reasoning="Anderson dominated with superior striking in rounds 1 and 3",
    ai_model="ICVSS-v2",
    user_id="judge_001"
)
print(judgment)
```

### Get Fight Judgments
```python
from supabase_client import get_fight_judgments

judgments = await get_fight_judgments("550e8400-e29b-41d4-a716-446655440000")
for j in judgments:
    print(f"Winner: {j['winner']}, Judge: {j.get('user_id')}")
```

## 🔐 Security Notes

- **`.env` is ignored by git** - Keep credentials safe
- **Service role key is secret** - Never expose in frontend
- **Use anon key for client-side** - If building frontend
- **Enable RLS policies** - For production security

## 📚 Documentation

For detailed information, see:
- `SUPABASE_SETUP.md` - Complete setup and troubleshooting
- `supabase_client.py` - All available functions with docstrings
- `supabase_routes.py` - All FastAPI endpoints with examples
- https://supabase.com/docs - Official Supabase documentation

## ✨ Next Steps

1. ✅ Create Supabase project
2. ✅ Run SQL setup script
3. ✅ Update `.env`
4. ✅ Add imports to `server.py`
5. ✅ Add `init_supabase()` call
6. ✅ Include `supabase_router`
7. ✅ Restart backend: `.\run_backend.ps1`
8. ✅ Test endpoints at http://localhost:8000/docs

**Your fights and judgments database is ready!** 🎉
