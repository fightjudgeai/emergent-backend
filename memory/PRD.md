# Fight Judge AI - Product Requirements Document

## Original Problem Statement
Building a real-time sports data feed service focused on MMA/Combat sports judging. The application provides:
1. Operator Panel for real-time event logging during fights
2. Judge Panel for scoring rounds
3. Broadcast displays for arena screens (PFC 50 ready)
4. Fight completion and archival system
5. Fight history for reviewing past fights

**CRITICAL REQUIREMENT**: Four operators on different laptops scoring different aspects of the same fight (e.g., Red Striking, Red Grappling, Blue Striking, Blue Grappling). All events logged by these operators must be combined in real-time on the server to produce ONE unified, official score.

## Architecture

### Backend Systems
- **Primary Backend**: `/app/backend/server.py` (MongoDB) - ACTIVE
- **Unified Scoring Engine**: `/app/backend/unified_scoring.py` - Delta-based scoring logic
- **Deprecated**: `/app/datafeed_api/` (Supabase/Postgres) - NOT IN USE

### Frontend
- React application at `/app/frontend`
- Components for Operator Panel, Judge Panel, Broadcast Display, Fight History
- **Lovable Broadcast Components** - Premium visual effects for arena display at `/pfc50`

## What's Been Implemented

### 2026-01-17 Session - Server-Authoritative Unified Scoring System (COMPLETED)

1. **WebSocket Real-Time Updates** (COMPLETED)
   - WebSocket endpoint at `/api/ws/unified/{bout_id}`
   - Connection manager for all operator laptops
   - Real-time broadcast of events, round computations, and fight finalization
   - All connected clients receive SAME data from server

2. **Unified Events API** (COMPLETED)
   - `POST /api/events` - Create event with device_role tagging
   - `GET /api/events` - Get ALL events (NO device filter)
   - Events stored with device_role for auditing only
   - Auto-creates bout if doesn't exist

3. **Server-Authoritative Round Computation** (COMPLETED)
   - `POST /api/rounds/compute` - Computes from ALL events, ALL devices
   - `GET /api/rounds` - Get all computed round results
   - Idempotent (safe to call multiple times)
   - Uses delta-based scoring system

4. **Fight Finalization** (COMPLETED)
   - `POST /api/fights/finalize` - Calculate final winner
   - `GET /api/fights/{bout_id}/result` - Get fight result

5. **Frontend Hooks** (COMPLETED)
   - `useUnifiedScoring.js` - WebSocket-based real-time hook
   - `CombinedSyncPanel.jsx` - Updated to use new hook
   - `OperatorPanel.jsx` - Updated to use unified API as primary

### Test Results (2026-01-17)
- **18/18 tests passed (100% success rate)**
- All device roles (RED_STRIKING, RED_GRAPPLING, BLUE_STRIKING, BLUE_GRAPPLING) combine correctly
- Delta scoring system working with correct event values
- WebSocket broadcasts functioning

### Previous Sessions
1. **Fixed Broadcast Connection Error** (COMPLETED)
2. **Enhanced BoutSelector Component** (COMPLETED)
3. **Lovable Broadcast Components Integrated** (COMPLETED)

## Server-Authoritative Scoring Architecture

### Core Principle
The SERVER is the SINGLE SOURCE OF TRUTH for all scoring data. Operator laptops are "thin clients" that:
1. Send events to the server
2. Display state provided by the server
3. NEVER compute scores locally

### Data Flow
```
Operator 1 (RED_STRIKING) ──┐
Operator 2 (RED_GRAPPLING) ──┼──> Server (MongoDB) ──> WebSocket Broadcast ──> ALL Operators
Operator 3 (BLUE_STRIKING) ──┤                                                see SAME data
Operator 4 (BLUE_GRAPPLING) ─┘
```

### Device Roles
- `RED_STRIKING` - Tracks Red corner striking events
- `RED_GRAPPLING` - Tracks Red corner grappling events
- `BLUE_STRIKING` - Tracks Blue corner striking events
- `BLUE_GRAPPLING` - Tracks Blue corner grappling events

## API Endpoints

### Unified Scoring API (V2)
- `POST /api/events` - Create event (broadcasts via WebSocket)
- `GET /api/events?bout_id=X&round_number=Y` - Get ALL events
- `POST /api/rounds/compute` - Compute round score (server-authoritative)
- `GET /api/rounds?bout_id=X` - Get all round results
- `POST /api/fights/finalize` - Finalize fight
- `GET /api/fights/{bout_id}/result` - Get fight result
- `WS /api/ws/unified/{bout_id}` - WebSocket for real-time updates

### Bout Management
- `GET /api/bouts` - List all bouts
- `GET /api/bouts/active` - List active bouts only
- `POST /api/bouts` - Create new bout
- `GET /api/bouts/{bout_id}` - Get specific bout

### Broadcast
- `GET /api/live/{bout_id}` - Live scoring data (used by Lovable)

## Key Files

### Backend
- `/app/backend/server.py` - Main FastAPI server with WebSocket
- `/app/backend/unified_scoring.py` - Delta-based scoring logic

### Frontend
- `/app/frontend/src/hooks/useUnifiedScoring.js` - WebSocket hook
- `/app/frontend/src/components/CombinedSyncPanel.jsx` - Unified display
- `/app/frontend/src/components/OperatorPanel.jsx` - Event logging
- `/app/frontend/src/components/LovableBroadcast.jsx` - Arena display

## Delta Scoring System

### Event Values
| Event Type | Value | Notes |
|------------|-------|-------|
| KD (Near-Finish) | 100.0 | Highest impact |
| KD (Hard) | 70.0 | |
| KD (Flash) | 40.0 | |
| Rocked/Stunned | 30.0 | |
| Takedown | 25.0 | |
| Cross/Hook/Uppercut/Elbow (sig) | 14.0 | |
| Head Kick (sig) | 15.0 | |
| Jab (sig) | 10.0 | |
| Submission Attempt (Near-Finish) | 100.0 | |
| Submission Attempt (Deep) | 60.0 | |

### Round Score Mapping
- Delta ≤ 3.0: 10-10 DRAW
- Delta < 140.0: 10-9 (standard)
- Delta < 200.0: 10-8 (dominant)
- Delta ≥ 200.0: 10-7 (extreme)

## Database Collections

### unified_events
```javascript
{
  bout_id: String,
  round_number: Number,
  corner: "RED" | "BLUE",
  aspect: "STRIKING" | "GRAPPLING",
  event_type: String,
  value: Number,
  device_role: String,
  metadata: Object,
  created_at: DateTime,
  created_by: String  // For audit only
}
```

### round_results
```javascript
{
  bout_id: String,
  round_number: Number,  // Unique compound key
  red_points: Number,
  blue_points: Number,
  delta: Number,
  red_total: Number,
  blue_total: Number,
  red_breakdown: Object,
  blue_breakdown: Object,
  total_events: Number
}
```

### fight_results
```javascript
{
  bout_id: String,  // Unique
  final_red: Number,
  final_blue: Number,
  winner: "RED" | "BLUE" | "DRAW",
  winner_name: String,
  rounds: Array
}
```

## Known Issues
1. **Firebase/MongoDB Sync**: Legacy components still use Firebase. EventSetup uses Firebase while broadcast uses MongoDB.
2. **datafeed_api**: The old Supabase backend is completely non-functional.

## Future Tasks (P2+)
- [ ] Full Firebase migration for remaining pages (EventSetup, FightList)
- [ ] Deprecate `/app/datafeed_api/` directory
- [ ] Add fighter photos to unified scoring display
- [ ] Implement operator authentication/authorization
