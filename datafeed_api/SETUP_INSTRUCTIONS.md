# 🚀 Database Setup Instructions

Due to network restrictions, you'll need to run the SQL migration through the Supabase SQL Editor.

## Step 1: Open Supabase SQL Editor

Click this link to open your project's SQL Editor:
**https://supabase.com/dashboard/project/yymuzbgipozkaxqabtxb/sql/new**

## Step 2: Copy the Migration SQL

The complete SQL migration is in:
```
/app/datafeed_api/migrations/001_initial_schema.sql
```

You can view it with:
```bash
cat /app/datafeed_api/migrations/001_initial_schema.sql
```

## Step 3: Paste and Execute

1. Copy ALL the SQL from the migration file
2. Paste it into the Supabase SQL Editor
3. Click the **"Run"** button (green play button)

## Step 4: Verify Setup

The migration will:
- ✅ Create all 7 tables (events, fighters, fights, round_state, fight_results, api_clients, audit_log)
- ✅ Set up indexes and constraints
- ✅ Create helper functions (sequence generator, triggers)
- ✅ Seed sample data (PFC 50 event with one test fight)
- ✅ Generate 3 API keys (one for each scope)

## Step 5: Get Your API Keys

After running the migration, fetch your test API keys:

```sql
SELECT name, api_key, scope FROM api_clients ORDER BY scope;
```

You should see 3 keys:
- **fantasy.basic** - Basic stats only
- **fantasy.advanced** - Basic stats + AI predictions
- **sportsbook.pro** - Full access including timeline

## Step 6: Test the API

Once the database is set up, the API server will be running at:
- **WebSocket:** `ws://localhost:8002/v1/realtime`
- **REST API:** `http://localhost:8002/v1`
- **Docs:** `http://localhost:8002/docs`

### Test REST Endpoint

```bash
# Get sample event
curl -H "Authorization: Bearer YOUR_API_KEY" \
  http://localhost:8002/v1/events/PFC50

# Get live fight state
curl -H "Authorization: Bearer YOUR_API_KEY" \
  http://localhost:8002/v1/fights/PFC50-F3/live
```

### Test WebSocket

```javascript
const ws = new WebSocket('ws://localhost:8002/v1/realtime');

ws.onopen = () => {
  // Authenticate
  ws.send(JSON.stringify({
    type: 'auth',
    api_key: 'YOUR_API_KEY'
  }));
};

ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);
  console.log('Received:', msg);
  
  if (msg.type === 'auth_ok') {
    // Subscribe to fight updates
    ws.send(JSON.stringify({
      type: 'subscribe',
      channel: 'fight',
      filters: { fight_code: 'PFC50-F3' }
    }));
  }
};
```

## Alternative: Run SQL via Command Line

If you have `psql` installed locally with network access to Supabase:

```bash
psql "postgresql://postgres:Cletalily349!@db.yymuzbgipozkaxqabtxb.supabase.co:5432/postgres" \
  < /app/datafeed_api/migrations/001_initial_schema.sql
```

## Need Help?

If you encounter any issues:
1. Check the Supabase logs in the dashboard
2. Verify your connection credentials
3. Ensure the database is not paused

## Next Steps After Setup

Once the database is ready:
1. ✅ API server will be running
2. ✅ Test with sample data
3. 🔄 Build event emitter service (broadcasts updates to WebSocket clients)
4. 🔄 Connect to FJAIPOS operator interface (data ingestion)
5. 🔄 Add rate limiting
6. 🔄 Deploy to production
