# ⚡ Quick Start Guide

## 🎯 Your Mission

Load dummy data into Supabase and test the Data Feed API.

## 📝 Step-by-Step

### Step 1: Run the Schema Migration

Open Supabase SQL Editor:
**https://supabase.com/dashboard/project/yymuzbgipozkaxqabtxb/sql/new**

Copy and paste the entire content of:
```bash
cat /app/datafeed_api/migrations/001_initial_schema.sql
```

Click **"Run"** ▶️

This creates all tables, indexes, and helper functions.

---

### Step 2: Load Dummy Data

**Option A: SQL (FASTEST - Recommended)**

In the same Supabase SQL Editor, copy and paste:
```bash
cat /app/datafeed_api/dummy_data.sql
```

Click **"Run"** ▶️

This loads:
- 1 event (PFC50)
- 6 fighters
- 3 fights with realistic matchups
- 6 round states (2 per fight)
- 3 fight results

**Option B: Table UI (Step-by-step)**

Follow the detailed guide in:
```bash
cat /app/datafeed_api/DUMMY_DATA_GUIDE.md
```

---

### Step 3: Get Your API Keys

In Supabase SQL Editor, run:
```sql
SELECT name, api_key, scope FROM api_clients ORDER BY scope;
```

You'll get 3 keys (copy them):
- **fantasy.basic** - Basic stats only
- **fantasy.advanced** - Stats + AI predictions  
- **sportsbook.pro** - Full access

---

### Step 4: Start the API Server

```bash
cd /app/datafeed_api
python main.py
```

The server will start on **http://localhost:8002**

---

### Step 5: Test the API

#### Test REST Endpoints

```bash
# Set your API key
export API_KEY='your_api_key_here'

# Run tests
./test_api.sh
```

#### Manual Tests

```bash
# Get event details
curl -H "Authorization: Bearer $API_KEY" \
  http://localhost:8002/v1/events/PFC50

# Get live fight state  
curl -H "Authorization: Bearer $API_KEY" \
  http://localhost:8002/v1/fights/PFC50-F1/live

# Get fight timeline (sportsbook.pro only)
curl -H "Authorization: Bearer $API_KEY" \
  http://localhost:8002/v1/fights/PFC50-F1/timeline
```

#### Test WebSocket (Browser Console)

```javascript
const ws = new WebSocket('ws://localhost:8002/v1/realtime');

ws.onopen = () => {
  ws.send(JSON.stringify({
    type: 'auth',
    api_key: 'paste_your_api_key_here'
  }));
};

ws.onmessage = (e) => {
  const msg = JSON.parse(e.data);
  console.log('📥', msg);
  
  if (msg.type === 'auth_ok') {
    console.log('✅ Authenticated as:', msg.payload.client_name);
    ws.send(JSON.stringify({
      type: 'subscribe',
      channel: 'fight',
      filters: { fight_code: 'PFC50-F1' }
    }));
  }
  
  if (msg.type === 'subscribe_ok') {
    console.log('✅ Subscribed to:', msg.payload.subscription_key);
  }
};
```

---

## 📊 Expected Test Data

After loading, you should have:

### Event
- **PFC50** - PFC 50: Frisco at Comerica Center

### Fights
1. **PFC50-F1** (bout 3) - John "The Blade" Strike vs Mike "The Hammer" Iron (Lightweight)
2. **PFC50-F2** (bout 2) - Carlos "El Fuego" Rivera vs Alex "The Wall" Stone (Featherweight)
3. **PFC50-F3** (bout 1) - David "Dragon" Lee vs Mark "The Tank" Torres (Welterweight)

### Round States
- Each fight has 2 rounds loaded
- Round 1: Locked (finalized)
- Round 2: Live (unlocked)

### Results
- Fight 1: RED wins by UD (Unanimous Decision)
- Fight 2: BLUE wins by TKO
- Fight 3: RED wins by KO

---

## 🐛 Troubleshooting

### Server won't start
```bash
# Check logs
tail -f /tmp/datafeed_api.log

# Check if database is accessible
cd /app/datafeed_api
python3 -c "
import asyncio
import asyncpg
import os
from dotenv import load_dotenv
load_dotenv()
async def test():
    url = os.getenv('DATABASE_URL')
    conn = await asyncpg.connect(url)
    print('✅ Connected')
    await conn.close()
asyncio.run(test())
"
```

### API returns 404
Make sure you ran BOTH:
1. The schema migration (`001_initial_schema.sql`)
2. The dummy data SQL (`dummy_data.sql`)

### WebSocket authentication fails
- Double-check you copied the correct API key
- Make sure it's from the `api_clients` table
- Try all 3 keys to test scope filtering

---

## 📚 Files Reference

| File | Purpose |
|------|---------|
| `migrations/001_initial_schema.sql` | Database schema (run first) |
| `dummy_data.sql` | Sample data (run second) |
| `main.py` | API server entrypoint |
| `test_api.sh` | Automated REST tests |
| `README.md` | Full documentation |
| `DUMMY_DATA_GUIDE.md` | Table UI instructions |

---

## ✅ Success Criteria

You'll know it's working when:
- ✅ Server starts without errors
- ✅ `/health` endpoint returns `"status": "healthy"`
- ✅ REST endpoints return event/fight data
- ✅ WebSocket authenticates and subscribes successfully
- ✅ Different API keys show different fields (scope filtering)

---

## 🚀 Next Steps

After successful testing:
1. Build event emitter service (broadcasts real-time updates)
2. Create data ingestion API (for operator interface)
3. Add rate limiting
4. Production deployment

**Questions? Issues? Let me know!**
