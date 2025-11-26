import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, TrendingUp, Target, Shield, Award, Clock } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || import.meta.env.VITE_BACKEND_URL;

const FighterProfilePage = () => {
  const { fighter_id } = useParams();
  const navigate = useNavigate();
  const [fighterData, setFighterData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadFighterStats();
  }, [fighter_id]);

  const loadFighterStats = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${BACKEND_URL}/api/fighters/${fighter_id}/stats`);
      
      if (!response.ok) {
        throw new Error('Fighter not found');
      }
      
      const data = await response.json();
      setFighterData(data);
      setError(null);
    } catch (err) {
      console.error('Error loading fighter stats:', err);
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

  const formatDate = (dateString) => {
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      });
    } catch {
      return 'N/A';
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-amber-500 mx-auto mb-4"></div>
          <p className="text-gray-300 text-lg">Loading fighter profile...</p>
        </div>
      </div>
    );
  }

  if (error || !fighterData) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 flex items-center justify-center">
        <div className="text-center bg-red-900/20 border border-red-500 rounded-lg p-8">
          <p className="text-red-400 text-xl mb-4">Fighter not found</p>
          <p className="text-gray-400 mb-6">{error || 'Unable to load fighter profile'}</p>
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

  const { fighter_name, career_metrics, per_minute_rates, last_5_fights, record } = fighterData;

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
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-5xl font-bold text-amber-500 mb-2">{fighter_name}</h1>
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-2">
                  <Award className="w-5 h-5 text-amber-400" />
                  <span className="text-gray-300 text-lg">Record: <span className="font-bold text-white">{record}</span></span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Career Metrics */}
        <div className="mb-8">
          <h2 className="text-2xl font-bold text-white mb-4 flex items-center gap-2">
            <TrendingUp className="w-6 h-6 text-amber-500" />
            Career Metrics
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-gradient-to-br from-amber-900/30 to-amber-800/20 border border-amber-700/50 rounded-lg p-6">
              <p className="text-gray-400 text-sm mb-1">Total Fights</p>
              <p className="text-4xl font-bold text-amber-400">{career_metrics.total_fights}</p>
            </div>

            <div className="bg-gradient-to-br from-blue-900/30 to-blue-800/20 border border-blue-700/50 rounded-lg p-6">
              <p className="text-gray-400 text-sm mb-1">Total Rounds</p>
              <p className="text-4xl font-bold text-blue-400">{career_metrics.total_rounds}</p>
            </div>

            <div className="bg-gradient-to-br from-red-900/30 to-red-800/20 border border-red-700/50 rounded-lg p-6">
              <p className="text-gray-400 text-sm mb-1">Avg Strikes / Fight</p>
              <p className="text-4xl font-bold text-red-400">
                {career_metrics.avg_strikes_per_fight?.toFixed(1) || '0.0'}
              </p>
            </div>

            <div className="bg-gradient-to-br from-green-900/30 to-green-800/20 border border-green-700/50 rounded-lg p-6">
              <p className="text-gray-400 text-sm mb-1">Avg Takedowns / Fight</p>
              <p className="text-4xl font-bold text-green-400">
                {career_metrics.avg_takedowns_per_fight?.toFixed(1) || '0.0'}
              </p>
            </div>

            <div className="bg-gradient-to-br from-purple-900/30 to-purple-800/20 border border-purple-700/50 rounded-lg p-6">
              <p className="text-gray-400 text-sm mb-1">Avg Control Time / Fight</p>
              <p className="text-4xl font-bold text-purple-400">
                {formatTime(Math.round(career_metrics.avg_control_time_per_fight || 0))}
              </p>
            </div>

            <div className="bg-gradient-to-br from-orange-900/30 to-orange-800/20 border border-orange-700/50 rounded-lg p-6">
              <p className="text-gray-400 text-sm mb-1">Total Knockdowns</p>
              <p className="text-4xl font-bold text-orange-400">{career_metrics.total_knockdowns}</p>
            </div>

            <div className="bg-gradient-to-br from-pink-900/30 to-pink-800/20 border border-pink-700/50 rounded-lg p-6">
              <p className="text-gray-400 text-sm mb-1">Total Sub Attempts</p>
              <p className="text-4xl font-bold text-pink-400">{career_metrics.total_submission_attempts}</p>
            </div>
          </div>
        </div>

        {/* Per-Minute Rates */}
        <div className="mb-8">
          <h2 className="text-2xl font-bold text-white mb-4 flex items-center gap-2">
            <Clock className="w-6 h-6 text-amber-500" />
            Per-Minute Rates
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
              <div className="flex items-center gap-3 mb-2">
                <Target className="w-5 h-5 text-red-400" />
                <p className="text-gray-400 text-sm">Strikes / Minute</p>
              </div>
              <p className="text-3xl font-bold text-red-400">
                {per_minute_rates.strikes_per_minute?.toFixed(2) || '0.00'}
              </p>
            </div>

            <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
              <div className="flex items-center gap-3 mb-2">
                <Target className="w-5 h-5 text-amber-400" />
                <p className="text-gray-400 text-sm">Sig. Strikes / Minute</p>
              </div>
              <p className="text-3xl font-bold text-amber-400">
                {per_minute_rates.significant_strikes_per_minute?.toFixed(2) || '0.00'}
              </p>
            </div>

            <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
              <div className="flex items-center gap-3 mb-2">
                <Shield className="w-5 h-5 text-green-400" />
                <p className="text-gray-400 text-sm">Takedowns / Minute</p>
              </div>
              <p className="text-3xl font-bold text-green-400">
                {per_minute_rates.takedowns_per_minute?.toFixed(2) || '0.00'}
              </p>
            </div>
          </div>
        </div>

        {/* Last 5 Fights */}
        <div>
          <h2 className="text-2xl font-bold text-white mb-4 flex items-center gap-2">
            <Award className="w-6 h-6 text-amber-500" />
            Last 5 Fights
          </h2>

          {last_5_fights.length === 0 ? (
            <div className="bg-gray-800 border border-gray-700 rounded-lg p-8 text-center">
              <p className="text-gray-400">No recent fight data available</p>
            </div>
          ) : (
            <div className="space-y-3">
              {last_5_fights.map((fight, index) => (
                <div
                  key={index}
                  className="bg-gray-800 border border-gray-700 rounded-lg p-6 hover:border-amber-500 transition-all cursor-pointer"
                  onClick={() => navigate(`/fights/${fight.fight_id}`)}
                >
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex-1">
                      <h3 className="text-xl font-bold text-white mb-1">
                        vs {fight.opponent || 'Unknown Opponent'}
                      </h3>
                      <div className="flex items-center gap-4 text-sm text-gray-400">
                        <span>{fight.event_name}</span>
                        <span>•</span>
                        <span>{formatDate(fight.date)}</span>
                      </div>
                    </div>
                    <div className="text-right">
                      <span className={`text-2xl font-bold ${
                        fight.result === 'win' ? 'text-green-400' :
                        fight.result === 'loss' ? 'text-red-400' :
                        'text-gray-400'
                      }`}>
                        {fight.result?.toUpperCase() || 'N/A'}
                      </span>
                    </div>
                  </div>

                  <div className="grid grid-cols-3 gap-4 mt-4 pt-4 border-t border-gray-700">
                    <div>
                      <p className="text-gray-500 text-xs mb-1">Sig. Strikes</p>
                      <p className="text-lg font-semibold text-amber-400">{fight.significant_strikes}</p>
                    </div>
                    <div>
                      <p className="text-gray-500 text-xs mb-1">Takedowns</p>
                      <p className="text-lg font-semibold text-blue-400">{fight.takedowns}</p>
                    </div>
                    <div>
                      <p className="text-gray-500 text-xs mb-1">Control Time</p>
                      <p className="text-lg font-semibold text-purple-400">{formatTime(fight.control_time)}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default FighterProfilePage;
