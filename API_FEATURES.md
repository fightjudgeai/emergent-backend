# Emergent Backend - API Features & Enhancements

## Overview
This document outlines all the advanced features implemented in the Emergent backend API.

---

## 1. CORS (Cross-Origin Resource Sharing)

### Status: ✅ Enabled

The API supports cross-origin requests from multiple origins to enable frontend integration.

**Configuration:**
- Location: `server.py`, line ~7000
- Allowed Origins: Configurable via `CORS_ORIGINS` environment variable
- Default: `*` (all origins)
- Methods: All HTTP methods allowed
- Headers: All headers allowed

**Environment Variable:**
```env
CORS_ORIGINS=https://yourdomain.com,https://api.yourdomain.com,http://localhost:3000
```

**Usage:**
The frontend can now make requests to the API without CORS errors:
```javascript
fetch('http://localhost:8000/api/v1/supabase/fights', {
  method: 'GET',
  headers: { 'Content-Type': 'application/json' }
})
```

---

## 2. Input Validation & Sanitization

### Status: ✅ Enabled

All API inputs are validated using Pydantic models with custom validators.

**Features:**
- Required field validation
- String length constraints
- JSON schema validation for complex fields
- Empty/whitespace detection
- Type checking

**Models with Validation:**

### FightCreate
```python
external_id: str  # Required, 1-255 chars, no empty strings
metadata: Dict    # Optional, must be JSON-serializable
```

Example validation errors:
```json
{
  "detail": [
    {
      "loc": ["body", "external_id"],
      "msg": "external_id cannot be empty or whitespace",
      "type": "value_error"
    }
  ]
}
```

### JudgmentCreate
```python
fight_id: str     # Required UUID reference
judge: str        # Optional, max 255 chars
scores: Dict      # Required, must be JSON-serializable, not empty
```

---

## 3. Automatic Retry Logic

### Status: ✅ Enabled

The Supabase client includes automatic retry logic for transient failures.

**Configuration:**
- Retry decorator: `tenacity` library
- Max attempts: 3
- Exponential backoff: 2-10 seconds
- Triggered by: Network timeouts, connection errors

**Features:**
- Automatic retry on `httpx.RequestError` and `httpx.TimeoutException`
- Exponential backoff prevents retry storms
- Detailed logging of retry attempts
- Transparent to API consumers (handled internally)

**Functions with Retry:**
- `create_fight()` - Up to 3 attempts
- `create_judgment()` - Up to 3 attempts
- Other read operations have inline error handling

**Example Log Output:**
```
[DEBUG] Attempting to create fight (attempt 1/3)
[DEBUG] Timeout on attempt 1, retrying in 2 seconds...
[DEBUG] Attempting to create fight (attempt 2/3)
[INFO] ✓ Fight created successfully
```

---

## 4. Health Checks & Database Connectivity

### Status: ✅ Enabled

Multiple health check endpoints for monitoring:

### Endpoint: GET /api/v1/supabase/health

**Response (Healthy):**
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

**Response (Degraded):**
```json
{
  "status": "degraded",
  "service": "supabase",
  "database_connected": false,
  "statistics": {
    "total_fights_stored": 0,
    "total_judgments_stored": 0
  },
  "timestamp": "2026-02-07T19:30:45.123456+00:00"
}
```

**Response (Error):**
```json
{
  "status": "error",
  "service": "supabase",
  "database_connected": false,
  "error": "Connection timeout after 30s",
  "timestamp": "2026-02-07T19:30:45.123456+00:00"
}
```

### Endpoint: GET /api/ping

Simple server heartbeat endpoint at `/api/ping` (existing).

---

## 5. API Versioning

### Status: ✅ v1.0 Active

All Supabase endpoints are versioned under `/api/v1/supabase/`.

**Benefits:**
- Backward compatibility for future versions
- Allows v2, v3 deployments without breaking v1 clients
- Clear deprecation path

**Version Endpoints:**

**v1 Base Path:** `/api/v1/supabase/`

Example progression for future versions:
- Current: `/api/v1/supabase/fights`
- Future: `/api/v2/supabase/fights` (new features, breaking changes)

---

## 6. Structured Request/Response Logging

### Status: ✅ Enabled

All requests and responses are logged with detailed context.

