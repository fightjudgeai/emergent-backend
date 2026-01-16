# Fight Judge AI - Product Requirements Document

## Original Problem Statement
Building a real-time sports data feed service focused on MMA/Combat sports judging. The application provides:
1. Operator Panel for real-time event logging during fights
2. Judge Panel for scoring rounds
3. Broadcast displays for arena screens (PFC 50 ready)
4. Fight completion and archival system
5. Fight history for reviewing past fights

## Architecture

### Backend Systems
- **Primary Backend**: `/app/backend/server.py` (MongoDB) - ACTIVE
- **Deprecated**: `/app/datafeed_api/` (Supabase/Postgres) - NOT IN USE

### Frontend
- React application at `/app/frontend`
- Components for Operator Panel, Judge Panel, Broadcast Display, Fight History
- **Lovable Broadcast Components** - Premium visual effects for arena display at `/pfc50`

## What's Been Implemented

### 2026-01-16 Session - Bug Fixes & Enhancements
1. **Fixed Broadcast Connection Error** (COMPLETED)
   - Added missing `/api/bouts` and `/api/bouts/active` endpoints
   - Added `/api/bouts/{bout_id}` for individual bout retrieval
   - Added `/api/bouts/{bout_id}/round-score` for updating scores
   - Added `/api/bouts/{bout_id}/status` for status updates
   - Bouts can now be created directly in MongoDB for broadcast display

2. **Enhanced BoutSelector Component** (COMPLETED)
   - Added "New" button to create bouts directly from broadcast UI
   - Added "Create New Bout - PFC 50" dialog
   - Auto-connects to newly created bouts
   - Dropdown shows all active bouts from MongoDB

### Previous Session - Lovable Integration
1. **Lovable Broadcast Components Integrated** (COMPLETED)
   - Created `/app/frontend/src/components/lovable-broadcast/` with all components
   - BroadcastScorecard, TopBar, FighterHeader, ScoreGrid, FinalResult, RoundWinner
   - SignalLostOverlay, StandbyScreen, ConnectionIndicator, DemoModeControls
   - Custom CSS with PFC 50 gold/cyan color scheme

2. **Hooks Created**
   - `useFightJudgeAPI.js` - Connects to backend `/api/live/{bout_id}`
   - `useDemoMode.js` - Demo simulation for testing

3. **Additional Features**
   - Fighter Photos Support in EventSetup
   - Offline Capability with localStorage caching
   - End Fight Dialog with method selection (KO, TKO, SUB, etc.)
   - Increased fight limit to 25 per event

## PFC 50 Live Broadcast Setup

### URLs for Arena Display:
- **Lovable Display (Premium)**: `/pfc50` or `/pfc50/{boutId}`
- **Standard Display**: `/arena/{boutId}`

### Quick Start for PFC 50:
1. Go to `/pfc50` in browser
2. Click "New" button in top bar
3. Enter fighter names, rounds, division
4. Click "Create & Connect"
5. Press F for fullscreen

### How to Use at PFC 50:
1. **Arena Display PC**: Open `/pfc50/{boutId}` in full-screen Chrome (press F)
2. **Controls Panel**: Click gear icon (bottom-left) to access display controls
3. **Demo Mode**: Test visuals before going live
4. **Live Mode**: Switch to "Live" and scores auto-update from backend

### Display Modes:
- **Scores**: Show live round-by-round scoring
- **R1/R2/R3**: Show round winner announcement
- **Final**: Show fight winner with totals

### Keyboard Shortcuts:
- **F**: Toggle fullscreen
- **Ctrl+Shift+R**: Emergency refresh

## API Endpoints

### Bout Management
- `GET /api/bouts` - List all bouts
- `GET /api/bouts/active` - List active bouts only
- `POST /api/bouts` - Create new bout
- `GET /api/bouts/{bout_id}` - Get specific bout
- `PUT /api/bouts/{bout_id}/round-score` - Update round score
- `PUT /api/bouts/{bout_id}/status` - Update bout status

### Broadcast
- `GET /api/live/{bout_id}` - Live scoring data (used by Lovable)
- `GET /api/final/{bout_id}` - Final results

### Fight Completion
- `POST /api/fight/complete/{bout_id}` - Archive completed fight

## Key Files
- `/app/frontend/src/components/LovableBroadcast.jsx` - Main Lovable page
- `/app/frontend/src/components/lovable-broadcast/BoutSelector.jsx` - Bout selection and creation
- `/app/frontend/src/hooks/useFightJudgeAPI.js` - Backend connection
- `/app/frontend/src/styles/lovable-broadcast.css` - Custom styles
- `/app/backend/server.py` - API with bout management and broadcast endpoints

## Color Scheme (Lovable)
- Gold/Cyan: `hsl(195, 100%, 70%)`
- Accent Gold: `hsl(43, 85%, 55%)`
- Corner Red: `hsl(348, 83%, 47%)`
- Corner Blue: `hsl(225, 73%, 57%)`

## Known Issues
1. **Firebase/MongoDB Sync**: EventSetup uses Firebase, broadcast uses MongoDB. Manual bout creation needed for broadcast.
2. **datafeed_api**: The old Supabase backend is completely non-functional and should be removed.

## Future Tasks
- Implement WebSocket for real-time updates (currently using polling)
- Consolidate Firebase and MongoDB data flows
- Remove deprecated `/app/datafeed_api/` directory
- Add fighter control time calculation
