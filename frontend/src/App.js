import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "sonner";
import JudgeLogin from "@/components/JudgeLogin";
import EventSetup from "@/components/EventSetup";
import FightList from "@/components/FightList";
import OperatorPanel from "@/components/OperatorPanel";
import JudgePanel from "@/components/JudgePanel";
import BroadcastMode from "@/components/BroadcastMode";
import SupervisorPanel from "@/components/SupervisorPanel";
import ShadowJudgingMode from "@/components/ShadowJudgingMode";
import LiveStatsDashboard from "@/components/LiveStatsDashboard";
import ReviewDashboard from "@/components/ReviewDashboard";
import TuningProfileManager from "@/components/TuningProfileManager";
import AuditLogViewer from "@/components/AuditLogViewer";
import JudgeProfile from "@/components/JudgeProfile";
import EventsPage from "@/components/EventsPage";
import FightDetailPage from "@/components/FightDetailPage";
import FighterProfilePage from "@/components/FighterProfilePage";
import PostFightReviewPanel from "@/components/PostFightReviewPanel";
import CVSystemsPage from "@/components/CVSystemsPage";

function App() {
  // Check if judge is logged in
  const isJudgeLoggedIn = () => {
    return localStorage.getItem('judgeProfile') !== null;
  };

  return (
    <div className="App">
      <Toaster position="top-right" richColors />
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<JudgeLogin />} />
          <Route path="/" element={
            isJudgeLoggedIn() ? <EventSetup /> : <Navigate to="/login" />
          } />
          <Route path="/event/:eventId/fights" element={<FightList />} />
          <Route path="/operator/:boutId" element={<OperatorPanel />} />
          <Route path="/judge/:boutId" element={<JudgePanel />} />
          <Route path="/broadcast/:boutId" element={<BroadcastMode />} />
          <Route path="/supervisor/:boutId" element={<SupervisorPanel />} />
          <Route path="/shadow-judging" element={<ShadowJudgingMode />} />
          <Route path="/review-dashboard" element={<ReviewDashboard />} />
          <Route path="/tuning-profiles" element={<TuningProfileManager />} />
          <Route path="/stats/fight/:fight_id" element={<LiveStatsDashboard />} />
          <Route path="/audit-logs" element={<AuditLogViewer />} />
          <Route path="/profile" element={<JudgeProfile />} />
          
          {/* Public Stats Pages */}
          <Route path="/events" element={<EventsPage />} />
          <Route path="/fights/:fight_id" element={<FightDetailPage />} />
          <Route path="/fighters/:fighter_id" element={<FighterProfilePage />} />
          
          {/* Post-Fight Review Interface */}
          <Route path="/review/:fight_id" element={<PostFightReviewPanel fightId="fight_123" supervisorId="supervisor_1" />} />
        </Routes>
      </BrowserRouter>
    </div>
  );
}

export default App;