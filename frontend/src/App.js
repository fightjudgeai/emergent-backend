import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import BoutSetup from "@/components/BoutSetup";
import OperatorPanel from "@/components/OperatorPanel";
import JudgePanel from "@/components/JudgePanel";

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<BoutSetup />} />
          <Route path="/operator/:boutId" element={<OperatorPanel />} />
          <Route path="/judge/:boutId" element={<JudgePanel />} />
        </Routes>
      </BrowserRouter>
    </div>
  );
}

export default App;