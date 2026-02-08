# Backend Setup Guide

## Prerequisites Installed ✓
- Python 3.14.3
- Virtual environment (.venv)
- All dependencies from requirements.txt

## What's Needed to Run the Server

The backend requires **MongoDB** to be running. Here are your options:

### Option 1: MongoDB Atlas (Cloud - Easiest)
1. Go to https://www.mongodb.com/cloud/atlas
2. Create a free account
3. Create a cluster
4. Get your connection string
5. Update `.env` file with your connection details:
   ```
   MONGO_URL=mongodb+srv://<USERNAME>:<PASSWORD>@<YOUR_CLUSTER>.mongodb.net/
   DB_NAME=emergent_prod
   ```

### Option 2: Local MongoDB Installation (Recommended for Development)

**Windows:**
1. Download: https://www.mongodb.com/try/download/community
2. Run the installer
3. During installation, select "Install MongoDB as a Service"
4. MongoDB will start automatically
5. Update `.env`:
   ```
   MONGO_URL=mongodb://localhost:27017
   DB_NAME=emergent_test
   ```

**Alternative - Using Docker (if installed):**
```powershell
docker run -d -p 27017:27017 --name mongodb mongo:latest
```

### Option 3: MongoDB Memory Server (Testing Only)
```powershell
npm install -g mongodb-memory-server
mongod-service start  # (If installed globally)
```

## Configuration Files

### .env (Current Configuration)
```
MONGO_URL=mongodb://localhost:27017
DB_NAME=emergent_test
```

### Optional Environment Variables
- `POSTGRES_URL` - PostgreSQL connection (optional)
- `REDIS_URL` - Redis connection (optional)
- `DEBUG` - Set to "true" for verbose logging

## Starting the Server

Once MongoDB is running:

```powershell
# From the backend directory
.\.venv\Scripts\Activate.ps1

# Start the development server
python -m uvicorn server:app --host 0.0.0.0 --port 8000 --reload
```

The server will be available at: **http://localhost:8000**

### API Documentation
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Verifying the Backend Works

Once running, test with:

```powershell
# Healthcheck
curl http://localhost:8000/health

# List all bouts
curl http://localhost:8000/api/bouts

# Get Swagger/OpenAPI docs
curl http://localhost:8000/docs
```

## Troubleshooting

### "Cannot connect to MongoDB"
```
pymongo.errors.ServerSelectionTimeoutError
```
**Solution:** Make sure MongoDB is running on localhost:27017 or update MONGO_URL in .env

### "Invalid URI host"
```
pymongo.errors.ConfigurationError
```
**Solution:** Check your MONGO_URL in .env - replace placeholders with real values

### "Module not found" errors
**Solution:** Reinstall dependencies:
```powershell
pip install -r requirements.txt --force-reinstall
```

### Port 8000 already in use
**Solution:** Change the port:
```powershell
python -m uvicorn server:app --host 0.0.0.0 --port 8001
```

## Architecture

The backend is a **FastAPI/Python** application with:
- **FastAPI** - Web framework
- **Motor** - Async MongoDB driver
- **Uvicorn** - ASGI server
- **Motor + PyMongo** - Database ORM
- **Pydantic** - Data validation
- **WebSockets** - Real-time updates

## Key Endpoints

- `GET /api/bouts` - List all bouts
- `POST /api/bouts` - Create new bout
- `GET /api/bouts/{bout_id}` - Get bout details
- `WebSocket /ws/{bout_id}` - Real-time scoring updates
- `POST /api/judge` - Submit judge scoring
- `GET /health` - Server health check

## Next Steps

1. **Install MongoDB** (Option 1 or 2 above)
2. **Update `.env`** with MongoDB connection details
3. **Start the server** using the uvicorn command above
4. **Test** by visiting http://localhost:8000/docs in your browser

Enjoy your backend!
