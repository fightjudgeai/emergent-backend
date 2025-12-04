# API Key Access System - Complete Guide

## 🎯 Overview

The API Key Access System provides comprehensive authentication, authorization, and rate limiting for the Fight Judge AI Data Feed API. It implements Role-Based Access Control (RBAC) with 6 tier levels, cryptographic API key generation, and multi-period rate limiting.

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Request Flow                             │
└─────────────────────────────────────────────────────────────┘

Client Request
    │
    ├─→ Extract API Key (X-API-Key or Authorization header)
    │
    ├─→ Validate API Key (check api_clients table)
    │
    ├─→ Check Status (ACTIVE/SUSPENDED/REVOKED)
    │
    ├─→ Check Tier Permissions (RBAC)
    │
    ├─→ Check Rate Limits (minute, hour, day)
    │
    ├─→ Log Usage (api_usage_logs table)
    │
    └─→ Allow/Deny Request
```

---

## 📊 Database Schema

### api_clients Table

```sql
CREATE TABLE api_clients (
    id UUID PRIMARY KEY,
    name TEXT NOT NULL,
    tier TEXT NOT NULL CHECK (tier IN (
        'public', 'dev', 'fantasy.basic', 
        'fantasy.advanced', 'sportsbook.pro', 
        'promotion.enterprise'
    )),
    api_key TEXT UNIQUE NOT NULL,
    status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK (status IN (
        'ACTIVE', 'SUSPENDED', 'REVOKED'
    )),
    rate_limit_per_minute INT NOT NULL DEFAULT 60,
    rate_limit_per_hour INT DEFAULT 3600,
    rate_limit_per_day INT DEFAULT 50000,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_used_at TIMESTAMPTZ,
    notes TEXT
);
```

### api_usage_logs Table

```sql
CREATE TABLE api_usage_logs (
    id UUID PRIMARY KEY,
    client_id UUID NOT NULL REFERENCES api_clients(id),
    endpoint TEXT NOT NULL,
    method TEXT NOT NULL,
    status_code INT,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    response_time_ms INT,
    ip_address TEXT,
    user_agent TEXT
);
```

---

## 🎫 Access Tier System

### Tier Matrix

| Tier | Public | Fantasy | Markets | Events | WebSocket | Enterprise | Rate Limit/Min |
|------|--------|---------|---------|--------|-----------|------------|----------------|
| **public** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | 60 |
| **dev** | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | 120 |
| **fantasy.basic** | ✅ | ✅ | ❌ | ❌ | ✅ (delayed) | ❌ | 180 |
| **fantasy.advanced** | ✅ | ✅ | ❌ | ✅ | ✅ (live) | ❌ | 300 |
| **sportsbook.pro** | ✅ | ✅ | ✅ | ✅ | ✅ (live) | ❌ | 600 |
| **promotion.enterprise** | ✅ | ✅ | ✅ | ✅ | ✅ (live) | ✅ | 1200 |

### Tier Descriptions

**public** - UFCstats-style pages only
- Access: Fight stats, fighter profiles
- Use case: Public websites, media

**dev** - Development/testing tier
- Access: Public + delayed fight data
- Use case: Developers, testing environments

**fantasy.basic** - Basic fantasy sports
- Access: Public + basic fantasy scoring
- Use case: Casual fantasy platforms

**fantasy.advanced** - Advanced fantasy
- Access: Basic + live fantasy + AI metrics
- Use case: Professional fantasy platforms

**sportsbook.pro** - Sportsbook integration
- Access: Advanced + markets + settlement
- Use case: Sportsbook operators

**promotion.enterprise** - Full access
- Access: All features + custom branding
- Use case: Major promotions, partners

---

## 🔑 API Key Format

### Key Structure

```
FJAI_{32_CHARACTERS_RANDOM}
```

**Example:**
```
FJAI_x7K9mP2nQ4rS8tV1wX3yZ6aB5cD...
```

### Security Features

- **Cryptographically Secure**: Uses `secrets.token_urlsafe(32)`
- **256-bit Entropy**: 32 bytes of random data
- **URL-Safe**: No special characters that need encoding
- **Prefix**: `FJAI_` for easy identification

---

## 🔐 Authentication

### Headers

**Option 1: X-API-Key** (Recommended)
```http
X-API-Key: FJAI_x7K9mP2nQ4rS8tV1wX3yZ6aB5cD...
```

**Option 2: Authorization Bearer**
```http
Authorization: Bearer FJAI_x7K9mP2nQ4rS8tV1wX3yZ6aB5cD...
```

### Example Requests

**cURL:**
```bash
curl "http://localhost:8002/v1/fantasy/fight-id/fantasy.basic" \
  -H "X-API-Key: FJAI_FANTASY_BASIC_001"
