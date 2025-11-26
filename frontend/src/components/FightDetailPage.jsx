import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { VictoryBar, VictoryChart, VictoryAxis, VictoryTheme, VictoryGroup, VictoryLegend } from 'victory';
import { ArrowLeft, TrendingUp, Target, Shield } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || import.meta.env.VITE_BACKEND_URL;

const FightDetailPage = () => {
  const { fight_id } = useParams();
  const navigate = useNavigate();
  const [fightData, setFightData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadFightStats();
  }, [fight_id]);

  const loadFightStats = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${BACKEND_URL}/api/fights/${fight_id}/stats`);
      
      if (!response.ok) {
        throw new Error('Fight not found');
      }
      
      const data = await response.json();
      setFightData(data);
      setError(null);
    } catch (err) {
      console.error('Error loading fight stats:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-amber-500 mx-auto mb-4"></div>
          <p className="text-gray-300 text-lg">Loading fight statistics...</p>
        </div>
      </div>
    );
  }

  if (error || !fightData) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 flex items-center justify-center">
        <div className="text-center bg-red-900/20 border border-red-500 rounded-lg p-8">
          <p className="text-red-400 text-xl mb-4">Fight not found</p>
          <p className="text-gray-400 mb-6">{error || 'Unable to load fight statistics'}</p>
          <button
            onClick={() => navigate('/events')}
            className="px-6 py-2 bg-amber-600 hover:bg-amber-700 text-white rounded-lg transition-colors"
          >
            Back to Events
          </button>
        </div>
      </div>
    );
  }

  const fighters = fightData.fighters || [];
  const fighter1 = fighters[0] || {};
  const fighter2 = fighters[1] || {};

  // Prepare chart data for each metric
  const prepareChartData = (metric) => {
    const rounds = Math.max(
      fighter1.rounds?.length || 0,
      fighter2.rounds?.length || 0
    );

    const data = [];
    for (let i = 1; i <= rounds; i++) {
      const f1Round = fighter1.rounds?.find(r => r.round === i) || {};
      const f2Round = fighter2.rounds?.find(r => r.round === i) || {};

      data.push({
        round: i,
        [fighter1.fighter_name || 'Fighter 1']: f1Round[metric] || 0,
        [fighter2.fighter_name || 'Fighter 2']: f2Round[metric] || 0
      });
    }
    return data;
  };

  const sigStrikesData = prepareChartData('significant_strikes');
  const takedownsData = prepareChartData('takedowns');
  const controlTimeData = prepareChartData('control_time_seconds');

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 py-8 px-4">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <button
            onClick={() => navigate('/events')}
            className="flex items-center gap-2 text-gray-400 hover:text-amber-400 transition-colors mb-4"
          >
            <ArrowLeft className="w-5 h-5" />
            Back to Events
          </button>
          <h1 className="text-4xl font-bold text-amber-500 mb-2">Fight Statistics</h1>
          <p className="text-gray-400">{fight_id}</p>
        </div>

        {/* Fighters Header */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          {/* Fighter 1 */}
          <div className="bg-gradient-to-br from-red-900/30 to-red-800/20 border-2 border-red-500 rounded-lg p-6">
            <h2 className="text-3xl font-bold text-white mb-4">
              {fighter1.fighter_name || 'Fighter 1'}
            </h2>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-gray-400 text-sm">Sig. Strikes</p>
                <p className="text-2xl font-bold text-red-400">
                  {fighter1.total_stats?.significant_strikes || 0}
                </p>
              </div>
              <div>
                <p className="text-gray-400 text-sm">Takedowns</p>
                <p className="text-2xl font-bold text-red-400">
                  {fighter1.total_stats?.takedowns || 0} / {fighter1.total_stats?.takedown_attempts || 0}
                </p>
              </div>
              <div>
                <p className="text-gray-400 text-sm">Control Time</p>
                <p className="text-2xl font-bold text-red-400">
                  {formatTime(fighter1.total_stats?.control_time_seconds || 0)}
                </p>
              </div>
              <div>
                <p className="text-gray-400 text-sm">Knockdowns</p>
                <p className="text-2xl font-bold text-red-400">
                  {fighter1.total_stats?.knockdowns || 0}
                </p>
              </div>
            </div>
          </div>

          {/* Fighter 2 */}
          <div className="bg-gradient-to-br from-blue-900/30 to-blue-800/20 border-2 border-blue-500 rounded-lg p-6">
            <h2 className="text-3xl font-bold text-white mb-4">
              {fighter2.fighter_name || 'Fighter 2'}
            </h2>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-gray-400 text-sm">Sig. Strikes</p>
                <p className="text-2xl font-bold text-blue-400">
                  {fighter2.total_stats?.significant_strikes || 0}
                </p>
              </div>
              <div>
                <p className="text-gray-400 text-sm">Takedowns</p>
                <p className="text-2xl font-bold text-blue-400">
                  {fighter2.total_stats?.takedowns || 0} / {fighter2.total_stats?.takedown_attempts || 0}
                </p>
              </div>
              <div>
                <p className="text-gray-400 text-sm">Control Time</p>
                <p className="text-2xl font-bold text-blue-400">
                  {formatTime(fighter2.total_stats?.control_time_seconds || 0)}
                </p>
              </div>
              <div>
                <p className="text-gray-400 text-sm">Knockdowns</p>
                <p className="text-2xl font-bold text-blue-400">
                  {fighter2.total_stats?.knockdowns || 0}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Round-by-Round Charts */}
        <div className="space-y-8">
          {/* Significant Strikes Chart */}
          <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
            <div className="flex items-center gap-3 mb-4">
              <Target className="w-6 h-6 text-amber-500" />
              <h3 className="text-2xl font-bold text-white">Significant Strikes by Round</h3>
            </div>
            <div className="bg-gray-900 rounded-lg p-4">
              <VictoryChart
                theme={VictoryTheme.material}
                domainPadding={20}
                height={300}
                style={{
                  parent: { background: 'transparent' }
                }}
              >
                <VictoryAxis
                  tickFormat={(x) => `R${x}`}
                  style={{
                    axis: { stroke: '#6b7280' },
                    tickLabels: { fill: '#9ca3af', fontSize: 12 }
                  }}
                />
                <VictoryAxis
                  dependentAxis
                  style={{
                    axis: { stroke: '#6b7280' },
                    tickLabels: { fill: '#9ca3af', fontSize: 12 },
                    grid: { stroke: '#374151', strokeDasharray: '5,5' }
                  }}
                />
                <VictoryGroup offset={20} colorScale={['#ef4444', '#3b82f6']}>
                  <VictoryBar
                    data={sigStrikesData}
                    x="round"
                    y={fighter1.fighter_name || 'Fighter 1'}
                  />
                  <VictoryBar
                    data={sigStrikesData}
                    x="round"
                    y={fighter2.fighter_name || 'Fighter 2'}
                  />
                </VictoryGroup>
                <VictoryLegend
                  x={50}
                  y={10}
                  orientation="horizontal"
                  gutter={20}
                  style={{
                    labels: { fill: '#e5e7eb', fontSize: 12 }
                  }}
                  data={[
                    { name: fighter1.fighter_name || 'Fighter 1', symbol: { fill: '#ef4444' } },
                    { name: fighter2.fighter_name || 'Fighter 2', symbol: { fill: '#3b82f6' } }
                  ]}
                />
              </VictoryChart>
            </div>
          </div>

          {/* Takedowns Chart */}
          <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
            <div className="flex items-center gap-3 mb-4">
              <Shield className="w-6 h-6 text-amber-500" />
              <h3 className="text-2xl font-bold text-white">Takedowns by Round</h3>
            </div>
            <div className="bg-gray-900 rounded-lg p-4">
              <VictoryChart
                theme={VictoryTheme.material}
                domainPadding={20}
                height={300}
                style={{
                  parent: { background: 'transparent' }
                }}
              >
                <VictoryAxis
                  tickFormat={(x) => `R${x}`}
                  style={{
                    axis: { stroke: '#6b7280' },
                    tickLabels: { fill: '#9ca3af', fontSize: 12 }
                  }}
                />
                <VictoryAxis
                  dependentAxis
                  style={{
                    axis: { stroke: '#6b7280' },
                    tickLabels: { fill: '#9ca3af', fontSize: 12 },
                    grid: { stroke: '#374151', strokeDasharray: '5,5' }
                  }}
                />
                <VictoryGroup offset={20} colorScale={['#ef4444', '#3b82f6']}>
                  <VictoryBar
                    data={takedownsData}
                    x="round"
                    y={fighter1.fighter_name || 'Fighter 1'}
                  />
                  <VictoryBar
                    data={takedownsData}
                    x="round"
                    y={fighter2.fighter_name || 'Fighter 2'}
                  />
                </VictoryGroup>
                <VictoryLegend
                  x={50}
                  y={10}
                  orientation="horizontal"
                  gutter={20}
                  style={{
                    labels: { fill: '#e5e7eb', fontSize: 12 }
                  }}
                  data={[
                    { name: fighter1.fighter_name || 'Fighter 1', symbol: { fill: '#ef4444' } },
                    { name: fighter2.fighter_name || 'Fighter 2', symbol: { fill: '#3b82f6' } }
                  ]}
                />
              </VictoryChart>
            </div>
          </div>

          {/* Control Time Chart */}
          <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
            <div className="flex items-center gap-3 mb-4">
              <TrendingUp className="w-6 h-6 text-amber-500" />
              <h3 className="text-2xl font-bold text-white">Control Time by Round (seconds)</h3>
            </div>
            <div className="bg-gray-900 rounded-lg p-4">
              <VictoryChart
                theme={VictoryTheme.material}
                domainPadding={20}
                height={300}
                style={{
                  parent: { background: 'transparent' }
                }}
              >
                <VictoryAxis
                  tickFormat={(x) => `R${x}`}
                  style={{
                    axis: { stroke: '#6b7280' },
                    tickLabels: { fill: '#9ca3af', fontSize: 12 }
                  }}
                />
                <VictoryAxis
                  dependentAxis
                  style={{
                    axis: { stroke: '#6b7280' },
                    tickLabels: { fill: '#9ca3af', fontSize: 12 },
                    grid: { stroke: '#374151', strokeDasharray: '5,5' }
                  }}
                />
                <VictoryGroup offset={20} colorScale={['#ef4444', '#3b82f6']}>
                  <VictoryBar
                    data={controlTimeData}
                    x="round"
                    y={fighter1.fighter_name || 'Fighter 1'}
                  />
                  <VictoryBar
                    data={controlTimeData}
                    x="round"
                    y={fighter2.fighter_name || 'Fighter 2'}
                  />
                </VictoryGroup>
                <VictoryLegend
                  x={50}
                  y={10}
                  orientation="horizontal"
                  gutter={20}
                  style={{
                    labels: { fill: '#e5e7eb', fontSize: 12 }
                  }}
                  data={[
                    { name: fighter1.fighter_name || 'Fighter 1', symbol: { fill: '#ef4444' } },
                    { name: fighter2.fighter_name || 'Fighter 2', symbol: { fill: '#3b82f6' } }
                  ]}
                />
              </VictoryChart>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default FightDetailPage;
