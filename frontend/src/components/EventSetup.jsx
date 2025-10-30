import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import firebase from 'firebase/compat/app';
import { db } from '@/firebase';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { toast } from 'sonner';
import { Swords, Plus, Trash2, GraduationCap, AlertTriangle, Settings, Shield, User } from 'lucide-react';

export default function EventSetup() {
  const navigate = useNavigate();
  const [eventName, setEventName] = useState('');
  const [fights, setFights] = useState([
    { fighter1: '', fighter2: '', rounds: '3' }
  ]);
  const [loading, setLoading] = useState(false);

  const addFight = () => {
    if (fights.length < 15) {
      setFights([...fights, { fighter1: '', fighter2: '', rounds: '3' }]);
    } else {
      toast.error('Maximum 15 fights allowed per event');
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
        createdAt: firebase.firestore.FieldValue.serverTimestamp(),
        status: 'pending'
      });

      // Create bout documents for each fight
      const boutPromises = validFights.map(async (fight, index) => {
        return await db.collection('bouts').add({
          eventId: eventRef.id,
          eventName: eventName.trim(),
          fighter1: fight.fighter1.trim(),
          fighter2: fight.fighter2.trim(),
          totalRounds: parseInt(fight.rounds),
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

          <div className="border-t border-[#2a2d35] pt-3">
            <div className="flex items-center justify-between mb-3">
              <Label className="text-gray-300 text-sm font-medium">Fights ({fights.length}/15)</Label>
              <Button
                data-testid="add-fight-btn"
                onClick={addFight}
                disabled={fights.length >= 15}
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
                        <div className="space-y-1">
                          <Label className="text-xs text-gray-400">Fighter 1 (Red Corner)</Label>
                          <Input
                            data-testid={`fighter1-input-${index}`}
                            placeholder="Enter name"
                            value={fight.fighter1}
                            onChange={(e) => updateFight(index, 'fighter1', e.target.value)}
                            className="h-9 bg-[#13151a] border-[#2a2d35] text-white placeholder:text-gray-600"
                          />
                        </div>
                        <div className="space-y-1">
                          <Label className="text-xs text-gray-400">Fighter 2 (Blue Corner)</Label>
                          <Input
                            data-testid={`fighter2-input-${index}`}
                            placeholder="Enter name"
                            value={fight.fighter2}
                            onChange={(e) => updateFight(index, 'fighter2', e.target.value)}
                            className="h-9 bg-[#13151a] border-[#2a2d35] text-white placeholder:text-gray-600"
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

          <div className="pt-3">
            <Button
              data-testid="create-event-btn"
              onClick={createEvent}
              disabled={loading}
              className="w-full h-12 text-base font-semibold bg-gradient-to-r from-amber-500 to-orange-600 hover:from-amber-600 hover:to-orange-700 text-white shadow-lg transition-all duration-200"
            >
              {loading ? 'Creating Event...' : 'Create Event & Continue'}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