```

**JavaScript:**
```javascript
fetch('/v1/fantasy/fight-id/fantasy.basic', {
  headers: {
    'X-API-Key': 'FJAI_FANTASY_BASIC_001'
  }
})
```

**Python:**
```python
import requests

headers = {'X-API-Key': 'FJAI_FANTASY_BASIC_001'}
response = requests.get('/v1/fantasy/fight-id/fantasy.basic', headers=headers)
```

---

## ⚡ Rate Limiting

### Three-Tier Rate Limiting

1. **Per-Minute Limit** - Prevents burst attacks
2. **Per-Hour Limit** - Prevents sustained abuse
3. **Per-Day Limit** - Prevents monthly quota exhaustion

### Rate Limit Headers

All authenticated responses include:

```http
X-RateLimit-Limit: 180
X-RateLimit-Remaining: 179
X-RateLimit-Reset: 1704389400
X-Tier: fantasy.basic
```

### Rate Limit Exceeded Response

**HTTP Status:** `429 Too Many Requests`

```json
{
    "detail": "Rate limit exceeded",
    "error": "rate_limit_exceeded",
    "period": "minute",
    "limit": 180,
    "current": 181,
    "reset_at": "2024-01-04T12:01:00Z"
}
```

**Headers:**
```http
X-RateLimit-Limit: 180
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1704389460
Retry-After: 42
```

---

## 🔨 API Key Management

### Create API Key

```bash
POST /admin/api-keys
Content-Type: application/json

{
    "name": "Partner ABC",
    "tier": "fantasy.basic",
    "rate_limit_per_minute": 180,
    "rate_limit_per_hour": 10800,
    "rate_limit_per_day": 150000,
    "notes": "Production key"
}
```

**Response:**
```json
{
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Partner ABC",
    "tier": "fantasy.basic",
    "api_key": "FJAI_x7K9mP2nQ4rS8tV1wX3yZ6aB5cD...",
    "status": "ACTIVE",
    "rate_limit_per_minute": 180,
    "created_at": "2024-01-04T12:00:00Z",
    "warning": "Save this API key securely. It will not be shown again."
}
```

### List API Keys

```bash
GET /admin/api-keys?tier=fantasy.basic&status_filter=ACTIVE&limit=50
```

**Response:**
```json
{
    "api_keys": [
        {
            "id": "uuid",
            "name": "Partner ABC",
            "tier": "fantasy.basic",
            "status": "ACTIVE",
            "rate_limit_per_minute": 180,
            "created_at": "2024-01-04T12:00:00Z",
            "last_used_at": "2024-01-04T14:30:00Z"
        }
    ],
    "total": 1
}
```

### Get API Key Details

```bash
GET /admin/api-keys/{key_id}
```

**Response:**
```json
{
    "id": "uuid",
    "name": "Partner ABC",
    "tier": "fantasy.basic",
    "api_key": "FJAI_x7K9mP...",  // Masked
    "status": "ACTIVE",
    "rate_limit_per_minute": 180,
    "rate_limit_per_hour": 10800,
    "rate_limit_per_day": 150000,
    "created_at": "2024-01-04T12:00:00Z",
    "last_used_at": "2024-01-04T14:30:00Z",
    "usage_statistics": {
        "total_requests": 15234
    }
}
```

### Update API Key

```bash
PATCH /admin/api-keys/{key_id}
Content-Type: application/json

