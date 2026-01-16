# Fight Judge AI - Product Requirements Document

## Original Problem Statement
Building a real-time sports data feed service focused on MMA/Combat sports judging. The application provides:
1. Operator Panel for real-time event logging during fights
2. Judge Panel for scoring rounds
3. Broadcast displays for arena screens
4. Fight completion and archival system
5. Fight history for reviewing past fights

## Architecture

### Backend Systems
- **Primary Backend**: `/app/backend/server.py` (MongoDB) - ACTIVE
- **Secondary Backend**: `/app/datafeed_api` (Supabase/Postgres) - NON-FUNCTIONAL (pending migrations)

### Frontend
- React application at `/app/frontend`
- Components for Operator Panel, Judge Panel, Broadcast Display, Fight History

## What's Been Implemented

### 2025-01-16 Session (Latest)
1. **End Fight Button with Method Selection** (COMPLETED)
   - Removed CV Systems and Show Monitoring buttons from Operator Panel
   - Added comprehensive "End Fight" dialog with:
     - Winner selection (Fighter 1, Fighter 2, or Draw)
     - Method selection: KO, TKO, Submission, Unanimous Dec, Split Dec, Majority Dec, Draw
   - Saves fight result to database and opens Judge Panel for final scores

2. **Increased Fight Limit** (COMPLETED)
   - EventSetup now allows up to 25 fights per event (previously 15)

3. **Fight History Page** (`/fight-history`) (COMPLETED)
   - Displays all completed/archived fights with search functionality

4. **Fight Details Archived Page** (`/fight-details/:boutId`) (COMPLETED)
   - Detailed fighter statistics comparison

### Previous in this Session
- End Fight Button on Operator Panel navigating to Judge Panel
- Fight Completion API endpoints
- Judge Panel End-Fight Mode with auto-display of final scores

### Previous Sessions (from handoff)
- Scoring System: Percentage-based model with categories (Striking 50%, Grappling 40%, Other 10%)
- Operator Panel: Kick, SS Kick, Guard Passing buttons, keyboard shortcuts
- Broadcast UI: RoundWinner, FinalResult components
- Judge Panel: End Round/End Fight buttons with broadcast display

## Pending Issues

### P1 - Critical
- **datafeed_api Backend Non-Functional**: Database migrations not run

### P2 - Medium
- Control Time Logic: Calculate fighter control time from CTRL_START/CTRL_END events

## Key Files
- `/app/frontend/src/components/OperatorPanel.jsx` - Main operator interface with End Fight dialog
- `/app/frontend/src/components/JudgePanel.jsx` - Judge scoring interface
- `/app/frontend/src/components/EventSetup.jsx` - Event creation (25 fights max)
- `/app/frontend/src/components/FightHistory.jsx` - Fight history list
- `/app/frontend/src/components/FightDetailsArchived.jsx` - Detailed fight stats
- `/app/backend/server.py` - Active backend (MongoDB)

## API Endpoints (MongoDB Backend)
- `POST /api/calculate-score-v2` - New scoring engine
- `POST /api/fight/complete/{bout_id}` - Complete and archive fight
- `GET /api/fight/completed/{bout_id}` - Get archived fight data
- `GET /api/fights/completed` - List all completed fights

## Routes
- `/fight-history` - Browse all completed fights
- `/fight-details/:boutId` - View detailed archived fight stats
- `/operator/:boutId` - Operator panel with End Fight dialog
- `/judge/:boutId` - Judge panel (supports `?mode=end-fight`)

## Fight End Methods Supported
- KO (Knockout)
- TKO (Technical Knockout)
- SUB (Submission)
- UNANIMOUS_DEC (Unanimous Decision)
- SPLIT_DEC (Split Decision)
- MAJORITY_DEC (Majority Decision)
- DRAW

## Database Collections (MongoDB)
- `bouts` - Fight information (includes winner, method, status)
- `events` - Real-time event log
- `judge_scores` - Judge scorecards
- `completed_fights` - Archived fight data
