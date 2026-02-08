# Supabase Integration Complete! 🎉

## What's Been Set Up

### New Files Created:
1. **`supabase_client.py`** - Python client for Supabase database
   - Functions to create/read/update fights and judgments
   - Health checks and error handling
   
2. **`supabase_routes.py`** - FastAPI routes using Supabase
   - 12+ REST endpoints for fights and judgments
   - Analytics endpoints
   - Full CRUD operations
   
3. **`SUPABASE_SETUP.md`** - Complete setup guide
   - Step-by-step Supabase project creation
   - SQL schema setup
   - Troubleshooting

4. **`SUPABASE_QUICKSTART.md`** - Quick reference
   - Fast setup in 6 steps
   - Example code
   - Endpoint reference

### Updated Files:
- **`.env`** - Added Supabase credential placeholders
- **`requirements.txt`** - Added `supabase==2.4.2` package
- **Supabase package installed** - Python client ready to use

## Next Steps (5 Minutes)

### Step 1: Create Supabase Project
1. Go to https://supabase.com
2. Click "Start your project"
3. Create new project (name: "emergent" or similar)
4. Wait 2-3 minutes for project to be created

### Step 2: Get Credentials
1. Click **Settings** → **API**
2. Copy these three values to `.env`:
   - `SUPABASE_URL` = Project URL
   - `SUPABASE_ANON_KEY` = anon public
   - `SUPABASE_SERVICE_ROLE_KEY` = service_role secret

### Step 3: Create Tables
1. In Supabase: **SQL Editor** → **New query**
2. Paste SQL from `SUPABASE_SETUP.md` (Full SQL script in Step 3)
3. Click **Run**

### Step 4: Update Backend
Open `server.py` and find these sections:

**At the top (with other imports):**
```python
from supabase_client import init_supabase
from supabase_routes import get_supabase_router
```

**Where `app = FastAPI()` is defined (add after):**
```python
# Include Supabase routes
supabase_router = get_supabase_router()
app.include_router(supabase_router)
```

**In the `@app.on_event("startup")` section (add new function):**
```python
@app.on_event("startup")
async def startup_supabase():
    """Initialize Supabase on startup"""
    init_supabase()
    logger.info("✓ Supabase initialized")
```

### Step 5: Restart Backend
```powershell
# Restart the server
.\run_backend.ps1
```

### Step 6: Test
Visit: http://localhost:8000/docs

Look for `/api/supabase/*` endpoints to test!

## What You Can Do Now

### Create a Fight
```
POST /api/supabase/fights
{
  "description": "UFC 300: Silva vs Adesanya",
  "user_id": "judge_001",
  "metadata": {
    "event": "UFC 300",
    "location": "Madison Square Garden"
  }
}
```

### Submit a Judgment
```
POST /api/supabase/judgments
{
  "fight_id": "550e8400-e29b-41d4-a716-446655440000",
  "winner": "Anderson Silva",
  "scores": {
    "round1": {"anderson": 10, "israel": 9},
    "round2": {"anderson": 9, "israel": 10},
    "total": {"anderson": 29, "israel": 28}
  },
  "reasoning": "Superior striking in rounds 1, 3",
  "ai_model": "ICVSS-v2"
}
```

### Get Fight Judgments
```
GET /api/supabase/fights/{fight_id}/judgments
```

## File Structure

```
backend/
├── supabase_client.py           ← Database functions
├── supabase_routes.py           ← FastAPI endpoints
├── SUPABASE_SETUP.md            ← Complete guide
├── SUPABASE_QUICKSTART.md       ← Quick reference
├── server.py                    ← Main app (needs 3 edits)
├── .env                         ← Configuration
└── requirements.txt             ← Dependencies
```

## Available Endpoints

### Fights Management
- `POST /api/supabase/fights` - Create
- `GET /api/supabase/fights` - List all
- `GET /api/supabase/fights/{id}` - Get one
- `PUT /api/supabase/fights/{id}` - Update

### Judgments Management
- `POST /api/supabase/judgments` - Create
- `GET /api/supabase/judgments` - List all
- `GET /api/supabase/judgments/{id}` - Get one
- `GET /api/supabase/fights/{id}/judgments` - Get for fight
- `PUT /api/supabase/judgments/{id}` - Update

### Analytics
- `GET /api/supabase/stats/fights` - Fight stats
- `GET /api/supabase/stats/judgments` - Judgment stats

## Data Models

### Fight Object
```json
{
  "id": "uuid",
  "description": "Fight description",
  "user_id": "creator_id",
  "metadata": {
    "event": "Event name",
    "location": "Location",
    "fighters": ["Fighter A", "Fighter B"]
  },
  "created_at": "timestamp",
  "updated_at": "timestamp"
}
```

### Judgment Object
```json
{
  "id": "uuid",
  "fight_id": "uuid",
  "winner": "Fighter name",
  "scores": {
    "round1": {"fighter_a": 10, "fighter_b": 9},
    "round2": {"fighter_a": 9, "fighter_b": 10},
    "round3": {"fighter_a": 10, "fighter_b": 8}
  },
  "reasoning": "Why this decision",
  "ai_model": "Model name",
  "user_id": "judge_id",
  "created_at": "timestamp",
  "updated_at": "timestamp"
}
```

## Key Features

✅ **PostgreSQL Database** - Reliable, scalable backend
✅ **Async Operations** - Non-blocking database calls
✅ **Type Safety** - Pydantic models for validation
✅ **REST API** - Standard HTTP endpoints
✅ **Full CRUD** - Create, read, update for both tables
✅ **Filtering & Sorting** - Query with parameters
✅ **Foreign Keys** - Judgments linked to fights
✅ **Timestamps** - Auto-tracked creation/update time
✅ **Metadata Support** - Flexible JSON storage
✅ **Error Handling** - Graceful error responses

## Security Best Practices

⚠️ **Important:**
- Never commit `.env` to git (it's ignored by default)
- Service role key stays on server only
- Use anon key for frontend (if building one)
- Enable Row Level Security (RLS) for production
- Keep API keys in environment variables only

## Troubleshooting

**"SUPABASE_URL is empty"**
- Make sure `.env` has all three credentials filled
- Check for extra spaces around `=`

**"Table does not exist"**
- Run the SQL setup script in Supabase
- Verify table names match (case-sensitive)

**"Request failed"**
- Check internet connection
- Verify Supabase project is active (not paused)
- Check API key is correct

**Import errors in server.py**
- Make sure `supabase_client.py` and `supabase_routes.py` are in backend folder
- Check import paths match file names

## Resources

- 📘 **SUPABASE_SETUP.md** - Detailed setup guide
- 📗 **SUPABASE_QUICKSTART.md** - Quick reference
- 💻 **supabase_client.py** - Source code with docstrings
- 🔗 **https://supabase.com/docs** - Official docs
- 🐍 **https://github.com/supabase-community/supabase-py** - Python client

## Timeline

- **Now**: Read this file
- **5 min**: Create Supabase project
- **5 min**: Get credentials & update `.env`
- **5 min**: Run SQL setup script
- **10 min**: Edit `server.py`
- **1 min**: Restart backend
- **5 min**: Test endpoints

**Total: ~30 minutes** to full integration! ⚡

---

**Ready to proceed?** Follow the 6 steps above, then visit http://localhost:8000/docs to see your new endpoints in action! 🚀
