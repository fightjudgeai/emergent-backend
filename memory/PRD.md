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

### Frontend
- React application at `/app/frontend`
- Components for Operator Panel, Judge Panel, Broadcast Display, Fight History
- **NEW: Lovable Broadcast Components** - Premium visual effects for arena display

## What's Been Implemented

### 2025-01-16 Session - Lovable Integration
1. **Lovable Broadcast Components Integrated** (COMPLETED)
   - Created `/app/frontend/src/components/lovable-broadcast/` with all components
   - BroadcastScorecard, TopBar, FighterHeader, ScoreGrid, FinalResult, RoundWinner
   - SignalLostOverlay, StandbyScreen, ConnectionIndicator, DemoModeControls
   - Custom CSS with PFC 50 gold/cyan color scheme

2. **New Routes Added**
   - `/pfc50` - Demo mode for Lovable broadcast
   - `/pfc50/:boutId` - Live mode connected to bout

3. **Hooks Created**
   - `useFightJudgeAPI.js` - Connects to backend `/api/live/{bout_id}`
   - `useDemoMode.js` - Demo simulation for testing

### Previous Session
- Fighter Photos Support in EventSetup
- Offline Capability with localStorage caching
- End Fight Dialog with method selection (KO, TKO, SUB, etc.)
- Increased fight limit to 25 per event

## PFC 50 Live Broadcast Setup

### URLs for Arena Display:
- **Lovable Display (Premium)**: `/pfc50/{boutId}` 
- **Standard Display**: `/arena/{boutId}`

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

## Key Files
- `/app/frontend/src/components/LovableBroadcast.jsx` - Main Lovable page
- `/app/frontend/src/components/lovable-broadcast/` - All Lovable components
- `/app/frontend/src/hooks/useFightJudgeAPI.js` - Backend connection
- `/app/frontend/src/styles/lovable-broadcast.css` - Custom styles
- `/app/backend/server.py` - API with `/api/live/{bout_id}`

## API Endpoints
- `GET /api/live/{bout_id}` - Live scoring data (used by Lovable)
- `GET /api/final/{bout_id}` - Final results
- `POST /api/fight/complete/{bout_id}` - Archive completed fight

## Color Scheme (Lovable)
- Gold/Cyan: `hsl(195, 100%, 70%)`
- Accent Gold: `hsl(43, 85%, 55%)`
- Corner Red: `hsl(348, 83%, 47%)`
- Corner Blue: `hsl(225, 73%, 57%)`
