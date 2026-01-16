import { useState, useCallback, memo } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { AlertTriangle, Shield, Plus, Trash2 } from "lucide-react";

export const ManualScoreOverride = memo(function ManualScoreOverride({ currentData, onOverride, onClearOverride, isOverrideActive }) {
  const [isOpen, setIsOpen] = useState(false);
  const [event, setEvent] = useState(currentData.event);
  const [division, setDivision] = useState(currentData.division);
  const [redName, setRedName] = useState(currentData.red.name);
  const [blueName, setBlueName] = useState(currentData.blue.name);
  const [rounds, setRounds] = useState(currentData.rounds.length > 0 ? currentData.rounds : [{ round: 1, unified_red: 10, unified_blue: 9 }]);
  const [winner, setWinner] = useState(currentData.winner);

  const handleOpenChange = (open) => {
    if (open) {
      setEvent(currentData.event);
      setDivision(currentData.division);
      setRedName(currentData.red.name);
      setBlueName(currentData.blue.name);
      setRounds(currentData.rounds.length > 0 ? currentData.rounds : [{ round: 1, unified_red: 10, unified_blue: 9 }]);
      setWinner(currentData.winner);
    }
    setIsOpen(open);
  };

  const addRound = useCallback(() => { 
    if (rounds.length < 5) setRounds((prev) => [...prev, { round: prev.length + 1, unified_red: 10, unified_blue: 9 }]); 
  }, [rounds.length]);
  
  const removeRound = useCallback((index) => { 
    setRounds((prev) => prev.filter((_, i) => i !== index).map((r, i) => ({ ...r, round: i + 1 }))); 
  }, []);
  
  const updateRoundScore = useCallback((index, field, value) => {
    const numValue = Math.max(0, Math.min(10, parseInt(value) || 0));
    setRounds((prev) => prev.map((r, i) => (i === index ? { ...r, [field]: numValue } : r)));
  }, []);
  
  const calculateTotals = useCallback(() => rounds.reduce((acc, r) => ({ red: acc.red + r.unified_red, blue: acc.blue + r.unified_blue }), { red: 0, blue: 0 }), [rounds]);

  const handleApplyOverride = useCallback(() => {
    const totals = calculateTotals();
    const overrideData = {
      event: event.trim() || "PFC 50",
      fight_id: currentData.fight_id || "manual-override",
      division: division.trim(),
      red: { name: redName.trim() || "Red Corner" },
      blue: { name: blueName.trim() || "Blue Corner" },
      rounds,
      unified_total: totals,
      winner,
      status: winner ? "completed" : "in_progress",
    };
    onOverride(overrideData);
    setIsOpen(false);
  }, [event, division, redName, blueName, rounds, winner, currentData.fight_id, calculateTotals, onOverride]);

  const totals = calculateTotals();

  return (
    <Sheet open={isOpen} onOpenChange={handleOpenChange}>
      <SheetTrigger asChild>
        <Button variant={isOverrideActive ? "destructive" : "outline"} size="sm" className="gap-2">
          <Shield className="w-4 h-4" />
          {isOverrideActive ? "Override Active" : "Emergency Override"}
        </Button>
      </SheetTrigger>
      <SheetContent className="w-[400px] sm:w-[540px] overflow-y-auto bg-gray-900 border-gray-700">
        <SheetHeader>
          <SheetTitle className="flex items-center gap-2 text-amber-500">
            <AlertTriangle className="w-5 h-5" />
            Emergency Score Override
          </SheetTitle>
          <SheetDescription className="text-gray-400">
            Use only if API fails. Scores entered here will replace live data.
          </SheetDescription>
        </SheetHeader>
        <div className="mt-6 space-y-6">
          {/* Event Info */}
          <div className="space-y-3">
            <h4 className="text-sm font-semibold text-gray-400">Event Info</h4>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label htmlFor="event" className="text-gray-300">Event Name</Label>
                <Input id="event" value={event} onChange={(e) => setEvent(e.target.value)} placeholder="PFC 50" maxLength={50} className="bg-gray-800 border-gray-700" />
              </div>
              <div>
                <Label htmlFor="division" className="text-gray-300">Division</Label>
                <Input id="division" value={division} onChange={(e) => setDivision(e.target.value)} placeholder="Lightweight" maxLength={30} className="bg-gray-800 border-gray-700" />
              </div>
            </div>
          </div>
          
          {/* Fighters */}
          <div className="space-y-3">
            <h4 className="text-sm font-semibold text-gray-400">Fighters</h4>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label htmlFor="redName" className="text-red-500">Red Corner</Label>
                <Input id="redName" value={redName} onChange={(e) => setRedName(e.target.value)} placeholder="Fighter Name" className="border-red-500/30 bg-gray-800" maxLength={40} />
              </div>
              <div>
                <Label htmlFor="blueName" className="text-blue-500">Blue Corner</Label>
                <Input id="blueName" value={blueName} onChange={(e) => setBlueName(e.target.value)} placeholder="Fighter Name" className="border-blue-500/30 bg-gray-800" maxLength={40} />
              </div>
            </div>
          </div>
          
          {/* Round Scores */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h4 className="text-sm font-semibold text-gray-400">Round Scores</h4>
              <Button variant="ghost" size="sm" onClick={addRound} disabled={rounds.length >= 5} className="h-7 text-xs">
                <Plus className="w-3 h-3 mr-1" />Add Round
              </Button>
            </div>
            <div className="space-y-2">
              {rounds.map((round, index) => (
                <div key={round.round} className="flex items-center gap-2 p-2 rounded bg-gray-800">
                  <span className="w-12 text-xs font-medium text-gray-400">Rd {round.round}</span>
                  <div className="flex items-center gap-1">
                    <Input 
                      type="number" 
                      min={0} 
                      max={10} 
                      value={round.unified_red} 
                      onChange={(e) => updateRoundScore(index, "unified_red", e.target.value)} 
                      className="w-14 h-8 text-center text-red-500 font-bold bg-gray-900 border-gray-700" 
                    />
                    <span className="text-gray-500">-</span>
                    <Input 
                      type="number" 
                      min={0} 
                      max={10} 
                      value={round.unified_blue} 
                      onChange={(e) => updateRoundScore(index, "unified_blue", e.target.value)} 
                      className="w-14 h-8 text-center text-blue-500 font-bold bg-gray-900 border-gray-700" 
                    />
                  </div>
                  {rounds.length > 1 && (
                    <Button variant="ghost" size="sm" onClick={() => removeRound(index)} className="h-7 w-7 p-0 text-gray-400 hover:text-red-500">
                      <Trash2 className="w-3 h-3" />
                    </Button>
                  )}
                </div>
              ))}
            </div>
            <div className="flex items-center justify-center gap-4 p-3 rounded bg-gray-800 font-bold">
              <span className="text-red-500 text-lg">{totals.red}</span>
              <span className="text-gray-400">TOTAL</span>
              <span className="text-blue-500 text-lg">{totals.blue}</span>
            </div>
          </div>
          
          {/* Winner */}
          <div className="space-y-3">
            <h4 className="text-sm font-semibold text-gray-400">Winner (Optional)</h4>
            <Select value={winner || "none"} onValueChange={(v) => setWinner(v === "none" ? null : v)}>
              <SelectTrigger className="bg-gray-800 border-gray-700">
                <SelectValue placeholder="No winner declared" />
              </SelectTrigger>
              <SelectContent className="bg-gray-800 border-gray-700">
                <SelectItem value="none">No winner (in progress)</SelectItem>
                <SelectItem value="red">Red Corner Wins</SelectItem>
                <SelectItem value="blue">Blue Corner Wins</SelectItem>
                <SelectItem value="draw">Draw</SelectItem>
              </SelectContent>
            </Select>
          </div>
          
          {/* Actions */}
          <div className="flex gap-3 pt-4 border-t border-gray-700">
            <Button onClick={handleApplyOverride} className="flex-1 bg-amber-600 hover:bg-amber-700">
              <Shield className="w-4 h-4 mr-2" />Apply Override
            </Button>
            {isOverrideActive && (
              <Button variant="outline" onClick={() => { onClearOverride(); setIsOpen(false); }}>
                Clear Override
              </Button>
            )}
          </div>
          <p className="text-xs text-gray-500 text-center">
            Override will remain active until cleared or page refreshed.<br />
            <strong>Hotkey: Ctrl+Shift+O</strong> to toggle panel
          </p>
        </div>
      </SheetContent>
    </Sheet>
  );
});
