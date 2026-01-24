import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { ScrollArea } from '@/components/ui/scroll-area';
import { toast } from 'sonner';
import { 
  Plus, 
  Trophy, 
  Users, 
  Swords, 
  Play, 
  Square,
  Settings,
  ChevronRight,
  Crown,
  Scale,
  Clock,
  Trash2,
  Edit,
  Monitor
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

// Weight classes
// MMA Weight Classes - Men's, Women's, and Catchweight
const WEIGHT_CLASSES = {
  mens: [
    { value: 'M-Strawweight', label: "Men's Strawweight (115 lbs)" },
    { value: 'M-Flyweight', label: "Men's Flyweight (125 lbs)" },
    { value: 'M-Bantamweight', label: "Men's Bantamweight (135 lbs)" },
    { value: 'M-Featherweight', label: "Men's Featherweight (145 lbs)" },
    { value: 'M-Lightweight', label: "Men's Lightweight (155 lbs)" },
    { value: 'M-Welterweight', label: "Men's Welterweight (170 lbs)" },
    { value: 'M-Middleweight', label: "Men's Middleweight (185 lbs)" },
    { value: 'M-Light Heavyweight', label: "Men's Light Heavyweight (205 lbs)" },
    { value: 'M-Heavyweight', label: "Men's Heavyweight (265 lbs)" },
  ],
  womens: [
    { value: 'W-Strawweight', label: "Women's Strawweight (115 lbs)" },
    { value: 'W-Flyweight', label: "Women's Flyweight (125 lbs)" },
    { value: 'W-Bantamweight', label: "Women's Bantamweight (135 lbs)" },
    { value: 'W-Featherweight', label: "Women's Featherweight (145 lbs)" },
  ],
  other: [
    { value: 'Catchweight', label: 'Catchweight (Custom)' },
  ]
};

/**
 * SupervisorControl - Main control panel for supervisor
 * Creates events, fights, assigns operators, controls scoring flow
 */
export default function SupervisorControl() {
  const navigate = useNavigate();
  
  // Event state
  const [eventName, setEventName] = useState(localStorage.getItem('current_event_name') || '');
  const [eventId, setEventId] = useState(localStorage.getItem('current_event_id') || '');
  
  // Fights in this event
  const [fights, setFights] = useState([]);
  const [activeFight, setActiveFight] = useState(null);
  
  // New fight form
  const [showNewFight, setShowNewFight] = useState(false);
  const [newFight, setNewFight] = useState({
    fighter1: '',
    fighter1Record: '',
    fighter1Photo: '',
    fighter2: '',
    fighter2Record: '',
    fighter2Photo: '',
    weightClass: 'M-Lightweight',
    rounds: 3,
    isTitleFight: false,
    isMainEvent: false
  });
  
  // Operators
  const [operators, setOperators] = useState([]);
  
  // Loading
  const [isLoading, setIsLoading] = useState(false);

  // Create/Set Event
  const handleCreateEvent = async () => {
    if (!eventName.trim()) {
      toast.error('Please enter an event name');
      return;
    }
    
    const newEventId = `event-${Date.now()}`;
    
    try {
      await fetch(`${API}/api/events/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          event_id: newEventId,
          event_name: eventName.trim()
        })
      });
      
      setEventId(newEventId);
      localStorage.setItem('current_event_name', eventName.trim());
      localStorage.setItem('current_event_id', newEventId);
      toast.success(`Event "${eventName}" created!`);
    } catch (error) {
      // Even if API fails, set locally
      setEventId(newEventId);
      localStorage.setItem('current_event_name', eventName.trim());
      localStorage.setItem('current_event_id', newEventId);
      toast.success(`Event "${eventName}" created!`);
    }
  };

  // Fetch fights for this event
  const fetchFights = useCallback(async () => {
    if (!eventId) return;
    
    try {
      const response = await fetch(`${API}/api/supervisor/fights?event_id=${eventId}`);
      if (response.ok) {
        const data = await response.json();
        setFights(data.fights || []);
        
        // Find active fight
        const active = (data.fights || []).find(f => f.status === 'active' || f.status === 'in_progress');
        if (active) setActiveFight(active);
      }
    } catch (error) {
      console.error('Error fetching fights:', error);
    }
  }, [eventId]);

  // Fetch operators
  const fetchOperators = useCallback(async () => {
    if (!activeFight) return;
    
    try {
      const response = await fetch(`${API}/api/operators/list?bout_id=${activeFight.bout_id}`);
      if (response.ok) {
        const data = await response.json();
        setOperators(data.operators || []);
      }
    } catch (error) {
      console.error('Error fetching operators:', error);
    }
  }, [activeFight]);

  useEffect(() => {
    if (eventId) {
      fetchFights();
      const interval = setInterval(fetchFights, 5000);
      return () => clearInterval(interval);
    }
  }, [eventId, fetchFights]);

  useEffect(() => {
    if (activeFight) {
      fetchOperators();
      const interval = setInterval(fetchOperators, 3000);
      return () => clearInterval(interval);
    }
  }, [activeFight, fetchOperators]);

  // Create new fight
  const handleCreateFight = async () => {
    if (!newFight.fighter1.trim() || !newFight.fighter2.trim()) {
      toast.error('Please enter both fighter names');
      return;
    }
    
    setIsLoading(true);
    const boutId = `${eventId}-fight-${fights.length + 1}`;
    
    try {
      const response = await fetch(`${API}/api/bouts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          bout_id: boutId,
          event_id: eventId,
          event_name: eventName,
          fighter1: newFight.fighter1.trim(),
          fighter2: newFight.fighter2.trim(),
          weight_class: newFight.weightClass,
          totalRounds: newFight.rounds,
          is_title_fight: newFight.isTitleFight,
          is_main_event: newFight.isMainEvent,
          status: 'pending',
          currentRound: 1
        })
      });
      
      if (response.ok) {
        toast.success(`Fight added: ${newFight.fighter1} vs ${newFight.fighter2}`);
        setShowNewFight(false);
        setNewFight({
          fighter1: '',
          fighter2: '',
          weightClass: 'M-Lightweight',
          rounds: 3,
          isTitleFight: false,
          isMainEvent: false
        });
        fetchFights();
      } else {
        toast.error('Failed to create fight');
      }
    } catch (error) {
      toast.error('Error creating fight');
    } finally {
      setIsLoading(false);
    }
  };

  // Start a fight (make it active)
  const handleStartFight = async (fight) => {
    setIsLoading(true);
    try {
      // Set all other fights to pending, this one to active
      await fetch(`${API}/api/supervisor/activate-fight`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          event_id: eventId,
          bout_id: fight.bout_id
        })
      });
      
      setActiveFight(fight);
      toast.success(`Starting: ${fight.fighter1} vs ${fight.fighter2}`);
      fetchFights();
    } catch (error) {
      toast.error('Error starting fight');
    } finally {
      setIsLoading(false);
    }
  };

  // Go to scoring dashboard for active fight
  const handleOpenScoring = () => {
    if (activeFight) {
      navigate(`/supervisor/${activeFight.bout_id}`);
    }
  };

  // Delete a fight
  const handleDeleteFight = async (boutId) => {
    if (!window.confirm('Delete this fight?')) return;
    
    try {
      await fetch(`${API}/api/bouts/${boutId}`, { method: 'DELETE' });
      toast.success('Fight deleted');
      fetchFights();
    } catch (error) {
      toast.error('Error deleting fight');
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 p-6">
      <div className="max-w-6xl mx-auto space-y-6">
        
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Settings className="w-8 h-8 text-amber-500" />
            <div>
              <h1 className="text-2xl font-bold text-white">Supervisor Control</h1>
              <p className="text-gray-400 text-sm">Manage events, fights, and operators</p>
            </div>
          </div>
          {activeFight && (
            <Button onClick={handleOpenScoring} className="bg-green-600 hover:bg-green-700">
              <Monitor className="w-4 h-4 mr-2" /> Open Scoring Dashboard
            </Button>
          )}
        </div>

        {/* Event Setup */}
        {!eventId ? (
          <Card className="p-6 bg-gray-800/50 border-gray-700">
            <div className="space-y-4">
              <div className="flex items-center gap-2 text-amber-400">
                <Trophy className="w-5 h-5" />
                <h2 className="text-lg font-semibold">Create Event</h2>
              </div>
              <div className="flex gap-3">
                <Input
                  value={eventName}
                  onChange={(e) => setEventName(e.target.value)}
                  placeholder="Event name (e.g., PFC 50, UFC 300)"
                  className="bg-gray-700 border-gray-600 text-white flex-1"
                />
                <Button onClick={handleCreateEvent} className="bg-amber-500 hover:bg-amber-600 text-black">
                  Create Event
                </Button>
              </div>
            </div>
          </Card>
        ) : (
          <>
            {/* Event Info Bar */}
            <Card className="p-4 bg-amber-500/10 border-amber-500/30">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Trophy className="w-6 h-6 text-amber-400" />
                  <div>
                    <div className="text-xl font-bold text-white">{eventName}</div>
                    <div className="text-amber-400 text-sm">{fights.length} fights • {operators.length} operators connected</div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Badge className="bg-amber-500 text-black">
                    ID: {eventId.slice(-8)}
                  </Badge>
                  <Button 
                    size="sm" 
                    variant="outline" 
                    onClick={() => {
                      setEventId('');
                      setEventName('');
                      localStorage.removeItem('current_event_id');
                      localStorage.removeItem('current_event_name');
                    }}
                    className="border-gray-600"
                  >
                    Change Event
                  </Button>
                </div>
              </div>
            </Card>

            {/* Active Fight Banner */}
            {activeFight && (
              <Card className="p-4 bg-green-500/10 border-green-500/30">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className="w-3 h-3 bg-green-500 rounded-full animate-pulse" />
                    <div>
                      <div className="text-green-400 text-xs uppercase tracking-wider">Active Fight</div>
                      <div className="text-xl font-bold text-white">
                        {activeFight.fighter1} vs {activeFight.fighter2}
                      </div>
                      <div className="text-gray-400 text-sm">
                        {activeFight.weight_class} • {activeFight.totalRounds} rounds
                        {activeFight.is_title_fight && <Badge className="ml-2 bg-amber-500 text-black text-xs">TITLE</Badge>}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="text-right">
                      <div className="text-gray-400 text-xs">Operator URL</div>
                      <code className="text-amber-400 text-sm">/waiting/{activeFight.bout_id}</code>
                    </div>
                    <Button onClick={handleOpenScoring} className="bg-green-600 hover:bg-green-700">
                      <Play className="w-4 h-4 mr-2" /> Score Fight
                    </Button>
                  </div>
                </div>
              </Card>
            )}

            {/* Two Column Layout */}
            <div className="grid grid-cols-2 gap-6">
              
              {/* Fight Card */}
              <Card className="p-4 bg-gray-800/50 border-gray-700">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2 text-white">
                    <Swords className="w-5 h-5" />
                    <h2 className="font-semibold">Fight Card</h2>
                  </div>
                  <Dialog open={showNewFight} onOpenChange={setShowNewFight}>
                    <DialogTrigger asChild>
                      <Button size="sm" className="bg-amber-500 hover:bg-amber-600 text-black">
                        <Plus className="w-4 h-4 mr-1" /> Add Fight
                      </Button>
                    </DialogTrigger>
                    <DialogContent className="bg-gray-900 border-gray-700 text-white" aria-describedby="add-fight-description">
                      <DialogHeader>
                        <DialogTitle>Add New Fight</DialogTitle>
                        <p id="add-fight-description" className="sr-only">Form to add a new fight to the event card</p>
                      </DialogHeader>
                      <div className="space-y-4 py-4">
                        {/* Red Corner */}
                        <div className="space-y-2">
                          <Label className="text-red-400">Red Corner</Label>
                          <Input
                            value={newFight.fighter1}
                            onChange={(e) => setNewFight({...newFight, fighter1: e.target.value})}
                            placeholder="Fighter name"
                            className="bg-gray-800 border-red-900"
                          />
                        </div>
                        
                        {/* Blue Corner */}
                        <div className="space-y-2">
                          <Label className="text-blue-400">Blue Corner</Label>
                          <Input
                            value={newFight.fighter2}
                            onChange={(e) => setNewFight({...newFight, fighter2: e.target.value})}
                            placeholder="Fighter name"
                            className="bg-gray-800 border-blue-900"
                          />
                        </div>
                        
                        {/* Weight Class */}
                        <div className="space-y-2">
                          <Label>Weight Class</Label>
                          <Select value={newFight.weightClass} onValueChange={(v) => setNewFight({...newFight, weightClass: v})}>
                            <SelectTrigger className="bg-gray-800 border-gray-700">
                              <SelectValue placeholder="Select weight class" />
                            </SelectTrigger>
                            <SelectContent className="bg-gray-800 border-gray-700 max-h-80">
                              {/* Men's Division */}
                              <div className="px-2 py-1 text-xs font-semibold text-blue-400 uppercase tracking-wider">
                                Men's Division
                              </div>
                              {WEIGHT_CLASSES.mens.map(wc => (
                                <SelectItem key={wc.value} value={wc.value} className="text-white">
                                  {wc.label}
                                </SelectItem>
                              ))}
                              
                              {/* Women's Division */}
                              <div className="px-2 py-1 text-xs font-semibold text-pink-400 uppercase tracking-wider mt-2 border-t border-gray-700 pt-2">
                                Women's Division
                              </div>
                              {WEIGHT_CLASSES.womens.map(wc => (
                                <SelectItem key={wc.value} value={wc.value} className="text-white">
                                  {wc.label}
                                </SelectItem>
                              ))}
                              
                              {/* Other */}
                              <div className="px-2 py-1 text-xs font-semibold text-amber-400 uppercase tracking-wider mt-2 border-t border-gray-700 pt-2">
                                Other
                              </div>
                              {WEIGHT_CLASSES.other.map(wc => (
                                <SelectItem key={wc.value} value={wc.value} className="text-white">
                                  {wc.label}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>
                        
                        {/* Rounds */}
                        <div className="space-y-2">
                          <Label>Rounds</Label>
                          <Select value={String(newFight.rounds)} onValueChange={(v) => setNewFight({...newFight, rounds: parseInt(v)})}>
                            <SelectTrigger className="bg-gray-800 border-gray-700">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent className="bg-gray-800 border-gray-700">
                              <SelectItem value="3">3 Rounds</SelectItem>
                              <SelectItem value="5">5 Rounds</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                        
                        {/* Toggles */}
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <Switch 
                              checked={newFight.isTitleFight} 
                              onCheckedChange={(c) => setNewFight({...newFight, isTitleFight: c})}
                            />
                            <Label>Title Fight</Label>
                          </div>
                          <div className="flex items-center gap-2">
                            <Switch 
                              checked={newFight.isMainEvent} 
                              onCheckedChange={(c) => setNewFight({...newFight, isMainEvent: c})}
                            />
                            <Label>Main Event</Label>
                          </div>
                        </div>
                        
                        <Button onClick={handleCreateFight} disabled={isLoading} className="w-full bg-amber-500 hover:bg-amber-600 text-black">
                          {isLoading ? 'Creating...' : 'Add Fight to Card'}
                        </Button>
                      </div>
                    </DialogContent>
                  </Dialog>
                </div>
                
                <ScrollArea className="h-[400px]">
                  <div className="space-y-2">
                    {fights.length === 0 ? (
                      <div className="text-center py-8 text-gray-500">
                        No fights added yet. Click "Add Fight" to start.
                      </div>
                    ) : (
                      fights.map((fight, idx) => (
                        <div 
                          key={fight.bout_id} 
                          className={`p-3 rounded-lg border ${
                            fight.status === 'active' || fight.status === 'in_progress'
                              ? 'bg-green-500/10 border-green-500' 
                              : fight.status === 'completed'
                              ? 'bg-gray-800/50 border-gray-700 opacity-60'
                              : 'bg-gray-800/50 border-gray-700'
                          }`}
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex-1">
                              <div className="flex items-center gap-2">
                                <span className="text-gray-500 text-sm">#{idx + 1}</span>
                                <span className="text-white font-medium">{fight.fighter1}</span>
                                <span className="text-gray-500">vs</span>
                                <span className="text-white font-medium">{fight.fighter2}</span>
                                {fight.is_title_fight && <Crown className="w-4 h-4 text-amber-400" />}
                              </div>
                              <div className="flex items-center gap-2 text-xs text-gray-400 mt-1">
                                <Scale className="w-3 h-3" /> {fight.weight_class || 'TBD'}
                                <Clock className="w-3 h-3 ml-2" /> {fight.totalRounds || fight.total_rounds || 3} rds
                                {fight.is_main_event && <Badge className="bg-amber-600 text-xs ml-2">Main Event</Badge>}
                              </div>
                            </div>
                            <div className="flex items-center gap-2">
                              {fight.status === 'completed' ? (
                                <Badge className="bg-gray-600">Completed</Badge>
                              ) : fight.status === 'active' || fight.status === 'in_progress' ? (
                                <Badge className="bg-green-500">Active</Badge>
                              ) : (
                                <Button 
                                  size="sm" 
                                  onClick={() => handleStartFight(fight)}
                                  className="bg-green-600 hover:bg-green-700"
                                >
                                  <Play className="w-3 h-3 mr-1" /> Start
                                </Button>
                              )}
                              <Button 
                                size="sm" 
                                variant="ghost" 
                                onClick={() => handleDeleteFight(fight.bout_id)}
                                className="text-red-400 hover:text-red-300"
                              >
                                <Trash2 className="w-4 h-4" />
                              </Button>
                            </div>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </ScrollArea>
              </Card>

              {/* Operators Panel */}
              <Card className="p-4 bg-gray-800/50 border-gray-700">
                <div className="flex items-center gap-2 text-white mb-4">
                  <Users className="w-5 h-5" />
                  <h2 className="font-semibold">Connected Operators</h2>
                  {activeFight && (
                    <Badge className="bg-gray-700 ml-auto">{operators.length}/3</Badge>
                  )}
                </div>
                
                {!activeFight ? (
                  <div className="text-center py-8 text-gray-500">
                    Start a fight to see connected operators
                  </div>
                ) : (
                  <>
                    {/* Operator URL */}
                    <div className="bg-gray-900/50 rounded-lg p-3 mb-4">
                      <div className="text-gray-400 text-xs uppercase tracking-wider mb-1">
                        Operators should open:
                      </div>
                      <code className="text-amber-400 text-sm break-all">
                        {window.location.origin}/waiting/{activeFight.bout_id}
                      </code>
                    </div>
                    
                    {/* Role Assignments */}
                    <div className="space-y-2">
                      {['RED_STRIKING', 'RED_GRAPPLING', 'BLUE_ALL'].map((role) => {
                        const op = operators.find(o => o.assigned_role === role);
                        const roleConfig = {
                          RED_STRIKING: { label: 'Red Striking', color: 'red' },
                          RED_GRAPPLING: { label: 'Red Grappling', color: 'red' },
                          BLUE_ALL: { label: 'Blue All', color: 'blue' }
                        }[role];
                        
                        return (
                          <div 
                            key={role}
                            className={`p-3 rounded-lg border ${
                              op ? `bg-${roleConfig.color}-500/10 border-${roleConfig.color}-500/50` : 'bg-gray-900/50 border-gray-700 border-dashed'
                            }`}
                          >
                            <div className="flex items-center justify-between">
                              <div className={`font-medium ${roleConfig.color === 'red' ? 'text-red-400' : 'text-blue-400'}`}>
                                {roleConfig.label}
                              </div>
                              {op ? (
                                <div className="flex items-center gap-2">
                                  <span className="text-white">{op.device_name}</span>
                                  <div className={`w-2 h-2 rounded-full ${op.is_active ? 'bg-green-500' : 'bg-red-500'}`} />
                                </div>
                              ) : (
                                <span className="text-gray-500 text-sm">Waiting...</span>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                    
                    {/* Waiting operators */}
                    {operators.filter(o => !o.assigned_role).length > 0 && (
                      <div className="mt-4 pt-4 border-t border-gray-700">
                        <div className="text-gray-400 text-sm mb-2">Waiting for assignment:</div>
                        <div className="space-y-1">
                          {operators.filter(o => !o.assigned_role).map((op) => (
                            <div key={op.device_id} className="flex items-center justify-between text-sm bg-amber-500/10 rounded px-2 py-1">
                              <span className="text-amber-400">{op.device_name}</span>
                              <div className="flex gap-1">
                                {['RED_STRIKING', 'RED_GRAPPLING', 'BLUE_ALL'].map((role) => {
                                  const taken = operators.find(o => o.assigned_role === role);
                                  if (taken) return null;
                                  return (
                                    <Button 
                                      key={role} 
                                      size="sm" 
                                      variant="ghost"
                                      onClick={async () => {
                                        await fetch(`${API}/api/operators/assign`, {
                                          method: 'POST',
                                          headers: { 'Content-Type': 'application/json' },
                                          body: JSON.stringify({
                                            bout_id: activeFight.bout_id,
                                            device_id: op.device_id,
                                            role: role
                                          })
                                        });
                                        fetchOperators();
                                        toast.success(`Assigned ${op.device_name} to ${role}`);
                                      }}
                                      className={`text-xs h-6 ${role.includes('RED') ? 'text-red-400' : 'text-blue-400'}`}
                                    >
                                      {role.replace('_', ' ')}
                                    </Button>
                                  );
                                })}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </>
                )}
              </Card>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
