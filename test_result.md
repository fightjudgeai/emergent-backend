#====================================================================================================
# START - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================

# THIS SECTION CONTAINS CRITICAL TESTING INSTRUCTIONS FOR BOTH AGENTS
# BOTH MAIN_AGENT AND TESTING_AGENT MUST PRESERVE THIS ENTIRE BLOCK

# Communication Protocol:
# If the `testing_agent` is available, main agent should delegate all testing tasks to it.
#
# You have access to a file called `test_result.md`. This file contains the complete testing state
# and history, and is the primary means of communication between main and the testing agent.
#
# Main and testing agents must follow this exact format to maintain testing data. 
# The testing data must be entered in yaml format Below is the data structure:
# 
## user_problem_statement: {problem_statement}
## backend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.py"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## frontend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.js"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## metadata:
##   created_by: "main_agent"
##   version: "1.0"
##   test_sequence: 0
##   run_ui: false
##
## test_plan:
##   current_focus:
##     - "Task name 1"
##     - "Task name 2"
##   stuck_tasks:
##     - "Task name with persistent issues"
##   test_all: false
##   test_priority: "high_first"  # or "sequential" or "stuck_first"
##
## agent_communication:
##     -agent: "main"  # or "testing" or "user"
##     -message: "Communication message between agents"

# Protocol Guidelines for Main agent
#
# 1. Update Test Result File Before Testing:
#    - Main agent must always update the `test_result.md` file before calling the testing agent
#    - Add implementation details to the status_history
#    - Set `needs_retesting` to true for tasks that need testing
#    - Update the `test_plan` section to guide testing priorities
#    - Add a message to `agent_communication` explaining what you've done
#
# 2. Incorporate User Feedback:
#    - When a user provides feedback that something is or isn't working, add this information to the relevant task's status_history
#    - Update the working status based on user feedback
#    - If a user reports an issue with a task that was marked as working, increment the stuck_count
#    - Whenever user reports issue in the app, if we have testing agent and task_result.md file so find the appropriate task for that and append in status_history of that task to contain the user concern and problem as well 
#
# 3. Track Stuck Tasks:
#    - Monitor which tasks have high stuck_count values or where you are fixing same issue again and again, analyze that when you read task_result.md
#    - For persistent issues, use websearch tool to find solutions
#    - Pay special attention to tasks in the stuck_tasks list
#    - When you fix an issue with a stuck task, don't reset the stuck_count until the testing agent confirms it's working
#
# 4. Provide Context to Testing Agent:
#    - When calling the testing agent, provide clear instructions about:
#      - Which tasks need testing (reference the test_plan)
#      - Any authentication details or configuration needed
#      - Specific test scenarios to focus on
#      - Any known issues or edge cases to verify
#
# 5. Call the testing agent with specific instructions referring to test_result.md
#
# IMPORTANT: Main agent must ALWAYS update test_result.md BEFORE calling the testing agent, as it relies on this file to understand what to test next.

#====================================================================================================
# END - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================



#====================================================================================================
# Testing Data - Main Agent and testing sub agent both should log testing data below this section
#====================================================================================================

user_problem_statement: |
  Implement advanced features for combat sports judging tool in order:
  1. Shadow-Judging/Training Mode - Complete with metrics tracking, hidden official cards, calibration scoring
  2. Offline-First + Sync - Full IndexedDB queue, reconciliation logic, conflict resolution
  3. Explainability Cards - Detailed "Why 10-8?" breakdowns with event clips/timestamps
  4. Fighter Memory Log - Historical stats, tendencies tracking across fights
  5. Discrepancy Flags for Review
  6. Per-Promotion Tuning Profiles
  7. Distraction-Free Mode
  8. Uncertainty Bands
  9. Accessibility Features (large-type, high contrast, audible cues)
  10. Security & Audit (cryptographic signatures, WORM logs)
  
  Currently implementing Feature #1: Shadow-Judging/Training Mode

backend:
  - task: "Shadow Judging API - Seed Training Library"
    implemented: true
    working: true
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Created POST /api/training-library/seed endpoint with 16 sample historical rounds from real UFC events. Includes mix of 10-9, 10-8, 10-7, and 10-10 scenarios."
      - working: true
        agent: "testing"
        comment: "✅ TESTED: POST /api/training-library/seed successfully seeds 16 training rounds. Response includes correct count and success message. All rounds properly stored in MongoDB training_library collection."
  
  - task: "Shadow Judging API - Get Training Rounds"
    implemented: true
    working: true
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Created GET /api/training-library/rounds endpoint to fetch all available training rounds."
      - working: true
        agent: "testing"
        comment: "✅ TESTED: GET /api/training-library/rounds returns all 16 training rounds with correct structure (id, event, fighters, roundNumber, summary, officialCard, type, createdAt). Response format validated."
  
  - task: "Shadow Judging API - Submit Judge Score"
    implemented: true
    working: true
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Created POST /api/training-library/submit-score endpoint to record judge performance metrics (MAE, 10-8 sensitivity, accuracy)."
      - working: true
        agent: "testing"
        comment: "✅ TESTED: POST /api/training-library/submit-score successfully saves judge performance data. Tested with 9 submissions across 3 judges. All required fields (judgeId, judgeName, roundId, myScore, officialScore, mae, sensitivity108, accuracy, match) properly stored with generated ID and timestamp."
  
  - task: "Shadow Judging API - Get Judge Stats"
    implemented: true
    working: true
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Created GET /api/training-library/judge-stats/:judgeId endpoint to calculate aggregate statistics for a judge."
      - working: true
        agent: "testing"
        comment: "✅ TESTED: GET /api/training-library/judge-stats/{judgeId} correctly calculates aggregate stats. Verified calculations: totalAttempts=3, averageAccuracy=95%, averageMAE=0.33, perfectMatches=2 for test judge. Returns 404 for non-existent judges as expected."
  
  - task: "Shadow Judging API - Leaderboard"
    implemented: true
    working: true
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "medium"
    needs_retesting: false
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Created GET /api/training-library/leaderboard endpoint using MongoDB aggregation to rank judges by accuracy."
      - working: true
        agent: "testing"
        comment: "✅ TESTED: GET /api/training-library/leaderboard returns top judges ranked by accuracy in descending order. Tested with 3 judges, proper sorting verified. Response structure includes judgeId, judgeName, totalAttempts, averageAccuracy, averageMAE, perfectMatches."

