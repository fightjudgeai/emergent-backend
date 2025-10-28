import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Toaster } from "sonner";
import BoutSetup from "@/components/BoutSetup";
import OperatorPanel from "@/components/OperatorPanel";
import JudgePanel from "@/components/JudgePanel";

function App() {
  return (
    <div className="App">
      <Toaster position="top-right" richColors />
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