# Emergent Backend - Quick Start Guide

## 🎯 Status

✅ **All Python dependencies installed and ready**
- FastAPI framework
- Motor (async MongoDB driver)
- Uvicorn (ASGI server)
- All supporting packages

## ⚡ Quick Start (3 Steps)

### Step 1: Install MongoDB

Choose one option:

**Option A: MongoDB Community (Recommended)**
- Download: https://www.mongodb.com/try/download/community
- Install normally (Windows installer available)
- MongoDB will auto-start as a Windows service

**Option B: MongoDB Atlas (Cloud)** 
- Go to: https://www.mongodb.com/cloud/atlas
- Create free cluster
- Get connection string
- Update `.env` with your credentials

**Option C: Docker** (if available)
```powershell
docker run -d -p 27017:27017 --name emergent-mongodb mongo:latest
```

### Step 2: Update Configuration

The `.env` file is already set up for local MongoDB:
```
MONGO_URL=mongodb://localhost:27017
DB_NAME=emergent_test
```

No changes needed if using local MongoDB! If using MongoDB Atlas, update MONGO_URL.

### Step 3: Start the Server

```powershell
# From the backend folder
.\run_backend.ps1
```

Or manually:
```powershell
.\.venv\Scripts\Activate.ps1
python -m uvicorn server:app --host 0.0.0.0 --port 8000 --reload
```

**Server is live at:** http://localhost:8000

## 📚 Testing the Backend

Once running, test with:

```powershell
# Interactive API explorer
.\test_backend.ps1

# Or manually test endpoints
curl http://localhost:8000/health
curl http://localhost:8000/api/bouts
curl http://localhost:8000/docs
```

**Visit in browser:**
- Swagger/OpenAPI Docs: http://localhost:8000/docs
- Alternative Docs: http://localhost:8000/redoc

## 📁 Project Structure

```
backend/
├── server.py                 # Main FastAPI application (7099 lines)
├── run_backend.ps1          # Quick start script ⭐ USE THIS
├── test_backend.ps1         # Testing utility
├── SETUP_GUIDE.md           # Detailed setup instructions
├── .env                      # Configuration (already set)
├── requirements.txt          # Dependencies (all installed)
├── .venv/                    # Python virtual environment
│
├── database/                # Database utilities
│   └── init_db.py          # MongoDB schema initialization
│
├── auth_rbac/              # Authentication & role management
├── advanced_audit/         # Audit logging
├── ai_merge_engine/        # AI event merging
├── blockchain_audit/       # Block chain-style logging
├── scoring_engine_v2/      # Scoring logic
│
└── ... (20+ feature modules)
```

## 🏗️ Architecture

```
Client (Browser/App)
        ↓
    HTTP/WebSocket
        ↓
    FastAPI (Uvicorn)
        ↓
    [Routing & Business Logic]
        ↓
    MongoDB {
      - Bouts
      - Events
      - Scores
      - Users
    }
```

## 🚀 Key Features Loaded

- ✅ ICVSS (Intelligent Combat Vision Scoring System)
- ✅ Fight Judge AI (E1) - Integrated Scoring
- ✅ CV Analytics (E2) - Computer Vision events
- ✅ Event Harmonizer - Judge vs CV conflict resolution
- ✅ Round Validator - Real-time validation
- ✅ Replay Service - Event replay capability
- ✅ Advanced Audit - Tamper-proof logging
- ✅ Blockchain Audit - Immutable records
- ✅ Failover Engine - Auto-failover support
- ✅ Performance Profiler - Real-time metrics
- ✅ Fighter Analytics - Historical stats
- ✅ Social Media Integration
- ✅ Branding & Themes

And 10+ more modules!

## 📡 Main API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Server health check |
| GET | `/api/bouts` | List all bouts |
| POST | `/api/bouts` | Create new bout |
| GET | `/api/bouts/{id}` | Get bout details |
| POST | `/api/judge` | Submit judge scoring |
| WS | `/ws/{bout_id}` | Real-time scoring updates |
| GET | `/docs` | Swagger API documentation |
| GET | `/redoc` | Alternative API documentation |

## 🔧 Troubleshooting

### "Cannot connect to MongoDB"
```
pymongo.errors.ServerSelectionTimeoutError
```
**Solution:**
1. Make sure MongoDB is running: `mongod` (or check Windows Services)
2. Verify MONGO_URL in `.env` is correct
3. Try connecting directly: `mongo` or use MongoDB Compass

### "Port 8000 already in use"
**Solution:**
```powershell
# Use a different port
.\run_backend.ps1 -Port 8001

# Or find and stop the process using port 8000
Get-NetTCPConnection -LocalPort 8000 | Select-Object OwningProcess
```

### "Module not found" errors
**Solution:**
```powershell
# Reinstall all dependencies
pip install -r requirements.txt --force-reinstall
```

### "Invalid URI host"
**Solution:**
- If using MongoDB Atlas, replace `<USERNAME>`, `<PASSWORD>`, `<CLUSTER>` in MONGO_URL
- Don't use `< >` brackets - replace with actual values

## 📊 Monitoring

Once running, check these endpoints:
- Health: `http://localhost:8000/health`
- Performance: `http://localhost:8000/api/performance` (if available)
- Metrics: WebSocket stream at `/ws/metrics` (if available)

## 💾 Data

The backend uses MongoDB with collections for:
- `bouts` - Fight information
- `events` - Scoring events
- `round_results` - Round scoring
- `unified_events` - Harmonized judge + CV events
- `audit_logs` - Complete audit trail

## 🔐 Security

- Role-based access control (RBAC)
- SHA256 audit trails
- JWT authentication ready
- Blockchain-style tamper-proof logging

## 📖 Documentation

For more detailed info, see:
- `SETUP_GUIDE.md` - Comprehensive setup guide
- Server code: `server.py` (7099 lines with full documentation)
- API Docs: Visit `/docs` after starting server

## 🎓 Learning the APIs

1. **Start the server**: `.\run_backend.ps1`
2. **Visit**: http://localhost:8000/docs
3. **Try endpoints**: Use the interactive Swagger UI
4. **Read responses**: Each endpoint shows request/response schemas

## ❓ Questions?

Check the `SETUP_GUIDE.md` file for more detailed instructions on:
- MongoDB installation options
- Configuration details
- Advanced setup
- Performance tuning
- Production deployment

---

**Ready to start?** Run: `.\run_backend.ps1` ⚡
