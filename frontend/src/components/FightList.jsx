import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { db } from '@/firebase';
import deviceSyncManager from '@/utils/deviceSync';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import { Play, CheckCircle, Clock } from 'lucide-react';

export default function FightList() {
  const { eventId } = useParams();
  const navigate = useNavigate();
  const [event, setEvent] = useState(null);
  const [fights, setFights] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadEventAndFights();
  }, [eventId]);

  const loadEventAndFights = async () => {
    try {
      // Load event
      const eventDoc = await db.collection('events_main').doc(eventId).get();
      if (eventDoc.exists) {
        setEvent({ id: eventDoc.id, ...eventDoc.data() });
      }

      // Load fights for this event (without orderBy to avoid index requirement)
      const fightsSnapshot = await db.collection('bouts')
        .where('eventId', '==', eventId)
        .get();
      
      const fightsData = fightsSnapshot.docs.map(doc => ({
        id: doc.id,
        ...doc.data()
      }));
      
      // Sort manually by fightOrder
      fightsData.sort((a, b) => (a.fightOrder || 0) - (b.fightOrder || 0));
      
      setFights(fightsData);
    } catch (error) {
      console.error('Error loading event:', error);
      toast.error('Failed to load event');
    } finally {
      setLoading(false);
    }
  };

  const openFight = (fightId) => {
    navigate(`/operator/${fightId}`);
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case 'completed':
        return <Badge className="bg-green-900/30 text-green-400 border-green-700/30"><CheckCircle className="w-3 h-3 mr-1" />Completed</Badge>;
      case 'active':
        return <Badge className="bg-blue-900/30 text-blue-400 border-blue-700/30"><Play className="w-3 h-3 mr-1" />Active</Badge>;
      default:
        return <Badge className="bg-gray-800/30 text-gray-400 border-gray-700/30"><Clock className="w-3 h-3 mr-1" />Pending</Badge>;
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#0a0a0b]">
        <p className="text-gray-400">Loading event...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0a0a0b] p-4 md:p-8">
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <Card className="bg-gradient-to-r from-[#1a1d24] to-[#13151a] border-[#2a2d35] p-8 mb-8">
          <div className="text-center">
            <CardTitle className="text-4xl font-bold text-white mb-2">
              {event?.eventName || 'Event'}
            </CardTitle>
            <p className="text-gray-400 text-lg">{fights.length} Fights</p>
          </div>
        </Card>

        {/* Fights List */}
        <div className="space-y-4">
          {fights.map((fight) => (
            <Card 
              key={fight.id} 
              className="bg-[#13151a] border-[#2a2d35] hover:border-amber-500/30 transition-all cursor-pointer"
              data-testid={`fight-card-${fight.fightOrder}`}
            >
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-6 flex-1">
                    {/* Fight Number */}
                    <div className="text-center min-w-[60px]">
                      <div className="text-3xl font-bold text-amber-500" style={{ fontFamily: 'Space Grotesk' }}>
                        #{fight.fightOrder}
                      </div>
                      <div className="text-xs text-gray-500 mt-1">
                        {fight.totalRounds} RDS
                      </div>
                    </div>

                    {/* Fighters */}
                    <div className="flex-1">
                      <div className="flex items-center gap-4 mb-2">
                        <div className="flex-1">
                          <div className="text-sm text-red-400 mb-1">Red Corner</div>
                          <div className="text-xl font-semibold text-white">{fight.fighter1}</div>
                        </div>
                        <div className="text-gray-600 text-2xl font-bold">VS</div>
                        <div className="flex-1">
                          <div className="text-sm text-blue-400 mb-1">Blue Corner</div>
                          <div className="text-xl font-semibold text-white">{fight.fighter2}</div>
                        </div>
                      </div>
                      
                      <div className="flex items-center gap-2 mt-3">
                        {getStatusBadge(fight.status)}
                        {fight.totalRounds === 5 && (
                          <Badge className="bg-amber-900/30 text-amber-400 border-amber-700/30">
                            Title Fight
                          </Badge>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Open Button */}
                  <Button
                    data-testid={`open-fight-btn-${fight.fightOrder}`}
                    onClick={() => openFight(fight.id)}
                    className="h-12 px-6 bg-gradient-to-r from-amber-500 to-orange-600 hover:from-amber-600 hover:to-orange-700 text-white font-semibold"
                  >
                    <Play className="w-4 h-4 mr-2" />
                    Open
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}
