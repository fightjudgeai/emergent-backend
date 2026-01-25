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

## Operator UI Enhancements (IMPLEMENTED ✅ 2026-01-24)

### Significant Strike (SS) Mode
- **SS Mode Toggle**: Button in header toggles all strikes to Significant Strikes (2x points)
- **Keyboard shortcut**: Press backtick (`) to toggle SS mode
- **Visual feedback**: Button turns amber when SS mode is ON, strikes show "SS Jab", "SS Cross", etc.
- **Info tooltip**: Explains what SS mode does

### Tooltips on All Buttons
Every event button now has a hover tooltip explaining:
- What the event means
- Point value
- Impact Lock rules (for KD events)

### Control Time Buckets (P1)
- **Quick Add button**: Reveals quick-add control time buckets
- **Time buckets**: +10s, +20s, +30s for Back, Top, Cage control
- **Use case**: When timer wasn't started but control time needs to be logged retroactively

### Keyboard Shortcuts Updated
- **`** (backtick): Toggle SS mode
- **1-7**: Basic strikes (with SS mode support)
- **Q,W,E,R**: Damage events (Rocked, KD Flash, KD Hard, KD NF)
- **V,B**: Takedown, TD Stuffed
- **G**: Ground Strike (with quality toggle)
- **F**: Toggle GnP quality (Solid/Light)
- **A,S,D**: Submissions (Light, Deep, Near-Finish)
- **Z,X,C**: Control timers (Back, Top, Cage)

### Event Type Updates (V3 Engine Alignment)
- "Takedown Landed" → "Takedown"
- "Takedown Defended" → "Takedown Stuffed"  
- "Sub Attempt Standard" → "Sub Light"
- Added all SS event types

## Broadcast Graphics System (IMPLEMENTED ✅ 2026-01-24)

### Features
- **Strike Counter**: Live stats display (Total Strikes, Sig. Strikes, Knockdowns, Takedowns, Control Time)
- **Lower Third Graphics**: Fighter introduction cards with Name, Record, Weight Class, Photo
- **Dual Lower Thirds**: Side-by-side display of both fighters
- **OBS Overlay**: Clean overlay URL for streaming (`/overlay/{boutId}`)
- **Supervisor Controls**: Toggle graphics on/off from dashboard

### URLs
- Arena View: `/pfc50/{boutId}` 
- OBS Overlay: `/overlay/{boutId}`
- Overlay with static params: `/overlay/{boutId}?stats=1&lowerBoth=1`

### Supervisor Controls (Graphics button in dashboard)
- Copy OBS overlay URL
- Toggle Live Strike Stats
- Toggle Both Fighter Cards
- Toggle Red/Blue individual cards
- Hide All / Open Overlay buttons

### Fight Setup Enhancements
- Fighter Record (W-L) field
- Fighter Photo URL (optional)
- All MMA weight classes (Men's, Women's, Catchweight)

### API Endpoints
- `GET /api/overlay/stats/{bout_id}` - Live fight statistics
- `GET /api/broadcast/control/{bout_id}` - Get current control state
- `POST /api/broadcast/control/{bout_id}` - Update control state

## Operator Roles (UPDATED ✅ 2026-01-24)
All 6 operator role options are now available:
- RED_ALL, RED_STRIKING, RED_GRAPPLING
- BLUE_ALL, BLUE_STRIKING, BLUE_GRAPPLING

## Supervisor Event Management (IMPLEMENTED ✅ 2026-01-24)

### Features
- **Edit Events Button**: Green button in supervisor dashboard header opens Event Manager
- **Add Events**: Supervisor can add any event type for either corner
- **Delete Events**: Trash icon visible on ALL events (operator or supervisor logged)
- **Real-time Updates**: Events list refreshes immediately after add/delete

### How to Use
1. Navigate to `/supervisor/{boutId}`
2. **To Add**: Click "Edit Events" → Select corner → Click event button
3. **To Delete**: Click trash icon next to any event in the event lists
4. Score updates automatically

### API Endpoints
- `POST /api/events/supervisor` - Add event as supervisor
- `DELETE /api/events/by-id/{created_at}?bout_id={boutId}` - Delete specific event

### Overview
The scoring engine uses a config-driven, impact-first approach with 5 regularization rules to prevent score inflation from spam.

### Event Catalog & Point Values
| Event Type | Base Points | Category |
|------------|-------------|----------|
| Jab | 1 | Striking |
| SS Jab | 2 | Striking (Significant) |
| Cross | 3 | Striking |
| SS Cross | 6 | Striking (Significant) |
| Hook | 3 | Striking |
| SS Hook | 6 | Striking (Significant) |
| Uppercut | 3 | Striking |
| SS Uppercut | 6 | Striking (Significant) |
| Kick | 3 | Striking |
| SS Kick | 6 | Striking (Significant) |
| Elbow | 4 | Striking |
| SS Elbow | 6 | Striking (Significant) |
| Knee | 4 | Striking |
| SS Knee | 6 | Striking (Significant) |
| Rocked | 60 | Damage (Protected) |
| KD Flash | 100 | Damage (Protected) |
| KD Hard | 150 | Damage (Protected) |
| KD Near-Finish | 210 | Damage (Protected) |
| Takedown | 10 | Grappling |
| TD Stuffed | 5 | Grappling |
| GnP Light | 1 | Ground Strikes |
| GnP Solid | 3 | Ground Strikes |
| Sub Light | 12 | Submissions |
| Sub Deep | 28 | Submissions |
| Sub Near-Finish | 60 | Submissions (Protected) |

### Control Scoring (Time-Bucketed)
| Control Type | Points per 10s |
|--------------|----------------|
| Cage Control | 1 |
| Top Control | 3 |
| Back Control | 5 |

### 5 Regularization Rules

#### Rule 1: Technique Diminishing Returns
Per technique, per fighter, per round:
- Events 1-10: 100% value
- Events 11-20: 75% value
- Events 21+: 50% value

#### Rule 2: SS Abuse Guardrail
All Significant Strikes combined per fighter per round:
- SS 1-8: 100% value
- SS 9-14: 75% value
- SS 15+: 50% value

#### Rule 3: Control Time Diminishing Returns
After 60 seconds continuous control, points drop to 50% value.
Gaps of 15+ seconds reset the continuous streak.

#### Rule 4: Control Without Work Discount
If control points ≥ 20 AND no offensive work (strikes < 10 OR no submission OR GnP hard < 10):
- Control points discounted by 25%

#### Rule 5: TD Stuffed Cap
- First 3 TD Stuffed: 100% value
- TD Stuffed 4+: 50% value

### Impact Lock System
Impact events can "lock" a round win even if opponent has more volume points.

| Lock Type | Trigger Event | Delta Threshold |
|-----------|---------------|-----------------|
| Soft Lock | KD Flash | 50 points |
| Hard Lock | KD Hard | 110 points |
| NF Lock | KD Near-Finish | 150 points |
| Sub NF Lock | Sub Near-Finish | 90 points |

**Lock Logic**: Fighter with impact lock wins UNLESS opponent leads by ≥ threshold.

### Round Scoring (10-Point Must)
- **10-10 Draw**: Delta < 5 and no impact events
- **10-9**: Default when one fighter wins
- **10-8**: Requires 2+ protected events OR delta ≥ 100
- **10-7**: Requires 3+ protected events OR delta ≥ 200

## Key Files

### Scoring Engine (V3)
- `/app/backend/scoring_engine_v2/engine_v3.py` - Main v3 scoring engine
- `/app/backend/scoring_engine_v2/config_v3.py` - Event weights and rules config
- `/app/backend/scoring_engine_v2/__init__.py` - Exports score_round_v3

### Frontend
- `/app/frontend/src/components/SupervisorControl.jsx` - Event/fight creation
- `/app/frontend/src/components/SupervisorDashboardPro.jsx` - Live scoring
- `/app/frontend/src/components/OperatorSimple.jsx` - Event logging

### Backend
- `/app/backend/server.py` - API endpoints (uses v3 engine)

### Tests
- `/app/backend/tests/test_v3_scoring_comprehensive.py` - 38 tests for v3 engine
- `/app/backend/tests/test_scoring_engine_v3.py` - 19 tests for v3 engine

## API Endpoints

### Event Management
- `POST /api/events` - Store event with device_role
- `GET /api/events` - Get ALL events for a bout

### Round Scoring
- `POST /api/rounds/compute` - Server-authoritative scoring (v3 engine)
- `GET /api/rounds` - Get round results

### Fight Management
- `POST /api/fights/finalize` - Calculate winner
- `POST /api/bouts` - Create new bout
- `GET /api/supervisor/fights` - Get fights for event

## URLs / Routes

| Route | Purpose |
|-------|---------|
| `/control` | Supervisor: Create events, add fights, manage operators |
| `/supervisor/{boutId}` | Supervisor: Live scoring dashboard |
| `/op/{boutId}` | Operator: Simple event logging |
| `/waiting/{boutId}` | Operator: Wait for role assignment |
| `/pfc50/{boutId}` | Arena: Broadcast graphics |

## Test Results - V3 Engine (2026-01-23)
- **57/57 tests passed (100%)**
- Event point values verified
- Impact Lock system verified (KD Flash, KD Hard)
- All 5 regularization rules verified
- 10-8 scoring logic verified
- API integration verified

## Upcoming Tasks

### P0 - Operator UI Updates
- Add buttons for all new "significant strike" (SS) events
- Add tooltips explaining SS, KD NF, etc. definitions
- Implement control time-bucket clicking on operator screen

### P1 - Additional Testing
- Add more edge case tests for control scoring
- Add tests for Rule 3 (control diminishing returns)
- Add tests for Rule 4 (control without work)

### P2 - Firebase Migration
- Remove Firebase dependencies from legacy components
- Migrate EventSetup.jsx, FightList.jsx to MongoDB backend

### P3 - Backend Refactoring
- Break down server.py into modular structure (/routes, /models, /services)

## Future Tasks (Backlog)

### Fan Engagement App
- Build separate mobile-friendly web app for fans
- QR code scanning for live score submission
- Display fan scores on big screen

### Product Enhancements
- Live Score Reveal Animation
- Sponsored Scorecard Frame
- Round-by-round statistics display