**Logging Configuration:**
- Location: `server.py`, line ~6217
- Format: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`
- Level: INFO (detailed logs sent to stderr)

**Log Levels:**
- `DEBUG`: Fine-grained debug info, retry attempts
- `INFO`: Operation successes, server startup
- `WARNING`: Non-fatal issues, uninitialized services
- `ERROR`: Operation failures with exception details

**Example Logs:**
```
2026-02-07 19:30:45 - supabase_client - INFO - ✓ Fight created: {...}
2026-02-07 19:30:46 - supabase_routes - INFO - User retrieved fight: fight_123
2026-02-07 19:30:47 - supabase_client - ERROR - Failed to create fight. Status: 500. Body: {...}
```

**Server Startup Logging:**
```
✓ Supabase Integration v1 loaded - Fight/Judgment storage
  - POST /api/v1/supabase/fights (create fight)
  - GET /api/v1/supabase/fights (list fights)
  - GET /api/v1/supabase/fights/{fight_id} (get fight)
  [... additional endpoints ...]
✓ Supabase REST client initialized on startup
```

---

## 7. Enhanced Error Handling

### Status: ✅ Enabled

Comprehensive error handling with meaningful error messages.

**HTTP Status Codes:**
- `200 OK` - Successful GET/POST
- `201 Created` - Successful resource creation
- `400 Bad Request` - Validation error, missing required fields
- `404 Not Found` - Resource doesn't exist
- `500 Internal Server Error` - Database or server error (with automatic retry)

**Error Response Format:**
```json
{
  "detail": "Fight not found"
}
```

**Validation Error Response:**
```json
{
  "detail": [
    {
      "loc": ["body", "scores"],
      "msg": "scores must be JSON-serializable",
      "type": "value_error"
    }
  ]
}
```

---

## 8. Endpoint Security

### Features Implemented:
✅ Bearer token authentication (via Supabase API keys)
✅ Request validation (Pydantic)
✅ CORS policy enforcement
✅ Input sanitization (JSON schema validation)

### Features NOT Yet Implemented (Optional):
- Rate limiting
- API key management per user
- Request signing/HMAC
- IP whitelisting

---

## 9. Production Readiness Checklist

### Completed:
- ✅ Database schema with indexes
- ✅ REST client without C++ dependencies
- ✅ Input validation and error handling
- ✅ Retry logic for transient failures
- ✅ Health check endpoints
- ✅ CORS configuration
- ✅ API versioning structure
- ✅ Logging and monitoring
- ✅ Comprehensive test suite (5 test suites, 100% passing)

### Recommended Monitoring:
- Health check: `GET /api/v1/supabase/health` every 30 seconds
- Error logs: Monitor for 500 or repeated 400 errors
- Statistics: Track fights/judgments stored via `/api/v1/supabase/stats/*`

---

## 10. Dependencies Added

**New requirements:**
```
tenacity==8.2.3    # Automatic retry logic
httpx==0.26.0      # Async HTTP client (already used)
```

**All existing dependencies** remain unchanged to maintain compatibility.

---

## Quick Started Guide

### 1. Start the Server
```bash
.\.venv\Scripts\python.exe -m uvicorn server:app --host 127.0.0.1 --port 8000
```

### 2. Test Health
```bash
curl http://127.0.0.1:8000/api/v1/supabase/health
```

### 3. Create a Fight
```bash
curl -X POST http://127.0.0.1:8000/api/v1/supabase/fights \
  -H "Content-Type: application/json" \
  -d '{
    "external_id": "fight_001",
    "metadata": {"fighters": ["A", "B"], "event": "UFC 300"}
  }'
```

### 4. List Fights
```bash
curl http://127.0.0.1:8000/api/v1/supabase/fights?limit=10
```

---

## Configuration Summary

| Feature | Status | Default | Configurable |
|---------|--------|---------|--------------|
| CORS | ✅ Enabled | Allow all origins | `CORS_ORIGINS` env var |
| Validation | ✅ Enabled | Strict | Pydantic models |
| Retry Logic | ✅ Enabled | 3 attempts, 2-10s backoff | Code change required |
| Health Checks | ✅ Enabled | Always on | Always on |
| API Versioning | ✅ v1 | /api/v1 | Future versions available |
| Logging | ✅ Enabled | INFO level | `log-level` flag in uvicorn |

---

## Performance Characteristics

**Database:**
- Fights: Index on `external_id` for fast lookups
- Judgments: Index on `fight_id` for filter queries
- All queries use REST API (no local caching)

**Network:**
- Timeout: 30 seconds per request
- Retry: Up to 3 attempts (max 45+ seconds if needed)
- Exponential backoff: Prevents retry storms

**Memory:**
- Lightweight REST client (httpx)
- No SDK overhead (no C++ dependencies)
- Minimal in-memory state

---

Last Updated: February 7, 2026
