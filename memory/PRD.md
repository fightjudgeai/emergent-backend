# Fight Judge AI - Product Requirements Document

## Original Problem Statement
Building a real-time sports data feed service focused on MMA/Combat sports judging. The application provides:
1. Operator Panel for real-time event logging during fights
2. Judge Panel for scoring rounds
3. Broadcast displays for arena screens
4. Fight completion and archival system

## Architecture

### Backend Systems
- **Primary Backend**: `/app/backend/server.py` (MongoDB) - ACTIVE
- **Secondary Backend**: `/app/datafeed_api` (Supabase/Postgres) - NON-FUNCTIONAL (pending migrations)

### Frontend
- React application at `/app/frontend`
- Components for Operator Panel, Judge Panel, Broadcast Display

## What's Been Implemented

### 2025-01-16 Session
1. **End Fight Button on Operator Panel** (P0 - COMPLETED)
   - Added 'End Fight' button next to 'Next Round' button
   - Button navigates to Judge Panel with `mode=end-fight` parameter
   - Auto-displays final scores when in end-fight mode

2. **Fight Completion API** (P2 - COMPLETED)
   - Added `/api/fight/complete/{bout_id}` endpoint
   - Added `/api/fight/completed/{bout_id}` endpoint
   - Added `/api/fights/completed` for listing all completed fights
   - Integrated `fight_completion.py` into server.py

3. **Judge Panel End-Fight Mode** (COMPLETED)
   - Added URL parameter handling for `mode=end-fight`
   - Auto-displays final results when navigating from Operator Panel

### Previous Sessions (from handoff)
- Scoring System: Percentage-based model with categories (Striking 50%, Grappling 40%, Other 10%)
- Operator Panel: Kick, SS Kick, Guard Passing buttons, keyboard shortcuts
- Broadcast UI: RoundWinner, FinalResult components from lovable.dev integration
- Judge Panel: End Round/End Fight buttons with broadcast display

## Pending Issues

### P1 - Critical
- **datafeed_api Backend Non-Functional**: Database migrations in `/app/datafeed_api/migrations/` have not been run. This blocks API Key system, Billing, and Public Stats API features.

### P2 - Medium
- Control Time Logic: Calculate fighter control time from CTRL_START/CTRL_END events (not fully implemented)

## Upcoming Tasks
1. Clarify if `datafeed_api` features are still needed
2. If yes, guide user to run SQL migrations
3. Implement control time calculation logic

## Key Files
- `/app/frontend/src/components/OperatorPanel.jsx` - Main operator interface
- `/app/frontend/src/components/JudgePanel.jsx` - Judge scoring interface
- `/app/backend/server.py` - Active backend (MongoDB)
- `/app/backend/fight_completion.py` - Fight archival logic
- `/app/frontend/src/components/broadcast/` - Broadcast display components

## API Endpoints (MongoDB Backend)
- `POST /api/calculate-score-v2` - New scoring engine
- `POST /api/fight/complete/{bout_id}` - Complete and archive fight
- `GET /api/fight/completed/{bout_id}` - Get archived fight data
- `GET /api/fights/completed` - List all completed fights
- `GET /api/final/{bout_id}` - Final broadcast data

## Database Collections (MongoDB)
- `bouts` - Fight information
- `events` - Real-time event log
- `judge_scores` - Judge scorecards
- `completed_fights` - Archived fight data
