import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "sonner";
import JudgeLogin from "@/components/JudgeLogin";
import EventSetup from "@/components/EventSetup";
import FightList from "@/components/FightList";
import OperatorPanel from "@/components/OperatorPanel";
import OperatorSetup from "@/components/OperatorSetup";
import OperatorSimple from "@/components/OperatorSimple";
import OperatorWaiting from "@/components/OperatorWaiting";
import SupervisorDashboard from "@/components/SupervisorDashboard";
import JudgePanel from "@/components/JudgePanel";
import BroadcastMode from "@/components/BroadcastMode";
import BroadcastDisplay from "@/components/BroadcastDisplay";
import BroadcastDisplayDemo from "@/components/BroadcastDisplayDemo";
import LovableBroadcast from "@/components/LovableBroadcast";
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
import FightHistory from "@/components/FightHistory";
import FightDetailsArchived from "@/components/FightDetailsArchived";

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
          <Route path="/operator-setup" element={<OperatorSetup />} />
          <Route path="/op/:boutId" element={<OperatorSimple />} />
          <Route path="/waiting" element={<OperatorWaiting />} />
          <Route path="/waiting/:boutId" element={<OperatorWaiting />} />
          <Route path="/supervisor" element={<SupervisorDashboard />} />
          <Route path="/supervisor/:boutId" element={<SupervisorDashboard />} />
          <Route path="/cv-systems/:boutId" element={<CVSystemsPage />} />
          <Route path="/judge/:boutId" element={<JudgePanel />} />
          <Route path="/broadcast/:boutId" element={<BroadcastMode />} />
          <Route path="/arena/:boutId" element={<BroadcastDisplay />} />
          <Route path="/arena-demo/:boutId" element={<BroadcastDisplayDemo />} />
          <Route path="/pfc50/:boutId" element={<LovableBroadcast />} />
          <Route path="/pfc50" element={<LovableBroadcast />} />
          <Route path="/supervisor/:boutId" element={<SupervisorPanel />} />
          <Route path="/shadow-judging" element={<ShadowJudgingMode />} />
          <Route path="/review-dashboard" element={<ReviewDashboard />} />
          <Route path="/tuning-profiles" element={<TuningProfileManager />} />
          <Route path="/stats/fight/:fight_id" element={<LiveStatsDashboard />} />
          <Route path="/audit-logs" element={<AuditLogViewer />} />
          <Route path="/profile" element={<JudgeProfile />} />
          
          {/* Fight History & Archives */}
          <Route path="/fight-history" element={<FightHistory />} />
          <Route path="/fight-details/:boutId" element={<FightDetailsArchived />} />
          
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