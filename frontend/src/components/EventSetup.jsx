import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import firebase from 'firebase/compat/app';
import { db } from '@/firebase';
import deviceSyncManager from '@/utils/deviceSync';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Checkbox } from '@/components/ui/checkbox';
import { toast } from 'sonner';
import { Swords, Plus, Trash2, GraduationCap, AlertTriangle, Settings, Shield, User, ClipboardCheck, History } from 'lucide-react';

export default function EventSetup() {
  const navigate = useNavigate();
  const [eventName, setEventName] = useState('');
  const [videoUrl, setVideoUrl] = useState('');
  const [fights, setFights] = useState([
    { fighter1: '', fighter2: '', rounds: '3' }
  ]);
  const [loading, setLoading] = useState(false);
  const [showChecklist, setShowChecklist] = useState(false);
  const [checklistCompleted, setChecklistCompleted] = useState(false);

  // Initialize device sync for event setup
  useEffect(() => {
    const initSync = async () => {
      try {
        await deviceSyncManager.initializeDevice('event-setup', 'admin', {
          role: 'event_admin',
          page: 'event_setup'
        });
      } catch (error) {
        console.error('Device sync init failed:', error);
      }
    };
    initSync();
    return () => deviceSyncManager.cleanup();
  }, []);
  const [checklist, setChecklist] = useState({
    eventName: false,
    fighters: false,
    rounds: false,
    judgeLogin: false,
    internetCheck: false,
    equipmentReady: false
  });

  const addFight = () => {
    if (fights.length < 30) {
      setFights([...fights, { fighter1: '', fighter2: '', rounds: '3' }]);
    } else {
      toast.error('Maximum 30 fights allowed per event');
    }
  };

  const removeFight = (index) => {
    if (fights.length > 1) {
      setFights(fights.filter((_, i) => i !== index));
    } else {
      toast.error('At least one fight is required');
    }
  };

  const updateFight = (index, field, value) => {
    const newFights = [...fights];
    newFights[index][field] = value;
    setFights(newFights);
  };

  const createEvent = async () => {
    // Check if checklist is completed
    if (!checklistCompleted) {
      toast.error('Please complete the Pre-Flight Checklist first');
      // Auto-open checklist
      const judgeProfile = localStorage.getItem('judgeProfile');
      setChecklist({
        eventName: !!eventName,
        fighters: fights.every(f => f.fighter1 && f.fighter2),
        rounds: fights.every(f => f.rounds),
        judgeLogin: !!judgeProfile,
        internetCheck: navigator.onLine,
        equipmentReady: false
      });
      setShowChecklist(true);
      return;
    }

    // Validation
    if (!eventName.trim()) {
      toast.error('Please enter an event name');
      return;
    }

    const validFights = fights.filter(f => f.fighter1.trim() && f.fighter2.trim());
    if (validFights.length === 0) {
      toast.error('Please add at least one complete fight');
      return;
    }

    setLoading(true);
    try {
      // Create event document
      const eventRef = await db.collection('events_main').add({
        eventName: eventName.trim(),
        videoUrl: videoUrl.trim(),
        createdAt: firebase.firestore.FieldValue.serverTimestamp(),
        status: 'pending'
      });

      // Create bout documents for each fight
      const boutPromises = validFights.map(async (fight, index) => {
        return await db.collection('bouts').add({
          eventId: eventRef.id,
          eventName: eventName.trim(),
          videoUrl: videoUrl.trim(),
          fighter1: fight.fighter1.trim(),
          fighter2: fight.fighter2.trim(),
          totalRounds: parseInt(fight.rounds === '5-non-title' ? '5' : fight.rounds),
          currentRound: 1,
          status: 'pending',
          fightOrder: index + 1,
          createdAt: firebase.firestore.FieldValue.serverTimestamp()
        });
      });

      await Promise.all(boutPromises);

      toast.success(`Event created with ${validFights.length} fights!`);
      navigate(`/event/${eventRef.id}/fights`);
    } catch (error) {
      console.error('Error creating event:', error);
      toast.error('Failed to create event');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-2" style={{
      background: 'linear-gradient(135deg, #0f1419 0%, #1a1f2e 50%, #0f1419 100%)'
    }}>
      <Card className="w-full max-w-4xl bg-[#13151a]/95 border-[#2a2d35] backdrop-blur-xl shadow-2xl">
        <CardHeader className="text-center space-y-2 pb-4">
          <div className="flex flex-wrap justify-center gap-2 mb-1">
            <Button
              onClick={() => navigate('/profile')}
              className="bg-gradient-to-r from-indigo-600 to-indigo-700 hover:from-indigo-700 hover:to-indigo-800 text-white text-sm px-3 py-2"
            >
              <User className="mr-1.5 h-3.5 w-3.5" />
              Profile
            </Button>
            <Button
              onClick={() => navigate('/tuning-profiles')}
              className="bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 text-white text-sm px-3 py-2"
            >
              <Settings className="mr-1.5 h-3.5 w-3.5" />
              Tuning
            </Button>
            <Button
              onClick={() => navigate('/review-dashboard')}
              className="bg-gradient-to-r from-red-600 to-red-700 hover:from-red-700 hover:to-red-800 text-white text-sm px-3 py-2"
            >
              <AlertTriangle className="mr-1.5 h-3.5 w-3.5" />
              Review
            </Button>
            <Button
              onClick={() => navigate('/shadow-judging')}
              className="bg-gradient-to-r from-purple-600 to-purple-700 hover:from-purple-700 hover:to-purple-800 text-white text-sm px-3 py-2"
            >
              <GraduationCap className="mr-1.5 h-3.5 w-3.5" />
              Training
            </Button>
            <Button
              onClick={() => navigate('/audit-logs')}
              className="bg-gradient-to-r from-gray-600 to-gray-700 hover:from-gray-700 hover:to-gray-800 text-white text-sm px-3 py-2"
            >
              <Shield className="mr-1.5 h-3.5 w-3.5" />
              Audit
            </Button>
            <Button
              onClick={() => navigate('/fight-history')}
              className="bg-gradient-to-r from-purple-600 to-purple-700 hover:from-purple-700 hover:to-purple-800 text-white text-sm px-3 py-2"
            >
              <History className="mr-1.5 h-3.5 w-3.5" />
              Fight History
            </Button>
            <Button
              onClick={() => {
                // Auto-check items
                const judgeProfile = localStorage.getItem('judgeProfile');
                setChecklist({
                  eventName: !!eventName,
                  fighters: fights.every(f => f.fighter1 && f.fighter2),
                  rounds: fights.every(f => f.rounds),
                  judgeLogin: !!judgeProfile,
                  internetCheck: navigator.onLine,
                  equipmentReady: false
                });
                setShowChecklist(true);
              }}
              className="bg-gradient-to-r from-green-600 to-green-700 hover:from-green-700 hover:to-green-800 text-white text-sm px-3 py-2"
            >
              <ClipboardCheck className="mr-1.5 h-3.5 w-3.5" />
              Pre-Fight Checklist
            </Button>
          </div>
          <div className="mx-auto w-16 h-16 bg-gradient-to-br from-amber-500 to-orange-600 rounded-2xl flex items-center justify-center shadow-lg">
            <Swords className="w-8 h-8 text-white" />
          </div>
          <CardTitle className="text-3xl font-bold tracking-tight" style={{
            background: 'linear-gradient(135deg, #fbbf24 0%, #f97316 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent'
          }}>
            Combat Judging System
          </CardTitle>
          <CardDescription className="text-base text-gray-400">
            Create event and add fights (up to 15)
          </CardDescription>
        </CardHeader>
        
        <CardContent className="space-y-4 max-h-[50vh] overflow-y-auto">
          {/* Event Name */}
          <div className="space-y-1">
            <Label htmlFor="eventName" className="text-gray-300 text-sm font-medium">Event Name</Label>
            <Input
              id="eventName"
              data-testid="event-name-input"
              placeholder="e.g., UFC 300, Bellator 250"
              value={eventName}
              onChange={(e) => setEventName(e.target.value)}
              className="h-10 bg-[#1a1d24] border-[#2a2d35] text-white placeholder:text-gray-500 focus:border-amber-500 focus:ring-amber-500/20"
            />
          </div>

          {/* Video URL */}
          <div className="space-y-1">
            <Label htmlFor="videoUrl" className="text-gray-300 text-sm font-medium">YouTube Live URL (Optional)</Label>
            <Input
              id="videoUrl"
              placeholder="e.g., https://www.youtube.com/watch?v=..."
              value={videoUrl}
              onChange={(e) => setVideoUrl(e.target.value)}
              className="h-10 bg-[#1a1d24] border-[#2a2d35] text-white placeholder:text-gray-500 focus:border-amber-500 focus:ring-amber-500/20"
            />
          </div>

          <div className="border-t border-[#2a2d35] pt-3">
            <div className="flex items-center justify-between mb-3">
              <Label className="text-gray-300 text-sm font-medium">Fights ({fights.length}/30)</Label>
              <Button
                data-testid="add-fight-btn"
                onClick={addFight}
                disabled={fights.length >= 30}
                className="h-8 px-3 bg-gradient-to-r from-green-600 to-green-700 hover:from-green-700 hover:to-green-800 text-white text-sm disabled:opacity-50"
              >
                <Plus className="w-4 h-4 mr-1" />
                Add Fight
              </Button>
            </div>

            {/* Fights List */}
            <div className="space-y-3">
              {fights.map((fight, index) => (
                <Card key={index} className="bg-[#1a1d24] border-[#2a2d35] p-3">
                  <div className="flex items-start gap-2">
                    <div className="text-gray-500 font-bold mt-2 min-w-[25px]">#{index + 1}</div>
                    
                    <div className="flex-1 space-y-2">
                      <div className="grid md:grid-cols-2 gap-2">
                        {/* Fighter 1 */}
                        <div className="space-y-1">
                          <Label className="text-xs text-gray-400">Fighter 1 (Red Corner)</Label>
                          <Input
                            data-testid={`fighter1-input-${index}`}
                            placeholder="Enter name"
                            value={fight.fighter1}
                            onChange={(e) => updateFight(index, 'fighter1', e.target.value)}
                            className="h-9 bg-[#13151a] border-[#2a2d35] text-white placeholder:text-gray-600"
                          />
                          <Input
                            data-testid={`fighter1-photo-${index}`}
                            placeholder="Photo URL (optional)"
                            value={fight.fighter1Photo || ''}
                            onChange={(e) => updateFight(index, 'fighter1Photo', e.target.value)}
                            className="h-8 text-xs bg-[#13151a] border-[#2a2d35] text-white placeholder:text-gray-600"
                          />
                        </div>
                        {/* Fighter 2 */}
                        <div className="space-y-1">
                          <Label className="text-xs text-gray-400">Fighter 2 (Blue Corner)</Label>
                          <Input
                            data-testid={`fighter2-input-${index}`}
                            placeholder="Enter name"
                            value={fight.fighter2}
                            onChange={(e) => updateFight(index, 'fighter2', e.target.value)}
                            className="h-9 bg-[#13151a] border-[#2a2d35] text-white placeholder:text-gray-600"
                          />
                          <Input
                            data-testid={`fighter2-photo-${index}`}
                            placeholder="Photo URL (optional)"
                            value={fight.fighter2Photo || ''}
                            onChange={(e) => updateFight(index, 'fighter2Photo', e.target.value)}
                            className="h-8 text-xs bg-[#13151a] border-[#2a2d35] text-white placeholder:text-gray-600"
                          />
                        </div>
                      </div>
                      
                      <div className="flex items-center gap-2">
                        <div className="flex-1">
                          <Label className="text-xs text-gray-400 mb-1 block">Rounds</Label>
                          <Select 
                            value={fight.rounds} 
                            onValueChange={(value) => updateFight(index, 'rounds', value)}
                          >
                            <SelectTrigger className="h-9 bg-[#13151a] border-[#2a2d35] text-white">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent className="bg-[#1a1d24] border-[#2a2d35]">
                              <SelectItem value="3">3 Rounds (Standard)</SelectItem>
                              <SelectItem value="5">5 Rounds (Title Fight)</SelectItem>
                              <SelectItem value="5-non-title">5 Rounds (Non-Title)</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                      </div>
                    </div>

                    <Button
                      data-testid={`remove-fight-btn-${index}`}
                      onClick={() => removeFight(index)}
                      disabled={fights.length === 1}
                      className="mt-6 h-9 w-9 p-0 bg-red-900/30 hover:bg-red-900/50 text-red-400 border border-red-800/30 disabled:opacity-30"
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                </Card>
              ))}
            </div>
          </div>

          <div className="pt-3 space-y-2">
            {!checklistCompleted && (
              <div className="p-3 bg-amber-900/20 border border-amber-700/30 rounded-lg text-center">
                <p className="text-amber-400 text-sm font-semibold">⚠️ Pre-Flight Checklist Required</p>
                <p className="text-amber-300 text-xs mt-1">Complete the checklist before creating the event</p>
              </div>
            )}
            <Button
              data-testid="create-event-btn"
              onClick={createEvent}
              disabled={loading}
              className="w-full h-12 text-base font-semibold bg-gradient-to-r from-amber-500 to-orange-600 hover:from-amber-600 hover:to-orange-700 text-white shadow-lg transition-all duration-200"
            >
              {loading ? 'Creating Event...' : checklistCompleted ? 'Create Event & Continue' : '⚠️ Complete Checklist First'}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Pre-Fight Checklist Dialog */}
      <Dialog open={showChecklist} onOpenChange={setShowChecklist}>
        <DialogContent className="bg-[#13151a] border-[#2a2d35] max-w-md">
          <DialogHeader>
            <DialogTitle className="text-white flex items-center gap-2">
              <ClipboardCheck className="h-5 w-5 text-green-400" />
              Pre-Fight Checklist
            </DialogTitle>
          </DialogHeader>
          <div className="py-4 space-y-4">
            <p className="text-sm text-gray-400">Ensure everything is ready before starting the fight:</p>
            
            <div className="space-y-3">
              <div className="flex items-center space-x-3 p-3 bg-[#1a1d24] rounded-lg border border-[#2a2d35]">
                <Checkbox
                  id="check-event"
                  checked={checklist.eventName}
                  onCheckedChange={(checked) => setChecklist({...checklist, eventName: checked})}
                  className="border-gray-600"
                />
                <label htmlFor="check-event" className="text-sm text-gray-300 cursor-pointer flex-1">
                  Event name entered
                  {checklist.eventName && <span className="ml-2 text-green-400">✓</span>}
                </label>
              </div>

              <div className="flex items-center space-x-3 p-3 bg-[#1a1d24] rounded-lg border border-[#2a2d35]">
                <Checkbox
                  id="check-fighters"
                  checked={checklist.fighters}
                  onCheckedChange={(checked) => setChecklist({...checklist, fighters: checked})}
                  className="border-gray-600"
                />
                <label htmlFor="check-fighters" className="text-sm text-gray-300 cursor-pointer flex-1">
                  Fighter names entered (Red & Blue)
                  {checklist.fighters && <span className="ml-2 text-green-400">✓</span>}
                </label>
              </div>

              <div className="flex items-center space-x-3 p-3 bg-[#1a1d24] rounded-lg border border-[#2a2d35]">
                <Checkbox
                  id="check-rounds"
                  checked={checklist.rounds}
                  onCheckedChange={(checked) => setChecklist({...checklist, rounds: checked})}
                  className="border-gray-600"
                />
                <label htmlFor="check-rounds" className="text-sm text-gray-300 cursor-pointer flex-1">
                  Number of rounds selected
                  {checklist.rounds && <span className="ml-2 text-green-400">✓</span>}
                </label>
              </div>

              <div className="flex items-center space-x-3 p-3 bg-[#1a1d24] rounded-lg border border-[#2a2d35]">
                <Checkbox
                  id="check-judge"
                  checked={checklist.judgeLogin}
                  onCheckedChange={(checked) => setChecklist({...checklist, judgeLogin: checked})}
                  className="border-gray-600"
                />
                <label htmlFor="check-judge" className="text-sm text-gray-300 cursor-pointer flex-1">
                  Judge logged in
                  {checklist.judgeLogin && <span className="ml-2 text-green-400">✓</span>}
                </label>
              </div>

              <div className="flex items-center space-x-3 p-3 bg-[#1a1d24] rounded-lg border border-[#2a2d35]">
                <Checkbox
                  id="check-internet"
                  checked={checklist.internetCheck}
                  onCheckedChange={(checked) => setChecklist({...checklist, internetCheck: checked})}
                  className="border-gray-600"
                />
                <label htmlFor="check-internet" className="text-sm text-gray-300 cursor-pointer flex-1">
                  Internet connection stable
                  {checklist.internetCheck && <span className="ml-2 text-green-400">✓</span>}
                </label>
              </div>

              <div className="flex items-center space-x-3 p-3 bg-[#1a1d24] rounded-lg border border-[#2a2d35]">
                <Checkbox
                  id="check-equipment"
                  checked={checklist.equipmentReady}
                  onCheckedChange={(checked) => setChecklist({...checklist, equipmentReady: checked})}
                  className="border-gray-600"
                />
                <label htmlFor="check-equipment" className="text-sm text-gray-300 cursor-pointer flex-1">
                  Equipment ready (devices, backup)
                  {checklist.equipmentReady && <span className="ml-2 text-green-400">✓</span>}
                </label>
              </div>
            </div>

            {Object.values(checklist).every(v => v) && (
              <div className="p-3 bg-green-900/20 border border-green-700/30 rounded-lg text-center">
                <p className="text-green-400 font-semibold">✓ All checks complete - Ready to start!</p>
              </div>
            )}

            <div className="flex gap-2 pt-2">
              <Button
                onClick={() => setShowChecklist(false)}
                className="flex-1 bg-gray-700 hover:bg-gray-600 text-white"
              >
                Close
              </Button>
              {Object.values(checklist).every(v => v) && (
                <Button
                  onClick={() => {
                    setChecklistCompleted(true);
                    setShowChecklist(false);
                    toast.success('Pre-flight checklist complete! You can now create the event.');
                  }}
                  className="flex-1 bg-green-600 hover:bg-green-700 text-white"
                >
                  Confirm & Start
                </Button>
              )}
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
