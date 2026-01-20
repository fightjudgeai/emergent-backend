# Fight Judge AI - Product Requirements Document

## Original Problem Statement
Building a real-time sports data feed service focused on MMA/Combat sports judging. The application provides:
1. Operator Panel for real-time event logging during fights
2. Supervisor Dashboard for combined scoring display
3. Broadcast displays for arena screens (PFC 50 ready)
4. Fight completion and archival system

**CRITICAL REQUIREMENT**: Multiple operators on different laptops scoring different aspects of the same fight. All events logged combine in real-time on a single Supervisor Dashboard to produce ONE unified score.

## Current Architecture (Supervisor-Centric Polling System)

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
              │    /control (setup)             │
              │    /supervisor/{boutId}         │
              │                                 │
              │  Polls every 500ms              │
              │  Shows ALL events combined      │
              │  END ROUND / FINALIZE buttons   │
              │  Controls Arena View            │
              └─────────────────────────────────┘
```

### 3 Operator Roles:
1. **RED_STRIKING** - Track punches, kicks, elbows, knees, knockdowns for RED
2. **RED_GRAPPLING** - Track takedowns, submissions, sweeps, control for RED
3. **BLUE_ALL** - Track ALL events (striking + grappling) for BLUE

## What's Been Implemented

### 2026-01-17 - Complete Supervisor-Centric System

1. **Supervisor Control Page** (`/control`) - VERIFIED ✅
   - Create events with localStorage persistence
   - Add fights with fighter names, weight class, rounds
   - Start/activate fights
   - Connected operators display
   - Navigate to scoring dashboard

2. **Simple Operator View** (`/op/{boutId}`) - VERIFIED ✅
   - Simplified striking buttons (Jab, Cross, Hook - NO "SS" prefix)
   - Clean button grid for event logging
   - Color-coded by event type/severity
   - Round synced from supervisor
   - Toast notifications for logged events
   - Events sent directly to server API

3. **Supervisor Dashboard Pro** (`/supervisor/{boutId}`) - VERIFIED ✅
   - Polls server every 500ms
   - Shows combined events from ALL operators
   - Delta scoring breakdown
   - Net round score projections
   - "END ROUND" / "FINALIZE FIGHT" buttons
   - Operator assignment panel
   - Arena View dialog with broadcast graphics
   - Round scores display

4. **Operator Waiting Room** (`/waiting/{boutId}`) - COMPLETED
   - Operators register and wait for role assignment
   - Supervisor assigns roles from control panel

5. **Backend Unified Scoring API** - COMPLETED
   - `POST /api/events` - Store event with device_role
   - `GET /api/events` - Get ALL events
   - `POST /api/rounds/compute` - Server-authoritative scoring
   - `GET /api/rounds` - Get round results
   - `POST /api/fights/finalize` - Calculate winner
   - `POST /api/bouts` - Create new bout
   - `GET /api/supervisor/fights` - Get fights for event
   - `POST /api/supervisor/activate-fight` - Activate a fight
   - `POST /api/operators/register` - Operator registration
   - `POST /api/operators/assign` - Assign role to operator

## URLs / Routes

| Route | Purpose |
|-------|---------|
| `/control` | Supervisor: Create events, add fights, manage operators |
| `/supervisor/{boutId}` | Supervisor: Live scoring dashboard |
| `/op/{boutId}` | Operator: Simple event logging |
| `/waiting/{boutId}` | Operator: Wait for role assignment |
| `/operator-setup` | Legacy: Manual role selection |
| `/pfc50/{boutId}` | Arena: Broadcast graphics |

## How to Use (Fight Night)

1. **Setup (Before Fight)**
   - Supervisor opens `/control`
   - Create event (e.g., "PFC 50")
   - Add fights with fighter names and rounds
   - Click "Start" on the first fight

2. **Operator Connection**
   - Each operator laptop opens `/waiting/{boutId}`
   - Operators register with their device name
   - Supervisor assigns roles from `/control`
   - Operators automatically redirected to `/op/{boutId}`

3. **During Round**
   - Operators tap buttons to log events
   - Supervisor Dashboard shows combined totals in real-time (500ms polling)

4. **End of Round**
   - Supervisor clicks "END ROUND" on `/supervisor/{boutId}`
   - Server computes score from ALL events
   - Score displayed on dashboard

5. **End of Fight**
   - After final round, Supervisor clicks "FINALIZE FIGHT"
   - Winner determined and displayed

## Key Files

### Frontend
- `/app/frontend/src/components/SupervisorControl.jsx` - Event/fight creation
- `/app/frontend/src/components/SupervisorDashboardPro.jsx` - Live scoring
- `/app/frontend/src/components/OperatorSimple.jsx` - Event logging
- `/app/frontend/src/components/OperatorWaiting.jsx` - Operator waiting room
- `/app/frontend/src/components/OperatorAssignmentPanel.jsx` - Role assignment

### Backend
- `/app/backend/server.py` - API endpoints
- `/app/backend/unified_scoring.py` - Delta scoring logic

## Test Results - Iteration 5 (2026-01-20)
- Frontend: 5/5 tests passed (100%)
- Round broadcast feature verified ✅
- Round review dialog verified ✅
- Round count display (both 3 and 5 rounds) verified ✅
- Fixed API endpoint bug: /api/unified/events → /api/events

## Recent Updates (2026-01-20)

### P0 - Round Broadcast Feature (COMPLETED ✅)
- Added "Show Round Result on Arena" button to round end dialog
- Implemented RoundWinner broadcast overlay using FightJudgeAI.jsx component
- Shows round number, scores (red/blue), and winner name
- Fullscreen overlay with professional styling

### Bug Fix - API Endpoint (COMPLETED ✅)
- Fixed: fetchRoundForReview was calling /api/unified/events (404) instead of /api/events
- Round review dialog now works correctly

### Verified - Round Count Display (WORKING ✅)
- Both 5-round and 3-round fights display correctly in /control page
- API returns correct totalRounds value
- Frontend displays correct "X rds" in fight cards

## Future/Backlog Tasks

### P2 - Firebase Migration
- Remove Firebase dependencies from legacy components
- Migrate EventSetup.jsx, FightList.jsx to MongoDB backend

### P2 - Visual Improvements
- Add larger role indicator banner on OperatorSimple.jsx

### P3 - Backend Refactoring
- Break down server.py into modular structure (/routes, /models, /services)

### P3 - Cleanup
- Remove obsolete components (OperatorPanel.jsx, JudgePanel.jsx, CombinedSyncPanel.jsx)
- Remove deprecated datafeed_api directory
