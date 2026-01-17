# Fight Judge AI - Product Requirements Document

## Original Problem Statement
Building a real-time sports data feed service focused on MMA/Combat sports judging. The application provides:
1. Operator Panel for real-time event logging during fights
2. Supervisor Dashboard for combined scoring display
3. Broadcast displays for arena screens (PFC 50 ready)
4. Fight completion and archival system

**CRITICAL REQUIREMENT**: Multiple operators on different laptops scoring different aspects of the same fight. All events logged combine in real-time on a single Supervisor Dashboard to produce ONE unified score.

## Current Architecture (Option A - Single Scorekeeper Screen)

### Device Setup (4 devices total):
```
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  LAPTOP 1       │  │  LAPTOP 2       │  │  LAPTOP 3       │
│  Red Striking   │  │  Red Grappling  │  │  Blue All       │
│  /op/{boutId}   │  │  /op/{boutId}   │  │  /op/{boutId}   │
└────────┬────────┘  └────────┬────────┘  └────────┬────────┘
         │                    │                    │
         └────────────────────┴────────────────────┘
                              │
                              ▼
                     ┌─────────────────┐
                     │     SERVER      │
                     │   (MongoDB)     │
                     └────────┬────────┘
                              │
                              ▼
              ┌─────────────────────────────────┐
              │    LAPTOP 4 (SUPERVISOR)        │
              │    /supervisor/{boutId}         │
              │                                 │
              │  Polls every 500ms              │
              │  Shows ALL events combined      │
              │  END ROUND / FINALIZE buttons   │
              │  Streams to arena big screen    │
              └─────────────────────────────────┘
```

### 3 Operator Roles:
1. **RED_STRIKING** - Track punches, kicks, elbows, knees, knockdowns for RED
2. **RED_GRAPPLING** - Track takedowns, submissions, sweeps, control for RED
3. **BLUE_ALL** - Track ALL events (striking + grappling) for BLUE

## What's Been Implemented

### 2026-01-17 Session - Complete Multi-Operator System

1. **Operator Setup Page** (`/operator-setup`) - COMPLETED
   - 3 role selection cards with visual previews
   - Operator name input
   - Bout ID selection/input
   - Navigates to simple operator view

2. **Simple Operator View** (`/op/{boutId}`) - COMPLETED
   - Clean button grid for event logging
   - Color-coded by event type/severity
   - Round navigation
   - Events sent directly to server API
   - No local scoring computation

3. **Supervisor Dashboard** (`/supervisor/{boutId}`) - COMPLETED
   - Polls server every 500ms
   - Shows combined events from ALL operators
   - Split-screen Red vs Blue display
   - "END ROUND" button → server computes score
   - "NEXT ROUND" button
   - "FINALIZE FIGHT" button
   - Round scores display
   - Running totals
   - Fullscreen mode for arena streaming

4. **Backend Unified Scoring API** - COMPLETED
   - `POST /api/events` - Store event with device_role
   - `GET /api/events` - Get ALL events (no device filter)
   - `POST /api/rounds/compute` - Server-authoritative scoring
   - `GET /api/rounds` - Get round results
   - `POST /api/fights/finalize` - Calculate winner

## URLs / Routes

| Route | Purpose |
|-------|---------|
| `/operator-setup` | Configure device role before scoring |
| `/op/{boutId}` | Simple operator event logging |
| `/supervisor/{boutId}` | Combined scoring dashboard |
| `/supervisor` | Supervisor dashboard (enter bout ID) |

## How to Use (Fight Night)

1. **Setup (Before Fight)**
   - Create bout via API or existing bout management
   - Each operator opens `/operator-setup` on their laptop
   - Operator 1: Select "Red Striking", enter bout ID, start
   - Operator 2: Select "Red Grappling", enter bout ID, start
   - Operator 3: Select "Blue All", enter bout ID, start
   - Supervisor opens `/supervisor/{boutId}` on 4th laptop

2. **During Round**
   - Operators tap buttons to log events
   - Supervisor Dashboard shows combined totals in real-time (500ms polling)

3. **End of Round**
   - Supervisor clicks "END ROUND"
   - Server computes score from ALL events
   - Score displayed on dashboard
   - Supervisor clicks "NEXT ROUND"

4. **End of Fight**
   - After final round, Supervisor clicks "FINALIZE FIGHT"
   - Winner determined and displayed

## Key Files

### Frontend
- `/app/frontend/src/components/OperatorSetup.jsx` - Role selection
- `/app/frontend/src/components/OperatorSimple.jsx` - Event logging
- `/app/frontend/src/components/SupervisorDashboard.jsx` - Combined view

### Backend
- `/app/backend/server.py` - API endpoints
- `/app/backend/unified_scoring.py` - Delta scoring logic

## Test Results
- Backend: 18/18 tests passed (100%)
- Supervisor Dashboard: Showing events from operators ✅
- Polling sync: Working every 500ms ✅
