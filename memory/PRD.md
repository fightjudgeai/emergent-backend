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
- **Secondary Backend**: `/app/datafeed_api` (Supabase/Postgres) - NOT NEEDED (user confirmed)

### Frontend
- React application at `/app/frontend`
- Components for Operator Panel, Judge Panel, Broadcast Display, Fight History

## What's Been Implemented

### 2025-01-16 Session - PFC 50 Prep
1. **Fighter Photos Support** (COMPLETED)
   - EventSetup now has photo URL fields for both fighters
   - BroadcastDisplay shows fighter photos in circular frames

2. **Offline Capability** (COMPLETED)
   - BroadcastDisplay caches data to localStorage
   - Shows "OFFLINE MODE" banner when disconnected
   - Automatically uses cached data if connection fails
   - Faster polling (2 second refresh rate)

3. **Enhanced Broadcast Display** (COMPLETED)
   - Responsive design for various screen sizes
   - Larger fonts for arena visibility
   - Fighter photos with colored borders (red/blue)
   - Live status indicator with round number
   - Round-by-round score history

4. **End Fight Dialog with Method Selection** (COMPLETED)
   - Winner selection (Fighter 1, Fighter 2, or Draw)
   - Methods: KO, TKO, Submission, Unanimous/Split/Majority Dec, Draw

5. **Increased Fight Limit** (COMPLETED)
   - Now supports up to 25 fights per event

### Previous Sessions
- Scoring System: Percentage-based model
- Operator Panel: Kick, SS Kick, Guard Passing buttons
- Judge Panel: End Round/End Fight buttons

## PFC 50 Live Broadcast Setup

### How to Use:
1. **Setup Event**: Create event and add all 25 fights with fighter names + photo URLs
2. **Operator PC**: Open `/operator/{boutId}` to log events
3. **Arena Display PC**: Open `/arena/{boutId}` in full-screen browser
4. **Judges**: Each judge opens `/judge/{boutId}` on their device

### Offline Backup:
- If internet drops, display will show cached scores
- "OFFLINE MODE" banner appears at top
- Scores resume updating when connection restores

### Key URLs for PFC 50:
- Arena Display: `{your-url}/arena/{boutId}`
- Operator Panel: `{your-url}/operator/{boutId}`
- Judge Panel: `{your-url}/judge/{boutId}`

## Key Files
- `/app/frontend/src/components/BroadcastDisplay.jsx` - Arena display with photos + offline
- `/app/frontend/src/components/OperatorPanel.jsx` - Event logging + End Fight
- `/app/frontend/src/components/EventSetup.jsx` - 25 fights + photo URLs
- `/app/backend/server.py` - Live API with fighter photos

## API Endpoints
- `GET /api/live/{bout_id}` - Live data for broadcast (includes fighter photos)
- `POST /api/fight/complete/{bout_id}` - Archive completed fight
- `GET /api/fights/completed` - List archived fights

## Fight End Methods
- KO, TKO, SUB, UNANIMOUS_DEC, SPLIT_DEC, MAJORITY_DEC, DRAW

## Database (MongoDB)
- `bouts` - Fight info (fighter1, fighter2, fighter1Photo, fighter2Photo, winner, method)
- `events` - Real-time event log
- `completed_fights` - Archived fights
