import { memo, useState, useEffect, useRef, useCallback } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Wifi, WifiOff, RefreshCw, ChevronDown, Loader2, Copy, Check, Plus, Trophy } from "lucide-react";
import { toast } from "sonner";

const API_BASE = process.env.REACT_APP_BACKEND_URL || '';

export const BoutSelector = memo(function BoutSelector({ onConnect, onRefresh, onReset, connectionStatus, currentBoutId }) {
  const [boutId, setBoutId] = useState(currentBoutId || "");
  const [bouts, setBouts] = useState([]);
  const [isLoadingBouts, setIsLoadingBouts] = useState(false);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [newBout, setNewBout] = useState({
    fighter1: "",
    fighter2: "",
    total_rounds: "3",
    event_name: "PFC 50",
    division: ""
  });
  const dropdownRef = useRef(null);

  const fetchBouts = async () => {
    setIsLoadingBouts(true);
    try {
      const response = await fetch(`${API_BASE}/api/bouts/active`);
      if (response.ok) {
        const data = await response.json();
        setBouts(Array.isArray(data) ? data : data.bouts || []);
      } else {
        // Try alternative endpoint
        const altResponse = await fetch(`${API_BASE}/api/bouts`);
        if (altResponse.ok) {
          const data = await altResponse.json();
          setBouts(Array.isArray(data) ? data : data.bouts || []);
        }
      }
    } catch (error) {
      console.error("[BoutSelector] Failed to fetch bouts:", error);
    } finally {
      setIsLoadingBouts(false);
    }
  };

  const createBout = async () => {
    if (!newBout.fighter1.trim() || !newBout.fighter2.trim()) {
      toast.error("Please enter both fighter names");
      return;
    }

    setIsCreating(true);
    try {
      const response = await fetch(`${API_BASE}/api/bouts`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          fighter1: newBout.fighter1.trim(),
          fighter2: newBout.fighter2.trim(),
          total_rounds: parseInt(newBout.total_rounds),
          event_name: newBout.event_name || "PFC 50",
          division: newBout.division
        })
      });

      if (response.ok) {
        const data = await response.json();
        toast.success(`Bout created: ${data.fighter1} vs ${data.fighter2}`);
        setShowCreateDialog(false);
        setNewBout({ fighter1: "", fighter2: "", total_rounds: "3", event_name: "PFC 50", division: "" });
        await fetchBouts();
        // Auto-connect to the new bout
        setBoutId(data.bout_id);
        onConnect(data.bout_id);
      } else {
        const error = await response.json();
        toast.error(`Failed to create bout: ${error.detail || "Unknown error"}`);
      }
    } catch (error) {
      console.error("[BoutSelector] Failed to create bout:", error);
      toast.error("Failed to create bout. Check connection.");
    } finally {
      setIsCreating(false);
    }
  };

  useEffect(() => { fetchBouts(); }, []);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsDropdownOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleConnect = () => { 
    if (boutId.trim()) { 
      onConnect(boutId.trim()); 
      setIsDropdownOpen(false); 
    } 
  };
  
  const handleSelectBout = (bout) => { 
    setBoutId(bout.bout_id); 
    onConnect(bout.bout_id); 
    setIsDropdownOpen(false); 
  };
  
  const isConnected = connectionStatus === "connected";

  return (
    <div className="flex items-center gap-2 bg-gray-900 border border-gray-700 rounded-lg p-2 shadow-lg">
      <div className="flex items-center gap-1.5">
        {isConnected ? <Wifi className="w-3.5 h-3.5 text-green-500" /> : <WifiOff className="w-3.5 h-3.5 text-red-500" />}
        <span className="text-[10px] text-gray-400 uppercase tracking-wider">{connectionStatus}</span>
      </div>
      <div className="h-4 w-px bg-gray-700" />
      <div className="relative" ref={dropdownRef}>
        <div className="flex items-center gap-1">
          <Input 
            type="text" 
            placeholder="bout-id" 
            value={boutId} 
            onChange={(e) => setBoutId(e.target.value)} 
            onKeyDown={(e) => e.key === "Enter" && handleConnect()} 
            className="h-7 w-32 text-xs bg-gray-800 border-gray-700" 
          />
          <Button 
            size="sm" 
            variant="outline" 
            onClick={() => { if (!isDropdownOpen) fetchBouts(); setIsDropdownOpen(!isDropdownOpen); }} 
            className="h-7 w-7 p-0"
          >
            {isLoadingBouts ? <Loader2 className="w-3 h-3 animate-spin" /> : <ChevronDown className={`w-3 h-3 transition-transform ${isDropdownOpen ? "rotate-180" : ""}`} />}
          </Button>
        </div>
        {isDropdownOpen && (
          <div className="absolute top-full left-0 mt-1 w-64 max-h-64 overflow-y-auto z-50 bg-gray-900 border border-gray-700 rounded-lg shadow-xl">
            {bouts.length === 0 ? (
              <div className="p-3 text-xs text-gray-400 text-center">{isLoadingBouts ? "Loading bouts..." : "No active bouts found"}</div>
            ) : (
              <ul className="py-1">
                {bouts.map((bout) => (
                  <li key={bout.bout_id || bout._id}>
                    <button 
                      onClick={() => handleSelectBout(bout)} 
                      className={`w-full px-3 py-2 text-left hover:bg-gray-800 transition-colors ${boutId === bout.bout_id ? "bg-lb-gold/10 text-lb-gold" : "text-white"}`}
                    >
                      <div className="text-xs font-medium truncate">{bout.fighter1 || bout.red_fighter || "Red"} vs {bout.fighter2 || bout.blue_fighter || "Blue"}</div>
                      <div className="text-[10px] text-gray-500 flex items-center gap-2">
                        <span className="font-mono">{(bout.bout_id || bout._id || '').slice(0, 12)}</span>
                        {bout.status && <span className={`px-1 rounded ${bout.status === "in_progress" ? "bg-green-500/20 text-green-400" : bout.status === "completed" ? "bg-gray-700" : "bg-yellow-500/20 text-yellow-400"}`}>{bout.status}</span>}
                      </div>
                    </button>
                  </li>
                ))}
              </ul>
            )}
            <div className="border-t border-gray-700 p-2">
              <Button size="sm" variant="ghost" onClick={fetchBouts} className="w-full h-6 text-xs" disabled={isLoadingBouts}>
                <RefreshCw className={`w-3 h-3 mr-1 ${isLoadingBouts ? "animate-spin" : ""}`} /> Refresh List
              </Button>
            </div>
          </div>
        )}
      </div>
      <Button size="sm" variant="outline" onClick={handleConnect} className="h-7 px-2 text-xs">Connect</Button>
      {currentBoutId && (
        <>
          <Button size="sm" variant="ghost" onClick={onRefresh} className="h-7 w-7 p-0" title="Refresh data"><RefreshCw className="w-3.5 h-3.5" /></Button>
          <CopyBroadcastUrlButton boutId={currentBoutId} />
          <Button size="sm" variant="ghost" onClick={onReset} className="h-7 px-2 text-xs text-gray-400">Reset</Button>
        </>
      )}
    </div>
  );
});

function CopyBroadcastUrlButton({ boutId }) {
  const [copied, setCopied] = useState(false);
  
  const handleCopyUrl = useCallback(async () => {
    const broadcastUrl = `${window.location.origin}/pfc50/${boutId}`;
    try {
      await navigator.clipboard.writeText(broadcastUrl);
      setCopied(true);
      toast.success("Broadcast URL copied!", { description: broadcastUrl, duration: 3000 });
      setTimeout(() => setCopied(false), 2000);
    } catch {
      const textArea = document.createElement("textarea");
      textArea.value = broadcastUrl;
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand("copy");
      document.body.removeChild(textArea);
      setCopied(true);
      toast.success("Broadcast URL copied!");
      setTimeout(() => setCopied(false), 2000);
    }
  }, [boutId]);

  return (
    <Button size="sm" variant="ghost" onClick={handleCopyUrl} className="h-7 px-2 text-xs gap-1" title="Copy broadcast URL for arena display">
      {copied ? <Check className="w-3.5 h-3.5 text-green-500" /> : <Copy className="w-3.5 h-3.5" />}
      <span className="hidden sm:inline">Broadcast</span>
    </Button>
  );
}