frontend:
  - task: "Shadow Judging Mode - UI Component"
    implemented: true
    working: true
    file: "/app/frontend/src/components/ShadowJudgingMode.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Updated ShadowJudgingMode component to use backend APIs instead of direct Firestore. Auto-seeds library on first load. Fixed BACKEND_URL env variable access."
      - working: true
        agent: "testing"
        comment: "✅ TESTED: Shadow Judging UI Component working perfectly. Successfully loads 16 training rounds from auto-seeding. Round selection, judging interface, score buttons (10-10, 10-9, 10-8, 10-7), and 'Reveal Official Card' functionality all working correctly. Calibration results display properly with Your Score, Official Score, accuracy percentage, MAE, 10-8 Sensitivity, and Match indicators. 'Back to Library' navigation works correctly."
  
  - task: "Shadow Judging Mode - Judge Stats Dashboard"
    implemented: true
    working: false
    file: "/app/frontend/src/components/ShadowJudgingMode.jsx"
    stuck_count: 1
    priority: "high"
    needs_retesting: false
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Added judge stats dashboard showing total attempts, avg accuracy, avg MAE, 10-8 accuracy, and perfect matches."
      - working: false
        agent: "testing"
        comment: "❌ ISSUE: 'My Stats' button not appearing even after judging multiple rounds. Stats dashboard functionality appears to be implemented but the button to access it is not visible. This may be due to a condition not being met for showing the stats button, or an issue with the judge stats API response."
  
  - task: "Shadow Judging Mode - Routing"
    implemented: true
    working: true
    file: "/app/frontend/src/App.js"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Added /shadow-judging route in App.js for Shadow Judging Mode access."
      - working: true
        agent: "testing"
        comment: "✅ TESTED: /shadow-judging route working correctly. Direct navigation to https://fightscribe.preview.emergentagent.com/shadow-judging loads the Shadow Judging Library page properly with all training rounds displayed."
  
  - task: "Shadow Judging Mode - Navigation Link"
    implemented: true
    working: false
    file: "/app/frontend/src/components/EventSetup.jsx"
    stuck_count: 1
    priority: "medium"
    needs_retesting: false
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Added button in EventSetup header to navigate to Shadow Judging Training mode."
      - working: false
        agent: "testing"
        comment: "❌ ISSUE: Navigation from EventSetup to Shadow Judging works, but 'Back to Events' button from Shadow Judging redirects to login page instead of EventSetup. This appears to be a session/authentication issue where the judge session is not being maintained properly during navigation."

metadata:
  created_by: "main_agent"
  version: "1.0"
  test_sequence: 0
  run_ui: false

test_plan:
  current_focus:
    - "Shadow Judging Mode - Judge Stats Dashboard"
    - "Shadow Judging Mode - Navigation Link"
  stuck_tasks:
    - "Shadow Judging Mode - Judge Stats Dashboard"
    - "Shadow Judging Mode - Navigation Link"
  test_all: false
  test_priority: "high_first"

agent_communication:
  - agent: "main"
    message: "Implemented complete Shadow Judging / Training Mode feature. Backend has 5 new API endpoints for training library management and judge performance tracking. Frontend updated to use backend APIs with auto-seeding, stats dashboard, and calibration metrics. Ready for testing."
  - agent: "testing"
    message: "✅ BACKEND TESTING COMPLETE: All 5 Shadow Judging Training Mode APIs are working perfectly. Comprehensive testing performed including: (1) Seeding 16 training rounds, (2) Retrieving rounds with proper structure, (3) Submitting judge scores with performance tracking, (4) Calculating accurate judge statistics, (5) Generating properly sorted leaderboard. All database operations (MongoDB) functioning correctly. No critical issues found. Backend APIs ready for frontend integration."
  - agent: "testing"
    message: "✅ FRONTEND TESTING COMPLETE: Shadow Judging Training Mode frontend mostly working. Core functionality (UI Component and Routing) working perfectly - 16 training rounds load correctly, judging interface works, calibration results display properly. Two issues found: (1) 'My Stats' button not appearing after judging rounds - stats dashboard implemented but not accessible, (2) 'Back to Events' navigation redirects to login instead of EventSetup - session management issue. All other features including accessibility checks passed."
  - agent: "main"
    message: "✅ LOGIN ISSUE FIXED: Resolved navigation problem where sign-in stayed on login page. Made localStorage primary auth method and replaced navigate() with window.location.href for reliable page transitions. Login now works perfectly."
  - agent: "main"
    message: "⏳ FEATURE #2 IN PROGRESS: Offline-First + Sync implementation started. Created offlineDB.js (IndexedDB wrapper with event queue and sync log stores) and syncManager.js (comprehensive sync manager with auto-sync on reconnection). Integrated into OperatorPanel with UI indicators (online/offline badges, queue count, sync button). Event logging now routes through syncManager for automatic offline queuing."