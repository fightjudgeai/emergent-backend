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
    working: "NA"
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Created POST /api/training-library/seed endpoint with 16 sample historical rounds from real UFC events. Includes mix of 10-9, 10-8, 10-7, and 10-10 scenarios."
  
  - task: "Shadow Judging API - Get Training Rounds"
    implemented: true
    working: "NA"
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Created GET /api/training-library/rounds endpoint to fetch all available training rounds."
  
  - task: "Shadow Judging API - Submit Judge Score"
    implemented: true
    working: "NA"
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Created POST /api/training-library/submit-score endpoint to record judge performance metrics (MAE, 10-8 sensitivity, accuracy)."
  
  - task: "Shadow Judging API - Get Judge Stats"
    implemented: true
    working: "NA"
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Created GET /api/training-library/judge-stats/:judgeId endpoint to calculate aggregate statistics for a judge."
  
  - task: "Shadow Judging API - Leaderboard"
    implemented: true
    working: "NA"
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "medium"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Created GET /api/training-library/leaderboard endpoint using MongoDB aggregation to rank judges by accuracy."

frontend:
  - task: "Shadow Judging Mode - UI Component"
    implemented: true
    working: "NA"
    file: "/app/frontend/src/components/ShadowJudgingMode.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Updated ShadowJudgingMode component to use backend APIs instead of direct Firestore. Auto-seeds library on first load. Fixed BACKEND_URL env variable access."
  
  - task: "Shadow Judging Mode - Judge Stats Dashboard"
    implemented: true
    working: "NA"
    file: "/app/frontend/src/components/ShadowJudgingMode.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Added judge stats dashboard showing total attempts, avg accuracy, avg MAE, 10-8 accuracy, and perfect matches."
  
  - task: "Shadow Judging Mode - Routing"
    implemented: true
    working: "NA"
    file: "/app/frontend/src/App.js"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Added /shadow-judging route in App.js for Shadow Judging Mode access."
  
  - task: "Shadow Judging Mode - Navigation Link"
    implemented: true
    working: "NA"
    file: "/app/frontend/src/components/EventSetup.jsx"
    stuck_count: 0
    priority: "medium"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Added button in EventSetup header to navigate to Shadow Judging Training mode."

metadata:
  created_by: "main_agent"
  version: "1.0"
  test_sequence: 0
  run_ui: false

test_plan:
  current_focus:
    - "Shadow Judging API - Seed Training Library"
    - "Shadow Judging API - Get Training Rounds"
    - "Shadow Judging API - Submit Judge Score"
    - "Shadow Judging Mode - UI Component"
  stuck_tasks: []
  test_all: false
  test_priority: "high_first"

agent_communication:
  - agent: "main"
    message: "Implemented complete Shadow Judging / Training Mode feature. Backend has 5 new API endpoints for training library management and judge performance tracking. Frontend updated to use backend APIs with auto-seeding, stats dashboard, and calibration metrics. Ready for testing."