import { useState, useEffect } from 'react';
import { db } from '@/firebase';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Users, TrendingUp, Award, Target } from 'lucide-react';

export default function FighterMemoryLog({ fighterId, fighterName }) {
  const [stats, setStats] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadFighterData();
  }, [fighterId]);

  const loadFighterData = async () => {
    try {
      // Load fighter profile
      const profileDoc = await db.collection('fighterProfiles').doc(fighterId).get();
      if (profileDoc.exists) {
        setStats(profileDoc.data());
      }

      // Load fight history
      const historySnapshot = await db.collection('fightHistory')
        .where('fighterId', '==', fighterId)
        .orderBy('date', 'desc')
        .limit(10)
        .get();
      
      const historyData = historySnapshot.docs.map(doc => doc.data());
      setHistory(historyData);
    } catch (error) {
      console.error('Error loading fighter data:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div className="text-gray-400">Loading fighter stats...</div>;
  if (!stats) return null;

  return (
    <Card className="bg-[#13151a] border-[#2a2d35]">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-white">
          <Users className="w-5 h-5" />
          {fighterName} - Memory Log
        </CardTitle>
      </CardHeader>
      
      <CardContent>
        <Tabs defaultValue="stats" className="w-full">
          <TabsList className="bg-[#1a1d24] border-[#2a2d35]">
            <TabsTrigger value="stats">Statistics</TabsTrigger>
            <TabsTrigger value="tendencies">Tendencies</TabsTrigger>
            <TabsTrigger value="history">History</TabsTrigger>
          </TabsList>
          
          <TabsContent value="stats" className="space-y-4 mt-4">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <Card className="bg-[#1a1d24] border-[#2a2d35] p-4">
                <div className="text-xs text-gray-400 mb-1">Total Fights</div>
                <div className="text-2xl font-bold text-white">{stats.totalFights || 0}</div>
              </Card>
              
              <Card className="bg-[#1a1d24] border-[#2a2d35] p-4">
                <div className="text-xs text-gray-400 mb-1">Win Rate</div>
                <div className="text-2xl font-bold text-green-400">
                  {stats.winRate ? `${stats.winRate}%` : 'N/A'}
                </div>
              </Card>
              
              <Card className="bg-[#1a1d24] border-[#2a2d35] p-4">
                <div className="text-xs text-gray-400 mb-1">Avg KDs</div>
                <div className="text-2xl font-bold text-red-400">
                  {stats.avgKDs?.toFixed(1) || '0.0'}
                </div>
              </Card>
              
              <Card className="bg-[#1a1d24] border-[#2a2d35] p-4">
                <div className="text-xs text-gray-400 mb-1">Avg Strikes</div>
                <div className="text-2xl font-bold text-amber-400">
                  {stats.avgStrikes?.toFixed(0) || '0'}
                </div>
              </Card>
            </div>
          </TabsContent>
          
          <TabsContent value="tendencies" className="space-y-3 mt-4">
            <div className="space-y-2">
              {stats.tendencies?.map((tendency, idx) => (
                <div key={idx} className="flex items-center justify-between bg-[#1a1d24] p-3 rounded-lg border border-[#2a2d35]">
                  <span className="text-gray-300">{tendency.description}</span>
                  <Badge className="bg-amber-500/20 text-amber-500 border-amber-500/30">
                    {tendency.frequency}%
                  </Badge>
                </div>
              )) || (
                <div className="text-gray-500 text-center py-6">
                  No tendencies recorded yet
                </div>
              )}
            </div>
          </TabsContent>
          
          <TabsContent value="history" className="space-y-3 mt-4">
            {history.length > 0 ? (
              history.map((fight, idx) => (
                <Card key={idx} className="bg-[#1a1d24] border-[#2a2d35] p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="text-white font-semibold">{fight.opponent}</div>
                      <div className="text-xs text-gray-400">{fight.event} - {fight.date}</div>
                    </div>
                    <Badge className={
                      fight.result === 'WIN' 
                        ? 'bg-green-900/30 text-green-400 border-green-700/30'
                        : 'bg-red-900/30 text-red-400 border-red-700/30'
                    }>
                      {fight.result}
                    </Badge>
                  </div>
                </Card>
              ))
            ) : (
              <div className="text-gray-500 text-center py-6">
                No fight history available
              </div>
            )}
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}
