import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { toast } from 'sonner';
import { History, Trophy, Search, ChevronRight, Calendar, Users, Activity, ArrowLeft } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function FightHistory() {
  const navigate = useNavigate();
  const [fights, setFights] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [totalFights, setTotalFights] = useState(0);

  useEffect(() => {
    loadCompletedFights();
  }, []);

  const loadCompletedFights = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${API}/fights/completed?limit=100`);
      if (!response.ok) throw new Error('Failed to load fights');
      
      const data = await response.json();
      setFights(data.fights || []);
      setTotalFights(data.total || 0);
    } catch (error) {
      console.error('Error loading fights:', error);
      toast.error('Failed to load fight history');
    } finally {
      setLoading(false);
    }
  };

  const filteredFights = fights.filter(fight => {
    const query = searchQuery.toLowerCase();
    const fighter1 = fight.fighter1?.name?.toLowerCase() || '';
    const fighter2 = fight.fighter2?.name?.toLowerCase() || '';
    const event = fight.event?.event_name?.toLowerCase() || '';
    
    return fighter1.includes(query) || fighter2.includes(query) || event.includes(query);
  });

  const getWinnerBadge = (winner, fighter1Name, fighter2Name) => {
    if (winner === 'fighter1') {
      return <Badge className="bg-red-600 text-white">{fighter1Name} Won</Badge>;
    } else if (winner === 'fighter2') {
      return <Badge className="bg-blue-600 text-white">{fighter2Name} Won</Badge>;
    } else if (winner === 'draw') {
      return <Badge className="bg-yellow-600 text-white">Draw</Badge>;
    }
    return <Badge className="bg-gray-600 text-white">TBD</Badge>;
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return 'Unknown Date';
    try {
      return new Date(dateStr).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return 'Unknown Date';
    }
  };

  return (
    <div className="min-h-screen bg-[#0a0a0b] p-6">
      {/* Header */}
      <div className="max-w-6xl mx-auto mb-8">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-4">
            <Button
              onClick={() => navigate('/')}
              variant="ghost"
              className="text-gray-400 hover:text-white"
            >
              <ArrowLeft className="h-5 w-5 mr-2" />
              Back
            </Button>
            <div>
              <h1 className="text-3xl font-bold text-amber-500 flex items-center gap-3">
                <History className="h-8 w-8" />
                Fight History
              </h1>
              <p className="text-gray-400 mt-1">
                {totalFights} completed {totalFights === 1 ? 'fight' : 'fights'} archived
              </p>
            </div>
          </div>
          
          <Button
            onClick={loadCompletedFights}
            className="bg-amber-600 hover:bg-amber-700 text-white"
          >
            <Activity className="h-4 w-4 mr-2" />
            Refresh
          </Button>
        </div>

        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-500" />
          <Input
            placeholder="Search by fighter name or event..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10 bg-[#13151a] border-[#2a2d35] text-white h-12"
          />
        </div>
      </div>

      {/* Fight List */}
      <div className="max-w-6xl mx-auto">
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="text-gray-400">Loading fight history...</div>
          </div>
        ) : filteredFights.length === 0 ? (
          <Card className="bg-[#13151a] border-[#2a2d35] p-12 text-center">
            <Trophy className="h-16 w-16 text-gray-600 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-gray-400 mb-2">
              {searchQuery ? 'No fights match your search' : 'No completed fights yet'}
            </h3>
            <p className="text-gray-500">
              {searchQuery 
                ? 'Try a different search term' 
                : 'Completed fights will appear here after they are archived'}
            </p>
          </Card>
        ) : (
          <div className="space-y-4">
            {filteredFights.map((fight, index) => (
              <Card 
                key={fight.bout_id || index}
                className="bg-[#13151a] border-[#2a2d35] p-6 hover:border-amber-500/50 transition-all cursor-pointer"
                onClick={() => navigate(`/fight-details/${fight.bout_id}`)}
              >
                <div className="flex items-center justify-between">
                  {/* Fight Info */}
                  <div className="flex-1">
                    <div className="flex items-center gap-4 mb-3">
                      <div className="flex items-center gap-2 text-sm text-gray-400">
                        <Calendar className="h-4 w-4" />
                        {formatDate(fight.completed_at)}
                      </div>
                      {fight.event?.event_name && (
                        <Badge variant="outline" className="text-amber-500 border-amber-500/30">
                          {fight.event.event_name}
                        </Badge>
                      )}
                    </div>
                    
                    {/* Fighters */}
                    <div className="flex items-center gap-4">
                      <div className="flex items-center gap-3">
                        <div className="w-3 h-3 rounded-full bg-red-500"></div>
                        <span className="text-xl font-bold text-white">
                          {fight.fighter1?.name || 'Fighter 1'}
                        </span>
                      </div>
                      
                      <span className="text-gray-500 font-semibold">vs</span>
                      
                      <div className="flex items-center gap-3">
                        <div className="w-3 h-3 rounded-full bg-blue-500"></div>
                        <span className="text-xl font-bold text-white">
                          {fight.fighter2?.name || 'Fighter 2'}
                        </span>
                      </div>
                    </div>

                    {/* Stats Summary */}
                    <div className="flex items-center gap-6 mt-4 text-sm">
                      <div className="flex items-center gap-2 text-gray-400">
                        <Users className="h-4 w-4" />
                        {fight.fight_details?.total_rounds || 3} Rounds
                      </div>
                      <div className="text-gray-400">
                        Method: <span className="text-white">{fight.fight_details?.method || 'Decision'}</span>
                      </div>
                    </div>
                  </div>

                  {/* Winner Badge & Arrow */}
                  <div className="flex items-center gap-4">
                    {getWinnerBadge(
                      fight.fight_details?.winner,
                      fight.fighter1?.name,
                      fight.fighter2?.name
                    )}
                    <ChevronRight className="h-6 w-6 text-gray-500" />
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
