# Lovable.dev Frontend Integration Guide

Complete setup for connecting your Lovable.dev frontend to the Emergent Backend.

---

## 1. LOCAL DEVELOPMENT SETUP

### Backend Running Locally

**Environment Variables for Frontend (.env.local)**
```env
VITE_API_BASE=http://localhost:8000/api/v1/supabase
VITE_HEALTH_CHECK=http://localhost:8000/api/v1/supabase/health
```

**CORS Configuration (Already Enabled)**
- ✅ All origins allowed by default (`*`)
- ✅ All methods allowed
- ✅ All headers allowed

### Frontend API Service (Example - TypeScript)

```typescript
// services/api.ts
const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000/api/v1/supabase';

export const apiClient = {
  async request(endpoint: string, options: RequestInit = {}) {
    const url = `${API_BASE}${endpoint}`;
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
    
    if (!response.ok) {
      throw new Error(`API Error: ${response.status} ${response.statusText}`);
    }
    
    return response.json();
  },

  // Fights API
  fights: {
    create: (external_id: string, metadata?: Record<string, any>) =>
      apiClient.request('/fights', {
        method: 'POST',
        body: JSON.stringify({ external_id, metadata }),
      }),
    
    list: (limit?: number) =>
      apiClient.request(`/fights${limit ? `?limit=${limit}` : ''}`),
    
    get: (fight_id: string) =>
      apiClient.request(`/fights/${fight_id}`),
    
    update: (fight_id: string, updates: Record<string, any>) =>
      apiClient.request(`/fights/${fight_id}`, {
        method: 'PUT',
        body: JSON.stringify(updates),
      }),
  },

  // Judgments API
  judgments: {
    create: (fight_id: string, judge: string, scores: Record<string, any>) =>
      apiClient.request('/judgments', {
        method: 'POST',
        body: JSON.stringify({ fight_id, judge, scores }),
      }),
    
    list: (limit?: number) =>
      apiClient.request(`/judgments${limit ? `?limit=${limit}` : ''}`),
    
    get: (judgment_id: string) =>
      apiClient.request(`/judgments/${judgment_id}`),
    
    getByFight: (fight_id: string) =>
      apiClient.request(`/fights/${fight_id}/judgments`),
    
    update: (judgment_id: string, updates: Record<string, any>) =>
      apiClient.request(`/judgments/${judgment_id}`, {
        method: 'PUT',
        body: JSON.stringify(updates),
      }),
  },

  // Health Check
  health: () =>
    apiClient.request('/health'),
};
```

### React Component Example (Lovable.dev)

```tsx
// components/FightManager.tsx
'use client'

import { useState, useEffect } from 'react';
import { apiClient } from '@/services/api';

export function FightManager() {
  const [fights, setFights] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadFights();
  }, []);

  const loadFights = async () => {
    setLoading(true);
    try {
      const data = await apiClient.fights.list(50);
      setFights(data.data || []);
    } catch (error) {
      console.error('Failed to load fights:', error);
    } finally {
      setLoading(false);
    }
  };

  const createFight = async () => {
    try {
      const result = await apiClient.fights.create('fight_001', {
        fighters: ['Fighter A', 'Fighter B'],
        event: 'UFC 300',
        location: 'Las Vegas',
      });
      setFights([...fights, result.data]);
    } catch (error) {
      console.error('Failed to create fight:', error);
    }
  };

  return (
    <div>
      <h1>Fights</h1>
      <button onClick={createFight}>Create Fight</button>
      {loading && <p>Loading...</p>}
      <ul>
        {fights.map((fight) => (
          <li key={fight.id}>{fight.external_id}</li>
        ))}
      </ul>
    </div>
  );
}
```

---

## 2. CLOUD DEPLOYMENT

### Option A: Both on Same Domain (Recommended)

**Example: `yourdomain.com`**

Backend: `https://yourdomain.com/api/v1/supabase`
Frontend: `https://yourdomain.com`

**Frontend Environment Variables**
```env
VITE_API_BASE=https://yourdomain.com/api/v1/supabase
VITE_HEALTH_CHECK=https://yourdomain.com/api/v1/supabase/health
```

**Setup (Nginx/Apache Reverse Proxy)**

```nginx
# Nginx configuration for backend proxy
server {
    listen 443 ssl https2;
    server_name yourdomain.com;

    # Frontend (serves static files)
    location / {
        root /var/www/lovable-frontend;
        try_files $uri $uri/ /index.html;
    }

    # Backend API proxy
    location /api/ {
        proxy_pass http://localhost:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # CORS headers (if reverse proxy doesn't preserve them)
        add_header Access-Control-Allow-Origin $http_origin always;
        add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS" always;
        add_header Access-Control-Allow-Headers "Content-Type, Authorization" always;
        
        if ($request_method = OPTIONS) {
            return 200;
        }
    }

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
}
```

