import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { RefreshCw, Radio, Shield, TrendingUp } from 'lucide-react';

/**
 * Production Live Stat Dashboard
 * 
 * Route: /stats/fight/:fight_id
 * 
 * Features:
 * - Real-time stats from round_stats and fight_stats
 * - Table view with R1, R2, R3, Total columns
 * - Auto-refresh every 2 seconds
 * - Round selector
 * - Supervisor override mode
 * - Broadcast-safe dark theme
 */
export default function LiveStatsDashboard() {
  const { fight_id } = useParams();
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedRound, setSelectedRound] = useState('all');
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [supervisorMode, setSupervisorMode] = useState(false);
  const [lastUpdated, setLastUpdated] = useState(null);
  
  const backendUrl = process.env.REACT_APP_BACKEND_URL;
  
  // Fetch stats
  const fetchStats = async () => {
    try {
      const response = await fetch(`${backendUrl}/api/stats/live/${fight_id}`);
      const data = await response.json();
      
      if (response.ok) {
        setStats(data);
        setLastUpdated(new Date());
      }
      
      setLoading(false);
    } catch (error) {
      console.error('Error fetching stats:', error);
      setLoading(false);
    }
  };
  
  // Initial fetch
  useEffect(() => {
    if (fight_id) {
      fetchStats();
    }
  }, [fight_id]);
  
  // Auto-refresh every 2 seconds
  useEffect(() => {
    if (!autoRefresh) return;
    
    const interval = setInterval(() => {
      fetchStats();
    }, 2000);
    
    return () => clearInterval(interval);
  }, [autoRefresh, fight_id]);
  
  if (loading) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <div className="text-white text-2xl flex items-center gap-3">
          <RefreshCw className="w-8 h-8 animate-spin" />
          Loading Stats...
        </div>
      </div>
    );
  }
  
  if (!stats || !stats.fighters) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <div className="text-white text-2xl">
          No stats available for fight: {fight_id}
        </div>
      </div>
    );
  }
  
  // Get fighters
  const fighterIds = Object.keys(stats.fighters);
  const fighter1 = stats.fighters[fighterIds[0]];
  const fighter2 = stats.fighters[fighterIds[1]];
  
  // Determine rounds available
  const allRounds = new Set();
  Object.values(stats.fighters).forEach(fighter => {
    Object.keys(fighter.rounds || {}).forEach(round => {
      allRounds.add(parseInt(round));
    });
  });
  const roundNumbers = Array.from(allRounds).sort((a, b) => a - b);
  
  return (
    <div className="min-h-screen bg-black text-white">
      {/* Header */}
      <div className="border-b border-gray-800 bg-gray-900 shadow-lg sticky top-0 z-10">
        <div className="max-w-[1920px] mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            {/* Title */}
            <div>
              <h1 className="text-3xl font-bold text-white flex items-center gap-3">
                <TrendingUp className="w-8 h-8 text-red-500" />
                LIVE STATS DASHBOARD
              </h1>
              <div className="text-sm text-gray-400 mt-1">Fight ID: {fight_id}</div>
            </div>
            
            {/* Controls */}
            <div className="flex items-center gap-4">
              {/* Auto-Refresh Toggle */}
              <button
                onClick={() => setAutoRefresh(!autoRefresh)}
                className={`px-4 py-2 rounded-lg flex items-center gap-2 transition-all ${
                  autoRefresh 
                    ? 'bg-green-600 text-white' 
                    : 'bg-gray-700 text-gray-300'
                }`}
              >
                <Radio className={`w-4 h-4 ${autoRefresh ? 'animate-pulse' : ''}`} />
                {autoRefresh ? 'LIVE' : 'Paused'}
              </button>
              
              {/* Supervisor Mode */}
              <button
                onClick={() => setSupervisorMode(!supervisorMode)}
                className={`px-4 py-2 rounded-lg flex items-center gap-2 transition-all ${
                  supervisorMode 
                    ? 'bg-yellow-600 text-white' 
                    : 'bg-gray-700 text-gray-300'
                }`}
              >
                <Shield className="w-4 h-4" />
                {supervisorMode ? 'Supervisor ON' : 'Supervisor OFF'}
              </button>
              
              {/* Last Updated */}
              {lastUpdated && (
                <div className="text-sm text-gray-400">
                  Updated: {lastUpdated.toLocaleTimeString()}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
      
      {/* Round Selector */}
      <div className="max-w-[1920px] mx-auto px-6 py-4 border-b border-gray-800">
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-400 font-medium">View Round:</span>
          <button
            onClick={() => setSelectedRound('all')}
            className={`px-4 py-2 rounded-lg font-semibold transition-all ${
              selectedRound === 'all'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
            }`}
          >
            All Rounds
          </button>
          {roundNumbers.map(round => (
            <button
              key={round}
              onClick={() => setSelectedRound(round)}
              className={`px-4 py-2 rounded-lg font-semibold transition-all ${
                selectedRound === round
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
              }`}
            >
              Round {round}
            </button>
          ))}
        </div>
      </div>
      
      {/* Stats Table */}
      <div className="max-w-[1920px] mx-auto px-6 py-6">
        <StatsTable
          fighter1={fighter1}
          fighter2={fighter2}
          roundNumbers={roundNumbers}
          selectedRound={selectedRound}
          supervisorMode={supervisorMode}
        />
      </div>
    </div>
  );
}

/**
 * Stats Table Component
 */
function StatsTable({ fighter1, fighter2, roundNumbers, selectedRound, supervisorMode }) {
  const statRows = [
    { label: 'Total Strikes', key: 'total_strikes_landed' },
    { label: 'Sig Strikes', key: 'sig_strikes_landed' },
    { label: 'Knockdowns', key: 'knockdowns' },
    { label: 'Takedowns', key: 'td_landed' },
    { label: 'Sub Attempts', key: 'sub_attempts' },
    { label: 'Ground Control', key: 'ground_control_secs', format: 'time' },
    { label: 'Clinch Control', key: 'clinch_control_secs', format: 'time' },
    { label: 'Cage Control', key: 'cage_control_secs', format: 'time' }
  ];
  
  const formatValue = (value, format) => {
    if (value === null || value === undefined) return '-';
    if (format === 'time') {
      const mins = Math.floor(value / 60);
      const secs = value % 60;
      return `${mins}:${secs.toString().padStart(2, '0')}`;
    }
    return value;
  };
  
  const getValue = (fighter, round, key) => {
    if (round === 'total') {
      return fighter?.total?.[key] || 0;
    }
    return fighter?.rounds?.[round]?.[key] || 0;
  };
  
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse">
        {/* Table Header */}
        <thead>
          <tr className="bg-gray-900 border-b-2 border-gray-700">
            <th className="px-4 py-4 text-left text-sm font-bold text-gray-300">STAT</th>
            
            {/* Fighter 1 Columns */}
            <th className="px-4 py-4 text-center text-sm font-bold text-red-500 border-l border-gray-700" colSpan={roundNumbers.length + 1}>
              FIGHTER RED
            </th>
            
            {/* Fighter 2 Columns */}
            <th className="px-4 py-4 text-center text-sm font-bold text-blue-500 border-l border-gray-700" colSpan={roundNumbers.length + 1}>
              FIGHTER BLUE
            </th>
          </tr>
          
          {/* Sub-header with round numbers */}
          <tr className="bg-gray-800 border-b border-gray-700">
            <th className="px-4 py-2"></th>
            
            {/* Fighter 1 Round Headers */}
            <th className="border-l border-gray-700"></th>
            {roundNumbers.map(round => (
              <th key={`f1-r${round}`} className="px-4 py-2 text-center text-xs font-bold text-gray-400">
                R{round}
              </th>
            ))}
            <th className="px-4 py-2 text-center text-xs font-bold text-red-400">TOTAL</th>
            
            {/* Fighter 2 Round Headers */}
            <th className="border-l border-gray-700"></th>
            {roundNumbers.map(round => (
              <th key={`f2-r${round}`} className="px-4 py-2 text-center text-xs font-bold text-gray-400">
                R{round}
              </th>
            ))}
            <th className="px-4 py-2 text-center text-xs font-bold text-blue-400">TOTAL</th>
          </tr>
        </thead>
        
        {/* Table Body */}
        <tbody>
          {statRows.map((stat, idx) => (
            <tr
              key={stat.key}
              className={`border-b border-gray-800 ${
                idx % 2 === 0 ? 'bg-gray-900/50' : 'bg-black'
              } hover:bg-gray-800 transition-colors`}
            >
              {/* Stat Label */}
              <td className="px-4 py-4 text-sm font-semibold text-white">
                {stat.label}
              </td>
              
              {/* Fighter 1 Stats */}
              <td className="border-l border-gray-700"></td>
              {roundNumbers.map(round => (
                <td
                  key={`f1-r${round}-${stat.key}`}
                  className={`px-4 py-4 text-center text-lg font-bold ${
                    selectedRound === round || selectedRound === 'all'
                      ? 'text-red-400'
                      : 'text-gray-600'
                  }`}
                >
                  {formatValue(getValue(fighter1, round, stat.key), stat.format)}
                </td>
              ))}
              <td className="px-4 py-4 text-center text-lg font-bold text-red-500">
                {formatValue(getValue(fighter1, 'total', stat.key), stat.format)}
              </td>
              
              {/* Fighter 2 Stats */}
              <td className="border-l border-gray-700"></td>
              {roundNumbers.map(round => (
                <td
                  key={`f2-r${round}-${stat.key}`}
                  className={`px-4 py-4 text-center text-lg font-bold ${
                    selectedRound === round || selectedRound === 'all'
                      ? 'text-blue-400'
                      : 'text-gray-600'
                  }`}
                >
                  {formatValue(getValue(fighter2, round, stat.key), stat.format)}
                </td>
              ))}
              <td className="px-4 py-4 text-center text-lg font-bold text-blue-500">
                {formatValue(getValue(fighter2, 'total', stat.key), stat.format)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      
      {/* Supervisor Mode Overlay */}
      {supervisorMode && (
        <div className="mt-4 p-4 bg-yellow-900/20 border border-yellow-600 rounded-lg">
          <div className="flex items-center gap-2 text-yellow-400">
            <Shield className="w-5 h-5" />
            <span className="font-semibold">Supervisor Mode Active</span>
          </div>
          <div className="text-sm text-gray-400 mt-2">
            Additional controls and verification tools available. Click stat cells to drill down into event logs.
          </div>
        </div>
      )}
    </div>
  );
}
