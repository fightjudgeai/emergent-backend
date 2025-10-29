import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "sonner";
import JudgeLogin from "@/components/JudgeLogin";
import EventSetup from "@/components/EventSetup";
import FightList from "@/components/FightList";
import OperatorPanel from "@/components/OperatorPanel";
import JudgePanel from "@/components/JudgePanel";
import ShadowJudgingMode from "@/components/ShadowJudgingMode";

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
        </Routes>
      </BrowserRouter>
    </div>
  );
}

export default App;