**Python Backend Server Command**
```bash
python -m uvicorn server:app --host 127.0.0.1 --port 8000 --log-level info
```

---

### Option B: Different Domains

**Example:**
- Frontend: `https://app.yourdomain.com`
- Backend: `https://api.yourdomain.com`

**Frontend Environment Variables**
```env
VITE_API_BASE=https://api.yourdomain.com/api/v1/supabase
VITE_HEALTH_CHECK=https://api.yourdomain.com/api/v1/supabase/health
```

**Backend CORS Configuration (server.py)**
```python
# Add to server.py before running
import os

CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'https://app.yourdomain.com,https://yourdomain.com')
# Set environment variable when starting:
# export CORS_ORIGINS=https://app.yourdomain.com
```

:warning: **Important:** Update `CORS_ORIGINS` env var when starting the server:
```bash
export CORS_ORIGINS=https://app.yourdomain.com
python -m uvicorn server:app --host 0.0.0.0 --port 8000
```

---

## 3. AUTHENTICATION OPTIONS

### Option A: No Authentication (Default)
Uses Supabase anonymous key (already configured).

**Pros:**
- Simple setup
- Works immediately
- Good for internal tools

**Cons:**
- Anyone with API endpoint can access data
- Not suitable for public production

**Implementation:**
```typescript
// No auth needed - already included in requests
const response = await fetch('https://api.yourdomain.com/api/v1/supabase/fights');
```

---

### Option B: API Key Authentication (Recommended for Production)

**Step 1: Generate API Keys in Backend**

Create a new file: `api_key_manager.py`

```python
import secrets
import hashlib
from datetime import datetime

def generate_api_key():
    """Generate a random API key"""
    return secrets.token_urlsafe(32)

def hash_api_key(api_key: str) -> str:
    """Hash API key for storage"""
    return hashlib.sha256(api_key.encode()).hexdigest()

# Usage:
# key = generate_api_key()  # Give to user
# key_hash = hash_api_key(key)  # Store in database
```

**Step 2: Add Authentication Middleware to server.py**

```python
from fastapi import Depends, HTTPException, Header

# In-memory API keys (replace with database in production)
VALID_API_KEYS = {
    "key_a1b2c3d4e5f6g7h8": "frontend-app",
    "key_x9y8z7w6v5u4t3s2": "mobile-app",
}

async def verify_api_key(x_api_key: str = Header(...)):
    """Verify API key from header"""
    if x_api_key not in VALID_API_KEYS:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key

# Add dependency to Supabase routes:
@supabase_router.get("/fights", dependencies=[Depends(verify_api_key)])
async def list_all_fights(...):
    # Now protected by API key
    ...
```

**Step 3: Frontend Sends API Key**

```typescript
// services/api.ts
const API_KEY = import.meta.env.VITE_API_KEY;

export const apiClient = {
  async request(endpoint: string, options: RequestInit = {}) {
    const url = `${API_BASE}${endpoint}`;
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': API_KEY,  // Add API key to all requests
        ...options.headers,
      },
    });
    
    if (response.status === 401) {
      throw new Error('Invalid API key');
    }
    
    return response.json();
  },
  // ... rest of methods
};
```

**Frontend Environment Variables**
```env
VITE_API_BASE=https://api.yourdomain.com/api/v1/supabase
VITE_API_KEY=key_a1b2c3d4e5f6g7h8
```

:warning: **Security Note:** Never commit API keys to git. Use environment variables.

---

### Option C: JWT Authentication (Advanced)

For enterprise deployments with user authentication:

```python
# In server.py
from fastapi.security import HTTPBearer, HTTPAuthCredential
from jose import JWTError, jwt

security = HTTPBearer()
SECRET_KEY = os.getenv("JWT_SECRET", "your-secret-key")

async def verify_jwt(credentials: HTTPAuthCredential = Depends(security)):
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user_id
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Use on protected routes:
@supabase_router.get("/fights", dependencies=[Depends(verify_jwt)])
async def list_all_fights(...):
    # Now requires valid JWT
    ...
```

Frontend sends JWT:
```typescript
const response = await fetch(url, {
  headers: {
    'Authorization': `Bearer ${jwtToken}`,
  },
});
```

---

