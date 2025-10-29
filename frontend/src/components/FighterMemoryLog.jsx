import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Progress } from '@/components/ui/progress';
import { Users, TrendingUp, Award, Target, Swords, Shield } from 'lucide-react';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export default function FighterMemoryLog({ fighterName }) {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (fighterName) {
      loadFighterStats();
    }
  }, [fighterName]);

  const loadFighterStats = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${BACKEND_URL}/api/fighters/${encodeURIComponent(fighterName)}/stats`);
      
      if (response.status === 404) {
        setStats(null);
        return;
      }
      
      if (!response.ok) throw new Error('Failed to fetch stats');
      
      const data = await response.json();
      setStats(data);
    } catch (error) {
      console.error('Error loading fighter stats:', error);
      toast.error('Failed to load fighter stats');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <Card className="bg-[#13151a] border-[#2a2d35]">
        <CardContent className="py-8">
          <div className="text-gray-400 text-center">Loading fighter stats...</div>
        </CardContent>
      </Card>
    );
  }

  if (!stats) {
    return (
      <Card className="bg-[#13151a] border-[#2a2d35]">
        <CardContent className="py-8">
          <div className="text-gray-500 text-center">No historical data available for {fighterName}</div>
          <div className="text-gray-600 text-sm text-center mt-2">Stats will be recorded after this fighter completes rounds</div>
        </CardContent>
      </Card>
    );
  }

  const winRate = stats.total_rounds > 0 ? ((stats.rounds_won / stats.total_rounds) * 100).toFixed(1) : '0.0';

  return (
    <Card className="bg-[#13151a] border-[#2a2d35]">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-white">
          <Users className="w-5 h-5 text-amber-500" />
          {fighterName} - Fighter Memory Log
        </CardTitle>
      </CardHeader>
      
      <CardContent>
        <Tabs defaultValue="stats" className="w-full">
          <TabsList className="bg-[#1a1d24] border-[#2a2d35]">
            <TabsTrigger value="stats">Statistics</TabsTrigger>
            <TabsTrigger value="tendencies">Tendencies</TabsTrigger>
            <TabsTrigger value="performance">Performance</TabsTrigger>
          </TabsList>
          
          {/* Statistics Tab */}
          <TabsContent value="stats" className="space-y-4 mt-4">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <Card className="bg-[#1a1d24] border-[#2a2d35] p-4">
                <div className="text-xs text-gray-400 mb-1">Total Rounds</div>
                <div className="text-2xl font-bold text-white">{stats.total_rounds}</div>
              </Card>
              
              <Card className="bg-[#1a1d24] border-[#2a2d35] p-4">
                <div className="text-xs text-gray-400 mb-1">Win Rate</div>
                <div className="text-2xl font-bold text-green-400">{winRate}%</div>
              </Card>
              
              <Card className="bg-[#1a1d24] border-[#2a2d35] p-4">
                <div className="text-xs text-gray-400 mb-1">Avg KDs</div>
                <div className="text-2xl font-bold text-red-400">
                  {stats.avg_kd_per_round.toFixed(1)}
                </div>
              </Card>
              
              <Card className="bg-[#1a1d24] border-[#2a2d35] p-4">
                <div className="text-xs text-gray-400 mb-1">Avg Strikes</div>
                <div className="text-2xl font-bold text-amber-400">
                  {stats.avg_ss_per_round.toFixed(1)}
                </div>
              </Card>
            </div>

            {/* Detailed Stats */}
            <div className="space-y-3 mt-6">
              <div className="text-sm font-semibold text-gray-400 uppercase tracking-wide">
                Per Round Averages
              </div>
              
              <div className="grid md:grid-cols-2 gap-4">
                <Card className="bg-[#1a1d24] border-[#2a2d35] p-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-gray-300">Takedowns</span>
                    <span className="text-white font-bold">{stats.avg_td_per_round.toFixed(1)}</span>
                  </div>
                  <Progress value={stats.avg_td_per_round * 10} className="h-2" />
                </Card>
                
                <Card className="bg-[#1a1d24] border-[#2a2d35] p-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-gray-300">Submission Attempts</span>
                    <span className="text-white font-bold">{stats.avg_sub_attempts.toFixed(1)}</span>
                  </div>
                  <Progress value={stats.avg_sub_attempts * 10} className="h-2" />
                </Card>
                
                <Card className="bg-[#1a1d24] border-[#2a2d35] p-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-gray-300">Control Time (seconds)</span>
                    <span className="text-white font-bold">{stats.avg_control_time.toFixed(0)}s</span>
                  </div>
                  <Progress value={(stats.avg_control_time / 300) * 100} className="h-2" />
                </Card>
                
                <Card className="bg-[#1a1d24] border-[#2a2d35] p-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-gray-300">Avg Round Score</span>
                    <span className="text-white font-bold">{stats.avg_round_score.toFixed(0)}</span>
                  </div>
                  <Progress value={(stats.avg_round_score / 1000) * 100} className="h-2" />
                </Card>
              </div>
            </div>
          </TabsContent>
          
          {/* Tendencies Tab */}
          <TabsContent value="tendencies" className="space-y-4 mt-4">
            {stats.tendencies && (
              <>
                {/* Fighting Style */}
                <Card className="bg-[#1a1d24] border-[#2a2d35] p-6">
                  <div className="text-sm font-semibold text-gray-400 uppercase tracking-wide mb-4">
                    Fighting Style
                  </div>
                  
                  <div className="flex items-center gap-4 mb-6">
                    <Swords className="w-8 h-8 text-red-400" />
                    <div className="flex-1">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-gray-300">Striker</span>
                        <span className="text-white">{((1 - stats.tendencies.grappling_rate) * 100).toFixed(0)}%</span>
                      </div>
                      <Progress value={(1 - stats.tendencies.grappling_rate) * 100} className="h-3" />
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-4">
                    <Shield className="w-8 h-8 text-blue-400" />
                    <div className="flex-1">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-gray-300">Grappler</span>
                        <span className="text-white">{(stats.tendencies.grappling_rate * 100).toFixed(0)}%</span>
                      </div>
                      <Progress value={stats.tendencies.grappling_rate * 100} className="h-3" />
                    </div>
                  </div>
                </Card>

                {/* Striking Breakdown */}
                <Card className="bg-[#1a1d24] border-[#2a2d35] p-6">
                  <div className="text-sm font-semibold text-gray-400 uppercase tracking-wide mb-4">
                    Striking Distribution
                  </div>
                  
                  <div className="space-y-3">
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-gray-300">Head Strikes</span>
                        <span className="text-red-400 font-bold">
                          {(stats.tendencies.striking_style.head * 100).toFixed(0)}%
                        </span>
                      </div>
                      <Progress value={stats.tendencies.striking_style.head * 100} className="h-2 bg-red-950" />
                    </div>
                    
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-gray-300">Body Strikes</span>
                        <span className="text-amber-400 font-bold">
                          {(stats.tendencies.striking_style.body * 100).toFixed(0)}%
                        </span>
                      </div>
                      <Progress value={stats.tendencies.striking_style.body * 100} className="h-2 bg-amber-950" />
                    </div>
                    
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-gray-300">Leg Strikes</span>
                        <span className="text-blue-400 font-bold">
                          {(stats.tendencies.striking_style.leg * 100).toFixed(0)}%
                        </span>
                      </div>
                      <Progress value={stats.tendencies.striking_style.leg * 100} className="h-2 bg-blue-950" />
                    </div>
                  </div>
                </Card>

                {/* Other Tendencies */}
                <div className="grid md:grid-cols-2 gap-4">
                  <Card className="bg-[#1a1d24] border-[#2a2d35] p-4">
                    <div className="text-xs text-gray-400 mb-1">Finish Threat Rate</div>
                    <div className="text-2xl font-bold text-red-400">
                      {(stats.tendencies.finish_threat_rate * 100).toFixed(0)}%
                    </div>
                    <div className="text-xs text-gray-500 mt-1">Rounds with KD or deep SUB</div>
                  </Card>
                  
                  <Card className="bg-[#1a1d24] border-[#2a2d35] p-4">
                    <div className="text-xs text-gray-400 mb-1">Aggression Level</div>
                    <div className="text-2xl font-bold text-amber-400">
                      {stats.tendencies.aggression_level.toFixed(1)}/10
                    </div>
                    <div className="text-xs text-gray-500 mt-1">Activity and forward pressure</div>
                  </Card>
                </div>
              </>
            )}
          </TabsContent>
          
          {/* Performance Tab */}
          <TabsContent value="performance" className="space-y-4 mt-4">
            <div className="grid grid-cols-3 gap-4">
              <Card className="bg-green-900/20 border-green-700/30 p-4 text-center">
                <div className="text-xs text-green-400 mb-1">Rounds Won</div>
                <div className="text-3xl font-bold text-green-400">{stats.rounds_won}</div>
              </Card>
              
              <Card className="bg-red-900/20 border-red-700/30 p-4 text-center">
                <div className="text-xs text-red-400 mb-1">Rounds Lost</div>
                <div className="text-3xl font-bold text-red-400">{stats.rounds_lost}</div>
              </Card>
              
              <Card className="bg-gray-900/20 border-gray-700/30 p-4 text-center">
                <div className="text-xs text-gray-400 mb-1">Draws</div>
                <div className="text-3xl font-bold text-gray-400">{stats.rounds_drawn}</div>
              </Card>
            </div>

            <Card className="bg-[#1a1d24] border-[#2a2d35] p-6">
              <div className="text-sm font-semibold text-gray-400 uppercase tracking-wide mb-4">
                Dominance Rates
              </div>
              
              <div className="space-y-4">
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-gray-300">10-8 Rounds</span>
                    <Badge className="bg-orange-900/30 text-orange-400 border-orange-700/30">
                      {(stats.rate_10_8 * 100).toFixed(1)}%
                    </Badge>
                  </div>
                  <div className="text-xs text-gray-500">
                    Achieved 10-8 dominance in {(stats.rate_10_8 * 100).toFixed(1)}% of rounds
                  </div>
                </div>
                
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-gray-300">10-7 Rounds</span>
                    <Badge className="bg-red-900/30 text-red-400 border-red-700/30">
                      {(stats.rate_10_7 * 100).toFixed(1)}%
                    </Badge>
                  </div>
                  <div className="text-xs text-gray-500">
                    Achieved 10-7 dominance in {(stats.rate_10_7 * 100).toFixed(1)}% of rounds
                  </div>
                </div>
              </div>
            </Card>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}
