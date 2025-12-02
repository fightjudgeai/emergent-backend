# Fight Judge AI Data Feed API

Financial-grade real-time sports data syndication system for fantasy sports and regulated sportsbooks.

## 🏗️ Architecture

- **FastAPI** backend with WebSocket + REST endpoints
- **PostgreSQL** (Supabase) database with financial-grade data integrity
- **Asyncpg** for high-performance async database operations
- **Scope-based authentication** with three tiers:
  - `fantasy.basic` - Basic stats (strikes, control time, etc.)
  - `fantasy.advanced` - + AI predictions (damage, win probability)
  - `sportsbook.pro` - Full access including timeline and audit logs

## 📊 Database Schema

### Core Tables
- **events** - Fight cards/events
- **fighters** - Fighter profiles
- **fights** - Individual matchups
- **round_state** - Granular, monotonically-sequenced round updates
- **fight_results** - Final outcomes
- **api_clients** - API key management
- **audit_log** - Immutable audit trail for compliance

## 🚀 Quick Start

### 1. Configure Environment

Copy `.env.example` to `.env` and fill in your Supabase credentials:

```bash
SUPABASE_URL=https://yymuzbgipozkaxqabtxb.supabase.co
SUPABASE_KEY=your_service_role_key
DATABASE_URL=postgresql://postgres.yymuzbgipozkaxqabtxb:[PASSWORD]@aws-0-us-east-1.pooler.supabase.com:6543/postgres
```

**Finding your credentials in Supabase:**
1. Go to your Supabase project: https://supabase.com/dashboard/project/yymuzbgipozkaxqabtxb
2. Click "Settings" → "API"
   - Copy the `service_role` key (NOT anon key) → This is your `SUPABASE_KEY`
3. Click "Settings" → "Database"
   - Copy the "Connection string" (URI format)
   - Replace `[YOUR-PASSWORD]` with your database password

### 2. Install Dependencies

```bash
cd /app/datafeed_api
pip install -r requirements.txt
```

### 3. Set Up Database

Run the migration to create tables and seed sample data:

```bash
python setup_database.py
```

This will:
- Create all database tables
- Set up indexes and constraints
- Generate 3 test API keys (one for each scope)
- Seed sample event data (PFC 50)

### 4. Start the Server

```bash
python main.py
```

The API will be available at:
- **WebSocket:** `ws://localhost:8002/v1/realtime`
- **REST API:** `http://localhost:8002/v1`
- **Docs:** `http://localhost:8002/docs`
- **Health:** `http://localhost:8002/health`

## 📡 API Usage

### REST Endpoints

#### Get Event Details
```bash
curl -H "Authorization: Bearer <API_KEY>" \
  http://localhost:8002/v1/events/PFC50
```

#### Get Live Fight State
```bash
curl -H "Authorization: Bearer <API_KEY>" \
  http://localhost:8002/v1/fights/PFC50-F3/live
```

#### Get Fight Timeline (sportsbook.pro only)
```bash
curl -H "Authorization: Bearer <API_KEY>" \
  http://localhost:8002/v1/fights/PFC50-F3/timeline
```

### WebSocket Protocol

#### 1. Connect
```javascript
const ws = new WebSocket('ws://localhost:8002/v1/realtime');
```

#### 2. Authenticate
```javascript
ws.send(JSON.stringify({
  type: 'auth',
  api_key: 'your_api_key_here'
}));

// Server responds: {"type": "auth_ok", "payload": {...}}
```

#### 3. Subscribe to Fight
```javascript
ws.send(JSON.stringify({
  type: 'subscribe',
  channel: 'fight',
  filters: { fight_code: 'PFC50-F3' }
}));

// Server responds: {"type": "subscribe_ok", "payload": {...}}
```

#### 4. Receive Real-Time Updates
```javascript
ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  
  if (message.type === 'round_state') {
    console.log('New round state:', message.payload);
    // Fields filtered based on your API key scope
  }
  
  if (message.type === 'fight_result') {
    console.log('Fight finished:', message.payload);
  }
};
```

## 🔐 Authentication & Scoping

### API Key Scopes

| Scope | Basic Stats | AI Predictions | Timeline | Audit Logs |
|-------|------------|----------------|----------|------------|
| `fantasy.basic` | ✅ | ❌ | ❌ | ❌ |
| `fantasy.advanced` | ✅ | ✅ | ❌ | ❌ |
| `sportsbook.pro` | ✅ | ✅ | ✅ | ✅ |

### Field Filtering

Fields automatically filtered based on scope:
- **Basic stats:** strikes, sig_strikes, knockdowns, control_sec, round_locked
- **AI predictions (advanced+):** ai_damage, ai_win_prob
- **Timeline (pro only):** Full historical state updates

## 🧪 Testing

### Test with Sample Data

After running `setup_database.py`, you'll have:
- 1 sample event: PFC 50
- 1 sample fight: PFC50-F3 (John "The Hammer" Striker vs Carlos "El Pulpo" Grappler)
- 3 API keys (one for each scope)

### Insert Round State Updates

```python
import asyncio
import asyncpg
import time

async def insert_round_update():
    conn = await asyncpg.connect('your_database_url')
    
    # Get fight ID
    fight = await conn.fetchrow("SELECT id FROM fights WHERE code = 'PFC50-F3'")
    
    # Insert round state
    await conn.execute("""
        INSERT INTO round_state (
            fight_id, round, ts_ms, seq,
            red_strikes, red_sig_strikes, blue_strikes, blue_sig_strikes,
            red_control_sec, blue_control_sec,
            red_ai_damage, red_ai_win_prob,
            blue_ai_damage, blue_ai_win_prob
        )
        VALUES ($1, 1, $2, $3, 15, 10, 12, 8, 45, 30, 12.5, 0.55, 8.3, 0.45)
    """, fight['id'], int(time.time() * 1000), 1)
    
    await conn.close()

asyncio.run(insert_round_update())
```

## 🏭 Production Deployment

### Environment Variables
```bash
ENVIRONMENT=production
DATABASE_URL=<production_supabase_url>
API_HOST=0.0.0.0
API_PORT=8002
SECRET_KEY=<strong_random_key>
```

### Supervisor Configuration

The API can be added to the existing supervisor setup:

```ini
[program:datafeed_api]
directory=/app/datafeed_api
command=python main.py
autostart=true
autorestart=true
stdout_logfile=/var/log/supervisor/datafeed_api.log
stderr_logfile=/var/log/supervisor/datafeed_api.err.log
```

### Rate Limiting

Rate limits are configured per API client in the `api_clients` table (`rate_limit_per_min` column). Default: 1000 requests/minute.

## 📈 Monitoring

### Health Check
```bash
curl http://localhost:8002/health
```

Returns:
```json
{
  "status": "healthy",
  "database": "connected",
  "websocket_connections": 5,
  "version": "1.0.0"
}
```

### Logs

```bash
# View API logs
tail -f /var/log/supervisor/datafeed_api.log

# View errors
tail -f /var/log/supervisor/datafeed_api.err.log
```

## 🎯 Next Steps

1. ✅ Database schema and migrations
2. ✅ WebSocket server with authentication
3. ✅ REST API endpoints
4. ✅ Scope-based field filtering
5. 🔄 **TODO:** Event emitter service to broadcast round_state updates to WebSocket clients
6. 🔄 **TODO:** Data ingestion pipeline from FJAIPOS operator interface
7. 🔄 **TODO:** Rate limiting implementation
8. 🔄 **TODO:** Comprehensive API documentation

## 📞 Support

For issues or questions about the Fight Judge AI Data Feed API, contact the development team.