## 4. COMPLETE SETUP CHECKLIST

### Local Development

- [ ] Backend runs on `http://localhost:8000`
- [ ] Frontend runs on `http://localhost:3000` (or your dev port)
- [ ] Environment variables set in `.env.local`
- [ ] CORS working (no blocked requests in browser console)
- [ ] Health check passing: `GET /api/v1/supabase/health`
- [ ] Can create fight: `POST /api/v1/supabase/fights`
- [ ] Can list fights: `GET /api/v1/supabase/fights`

### Production Deployment

- [ ] Backend deployed to cloud (AWS, Heroku, DigitalOcean, etc.)
- [ ] Frontend deployed (Vercel, Netlify, etc.)
- [ ] Domain configured (yourdomain.com)
- [ ] SSL/HTTPS enabled
- [ ] Environment variables updated:
  - `VITE_API_BASE=https://yourdomain.com/api/v1/supabase`
  - `CORS_ORIGINS=https://app.yourdomain.com` (if separate domains)
- [ ] API keys configured (if using authentication)
- [ ] Health check passing on production
- [ ] Smoke tests passing

---

## 5. TESTING & DEBUGGING

### Health Check Endpoint

```bash
# Local
curl http://localhost:8000/api/v1/supabase/health

# Production
curl https://yourdomain.com/api/v1/supabase/health
```

Expected response:
```json
{
  "status": "ok",
  "service": "supabase",
  "database_connected": true,
  "statistics": {
    "total_fights_stored": 42,
    "total_judgments_stored": 157
  },
  "timestamp": "2026-02-07T19:30:45.123456+00:00"
}
```

### Browser Console Debugging

```javascript
// Test API connection
fetch('http://localhost:8000/api/v1/supabase/health')
  .then(r => r.json())
  .then(d => console.log('✓ API OK', d))
  .catch(e => console.error('✗ API Error', e));

// Create test fight
fetch('http://localhost:8000/api/v1/supabase/fights', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    external_id: 'test_' + Date.now(),
    metadata: { test: true }
  })
})
  .then(r => r.json())
  .then(d => console.log('✓ Fight created', d))
  .catch(e => console.error('✗ Error', e));
```

### Common Issues

| Issue | Solution |
|-------|----------|
| CORS error in browser | Check backend CORS_ORIGINS env var |
| 404 on API endpoint | Verify Supabase router is registered in server.py |
| Connection timeout | Backend not running or wrong port |
| 401 Unauthorized | Missing/invalid API key (if auth enabled) |
| Database error | Supabase credentials not configured |

---

## 6. DEPLOYMENT PLATFORMS

### Heroku (Easy for Backend)

```bash
# Deploy Python backend to Heroku
heroku login
heroku create your-app-name
git push heroku main

# Set environment variables
heroku config:set SUPABASE_URL=https://...
heroku config:set SUPABASE_ANON_KEY=...
heroku config:set CORS_ORIGINS=https://app.yourdomain.com
```

### Vercel (Easy for Frontend)

```bash
# Deploy Lovable frontend to Vercel
vercel deploy

# Set environment variables in Vercel dashboard
VITE_API_BASE=https://your-backend.herokuapp.com/api/v1/supabase
```

### AWS / DigitalOcean / GCP

See backend server startup section - standard Python FastAPI deployment.

---

## 7. QUICK START COMMANDS

### Terminal 1: Start Backend
```bash
cd backend
.\.venv\Scripts\python.exe -m uvicorn server:app --host 127.0.0.1 --port 8000
```

### Terminal 2: Start Frontend
```bash
cd lovable-frontend
npm run dev
```

### Terminal 3: Test API
```bash
.\.venv\Scripts\python.exe
# Then in Python:
>>> import httpx, asyncio
>>> asyncio.run(httpx.AsyncClient().get('http://localhost:8000/api/v1/supabase/health')).json()
```

---

## 8. ENVIRONMENT VARIABLES SUMMARY

### Frontend (.env.local / .env.production)
```env
# Required
VITE_API_BASE=http://localhost:8000/api/v1/supabase

# Optional
VITE_API_KEY=key_xxx (if using API key auth)
VITE_HEALTH_CHECK=http://localhost:8000/api/v1/supabase/health
```

### Backend (.env)
```env
# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key

# CORS
CORS_ORIGINS=*  # or specific domains like https://yourdomain.com

# Server
MONGO_URL=mongodb://...
DB_NAME=your_db
```

---

**Ready to connect!** 🚀 Your Lovable.dev frontend is now fully configured to work with the Emergent Backend.
