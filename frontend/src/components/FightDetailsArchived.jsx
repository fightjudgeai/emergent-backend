import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { toast } from 'sonner';
import { ArrowLeft, Trophy, Target, Shield, Clock, Zap, Activity } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function FightDetailsPage() {
  const { boutId } = useParams();
  const navigate = useNavigate();
  const [fight, setFight] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadFightDetails();
  }, [boutId]);

  const loadFightDetails = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${API}/fight/completed/${boutId}`);
      if (!response.ok) {
        if (response.status === 404) {
          toast.error('Fight not found');
          navigate('/fight-history');
          return;
        }
        throw new Error('Failed to load fight details');
      }
      
      const data = await response.json();
      setFight(data);
    } catch (error) {
      console.error('Error loading fight:', error);
      toast.error('Failed to load fight details');
    } finally {
      setLoading(false);
    }
  };

  const formatTime = (seconds) => {
    if (!seconds) return '0:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const StatCard = ({ label, value, icon: Icon, color = 'amber' }) => (
    <div className="bg-[#1a1d24] rounded-lg p-4 border border-[#2a2d35]">
      <div className="flex items-center gap-2 mb-2">
        <Icon className={`h-4 w-4 text-${color}-500`} />
        <span className="text-sm text-gray-400">{label}</span>
      </div>
      <div className="text-2xl font-bold text-white">{value}</div>
    </div>
  );

  const FighterStats = ({ fighter, stats, color }) => (
    <Card className={`bg-[#13151a] border-2 ${color === 'red' ? 'border-red-600/50' : 'border-blue-600/50'} p-6`}>
      <div className="flex items-center gap-3 mb-6">
        <div className={`w-4 h-4 rounded-full ${color === 'red' ? 'bg-red-500' : 'bg-blue-500'}`}></div>
        <h3 className="text-2xl font-bold text-white">{fighter.name}</h3>
        <Badge variant="outline" className="text-gray-400">
          {fighter.corner} corner
        </Badge>
      </div>

      {/* Striking Stats */}
      <div className="mb-6">
        <h4 className="text-amber-500 font-semibold mb-3 flex items-center gap-2">
          <Zap className="h-4 w-4" />
          Striking
        </h4>
        <div className="grid grid-cols-2 gap-3 text-sm">
          <div className="flex justify-between p-2 bg-[#1a1d24] rounded">
            <span className="text-gray-400">Total Strikes</span>
            <span className="text-white font-semibold">{stats?.striking?.total_strikes || 0}</span>
          </div>
          <div className="flex justify-between p-2 bg-[#1a1d24] rounded">
            <span className="text-gray-400">Significant</span>
            <span className="text-white font-semibold">{stats?.striking?.significant_strikes || 0}</span>
          </div>
          <div className="flex justify-between p-2 bg-[#1a1d24] rounded">
            <span className="text-gray-400">Jabs</span>
            <span className="text-white font-semibold">{stats?.striking?.jabs || 0}</span>
          </div>
          <div className="flex justify-between p-2 bg-[#1a1d24] rounded">
            <span className="text-gray-400">Crosses</span>
            <span className="text-white font-semibold">{stats?.striking?.crosses || 0}</span>
          </div>
          <div className="flex justify-between p-2 bg-[#1a1d24] rounded">
            <span className="text-gray-400">Hooks</span>
            <span className="text-white font-semibold">{stats?.striking?.hooks || 0}</span>
          </div>
          <div className="flex justify-between p-2 bg-[#1a1d24] rounded">
            <span className="text-gray-400">Kicks</span>
            <span className="text-white font-semibold">{stats?.striking?.kicks || 0}</span>
          </div>
        </div>
      </div>

      {/* Damage Stats */}
      <div className="mb-6">
        <h4 className="text-red-500 font-semibold mb-3 flex items-center gap-2">
          <Target className="h-4 w-4" />
          Damage Dealt
        </h4>
        <div className="grid grid-cols-2 gap-3 text-sm">
          <div className="flex justify-between p-2 bg-[#1a1d24] rounded">
            <span className="text-gray-400">Knockdowns</span>
            <span className="text-white font-semibold">{stats?.damage?.knockdowns || 0}</span>
          </div>
          <div className="flex justify-between p-2 bg-[#1a1d24] rounded">
            <span className="text-gray-400">Rocked</span>
            <span className="text-white font-semibold">{stats?.damage?.rocked || 0}</span>
          </div>
        </div>
      </div>

      {/* Grappling Stats */}
      <div className="mb-6">
        <h4 className="text-blue-500 font-semibold mb-3 flex items-center gap-2">
          <Shield className="h-4 w-4" />
          Grappling
        </h4>
        <div className="grid grid-cols-2 gap-3 text-sm">
          <div className="flex justify-between p-2 bg-[#1a1d24] rounded">
            <span className="text-gray-400">Takedowns</span>
            <span className="text-white font-semibold">{stats?.grappling?.takedowns_landed || 0}</span>
          </div>
          <div className="flex justify-between p-2 bg-[#1a1d24] rounded">
            <span className="text-gray-400">TD Stuffed</span>
            <span className="text-white font-semibold">{stats?.grappling?.takedowns_stuffed || 0}</span>
          </div>
          <div className="flex justify-between p-2 bg-[#1a1d24] rounded">
            <span className="text-gray-400">Sub Attempts</span>
            <span className="text-white font-semibold">{stats?.grappling?.submission_attempts || 0}</span>
          </div>
          <div className="flex justify-between p-2 bg-[#1a1d24] rounded">
            <span className="text-gray-400">Guard Passes</span>
            <span className="text-white font-semibold">{stats?.grappling?.guard_passes || 0}</span>
          </div>
        </div>
      </div>

      {/* Control Stats */}
      <div>
        <h4 className="text-purple-500 font-semibold mb-3 flex items-center gap-2">
          <Clock className="h-4 w-4" />
          Control Time
        </h4>
        <div className="grid grid-cols-1 gap-3 text-sm">
          <div className="flex justify-between p-2 bg-[#1a1d24] rounded">
            <span className="text-gray-400">Total Control</span>
            <span className="text-white font-semibold">{formatTime(stats?.control?.total_control_seconds)}</span>
          </div>
          <div className="flex justify-between p-2 bg-[#1a1d24] rounded">
            <span className="text-gray-400">Ground Top</span>
            <span className="text-white font-semibold">{formatTime(stats?.control?.ground_top_seconds)}</span>
          </div>
          <div className="flex justify-between p-2 bg-[#1a1d24] rounded">
            <span className="text-gray-400">Back Control</span>
            <span className="text-white font-semibold">{formatTime(stats?.control?.ground_back_seconds)}</span>
          </div>
        </div>
      </div>
    </Card>
  );

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0a0a0b] flex items-center justify-center">
        <div className="text-gray-400">Loading fight details...</div>
      </div>
    );
  }

  if (!fight) {
    return (
      <div className="min-h-screen bg-[#0a0a0b] flex items-center justify-center">
        <div className="text-gray-400">Fight not found</div>
      </div>
    );
  }

  const getWinnerName = () => {
    if (fight.fight_details?.winner === 'fighter1') return fight.fighter1?.name;
    if (fight.fight_details?.winner === 'fighter2') return fight.fighter2?.name;
    return 'Draw';
  };

  return (
    <div className="min-h-screen bg-[#0a0a0b] p-6">
      {/* Header */}
      <div className="max-w-6xl mx-auto mb-8">
        <Button
          onClick={() => navigate('/fight-history')}
          variant="ghost"
          className="text-gray-400 hover:text-white mb-4"
        >
          <ArrowLeft className="h-5 w-5 mr-2" />
          Back to Fight History
        </Button>

        <Card className="bg-gradient-to-r from-[#13151a] to-[#1a1d24] border-[#2a2d35] p-8">
          <div className="flex items-center justify-between mb-4">
            <Badge variant="outline" className="text-amber-500 border-amber-500/30">
              {fight.event?.event_name || 'Unknown Event'}
            </Badge>
            <Badge className="bg-green-600 text-white">Completed</Badge>
          </div>

          {/* Main Fight Title */}
          <div className="flex items-center justify-center gap-8 my-8">
            <div className="text-center">
              <div className="w-4 h-4 rounded-full bg-red-500 mx-auto mb-2"></div>
              <h2 className="text-3xl font-bold text-white">{fight.fighter1?.name}</h2>
              <p className="text-gray-400">{fight.fighter1?.weight_class}</p>
            </div>
            
            <div className="text-4xl font-bold text-gray-600">VS</div>
            
            <div className="text-center">
              <div className="w-4 h-4 rounded-full bg-blue-500 mx-auto mb-2"></div>
              <h2 className="text-3xl font-bold text-white">{fight.fighter2?.name}</h2>
              <p className="text-gray-400">{fight.fighter2?.weight_class}</p>
            </div>
          </div>

          {/* Winner */}
          <div className="text-center mb-6">
            <div className="flex items-center justify-center gap-2 mb-2">
              <Trophy className="h-6 w-6 text-amber-500" />
              <span className="text-lg text-gray-400">Winner</span>
            </div>
            <div className="text-2xl font-bold text-amber-500">{getWinnerName()}</div>
            <div className="text-gray-400">
              via {fight.fight_details?.method || 'Decision'} 
              {' '}&bull;{' '}
              {fight.fight_details?.total_rounds || 3} Rounds
            </div>
          </div>

          <Separator className="bg-[#2a2d35] my-6" />

          {/* Quick Stats */}
          <div className="grid grid-cols-4 gap-4">
            <StatCard 
              label="Total Events" 
              value={fight.metadata?.total_events || 0} 
              icon={Activity}
            />
            <StatCard 
              label="F1 Strikes" 
              value={fight.fighter1?.stats?.striking?.total_strikes || 0} 
              icon={Zap}
              color="red"
            />
            <StatCard 
              label="F2 Strikes" 
              value={fight.fighter2?.stats?.striking?.total_strikes || 0} 
              icon={Zap}
              color="blue"
            />
            <StatCard 
              label="Total Rounds" 
              value={fight.fight_details?.total_rounds || 3} 
              icon={Clock}
            />
          </div>
        </Card>
      </div>

      {/* Fighter Stats Comparison */}
      <div className="max-w-6xl mx-auto">
        <h3 className="text-xl font-bold text-white mb-4">Detailed Statistics</h3>
        <div className="grid md:grid-cols-2 gap-6">
          <FighterStats 
            fighter={fight.fighter1} 
            stats={fight.fighter1?.stats} 
            color="red" 
          />
          <FighterStats 
            fighter={fight.fighter2} 
            stats={fight.fighter2?.stats} 
            color="blue" 
          />
        </div>
      </div>
    </div>
  );
}