{
    "status": "SUSPENDED",
    "notes": "Payment overdue"
}
```

### Revoke API Key

```bash
DELETE /admin/api-keys/{key_id}
```

---

## 🚫 Error Responses

### 401 Unauthorized

**Missing API Key:**
```json
{
    "detail": "API key required. Provide X-API-Key header or Authorization: Bearer <key>",
    "error": "unauthorized"
}
```

**Invalid API Key:**
```json
{
    "detail": "Invalid or inactive API key",
    "error": "unauthorized"
}
```

### 403 Forbidden

```json
{
    "detail": "Tier 'fantasy.basic' does not have access to this endpoint. Consider upgrading.",
    "error": "forbidden"
}
```

### 429 Too Many Requests

```json
{
    "detail": "Rate limit exceeded: 180 requests per minute",
    "error": "rate_limit_exceeded",
    "period": "minute",
    "limit": 180,
    "current": 181
}
```

---

## 📊 Usage Analytics

### Get Usage Summary

```bash
GET /admin/usage/summary
```

**Response:**
```json
{
    "summary": [
        {
            "client_id": "uuid",
            "client_name": "Partner ABC",
            "tier": "fantasy.basic",
            "status": "ACTIVE",
            "total_requests": 15234,
            "requests_last_minute": 2,
            "requests_last_hour": 145,
            "requests_last_day": 1523,
            "avg_response_time_ms": 45,
            "last_request_at": "2024-01-04T14:30:00Z"
        }
    ],
    "total_clients": 1
}
```

### Get Client Usage Logs

```bash
GET /admin/usage/{client_id}?limit=100
```

**Response:**
```json
{
    "client_id": "uuid",
    "logs": [
        {
            "id": "uuid",
            "endpoint": "/v1/fantasy/fight-id/fantasy.basic",
            "method": "GET",
            "status_code": 200,
            "timestamp": "2024-01-04T14:30:15Z",
            "response_time_ms": 42,
            "ip_address": "192.168.1.1",
            "user_agent": "Mozilla/5.0..."
        }
    ],
    "total": 100
}
```

---

## 🔧 Setup Instructions

### 1. Run Database Migration

```bash
# Copy migration file
cat /app/datafeed_api/migrations/006_api_key_system.sql

# Paste into Supabase SQL Editor and execute
```

### 2. Verify Demo Keys

```sql
SELECT name, tier, api_key, status 
FROM api_clients 
ORDER BY tier;
```

**Demo Keys Available:**
- `FJAI_PUBLIC_DEMO_001` (public)
- `FJAI_DEV_DEMO_001` (dev)
- `FJAI_FANTASY_BASIC_001` (fantasy.basic)
- `FJAI_FANTASY_ADV_001` (fantasy.advanced)
- `FJAI_SPORTSBOOK_001` (sportsbook.pro)
- `FJAI_ENTERPRISE_001` (promotion.enterprise)

### 3. Test Authentication

```bash
# Test public endpoint (no auth required)
curl "http://localhost:8002/v1/public/fight/fight-id"

# Test authenticated endpoint
curl "http://localhost:8002/v1/fantasy/fight-id/fantasy.basic" \
  -H "X-API-Key: FJAI_FANTASY_BASIC_001"
```

---

## ⚠️ Security Best Practices

1. **Never Expose API Keys** - Keep them secret
2. **Use HTTPS** - Always encrypt in production
3. **Rotate Keys** - Periodically generate new keys
4. **Monitor Usage** - Watch for unusual patterns
5. **Revoke Compromised Keys** - Immediately revoke if exposed
6. **Tier Appropriately** - Give minimum required access

---

## 📚 Files Created

- `/app/datafeed_api/migrations/006_api_key_system.sql` - Database schema
- `/app/datafeed_api/auth/api_key_auth.py` - Auth service
- `/app/datafeed_api/auth/dependencies.py` - FastAPI dependencies
- `/app/datafeed_api/api/admin_routes.py` - Admin API
- `/app/datafeed_api/API_KEY_SYSTEM_GUIDE.md` - This guide

---

## ✅ Status

| Component | Status | Ready |
|-----------|--------|-------|
| Database Schema | ✅ Complete | Yes |
| API Key Generation | ✅ Complete | Yes |
| Authentication | ✅ Complete | Yes |
| RBAC | ✅ Complete | Yes |
| Rate Limiting | ✅ Complete | Yes |
| Usage Logging | ✅ Complete | Yes |
| Admin API | ✅ Complete | Yes |
| Demo Keys | ✅ Seeded | Yes |

**🎉 System is ready for production after migration!**
