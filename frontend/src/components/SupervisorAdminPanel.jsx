import React, { useState, useEffect } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { toast } from 'sonner';
import { RefreshCw, TrendingUp, User, Shield, CheckCircle, XCircle, Clock } from 'lucide-react';

/**
 * Supervisor-Only Admin Panel
 * 
 * Provides supervisor actions for recalculating statistics.
 * All actions are idempotent, audit-logged, and return real-time results.
 */
export default function SupervisorAdminPanel() {
  const [isLoading, setIsLoading] = useState({});
  const [results, setResults] = useState({});
  
  // Round Stats Form
  const [roundForm, setRoundForm] = useState({
    fight_id: '',
    round: 1
  });
  
  // Fight Stats Form
  const [fightForm, setFightForm] = useState({
    fight_id: ''
  });
  
  // Career Stats Form
  const [careerForm, setCareerForm] = useState({
    fighter_id: ''
  });
  
  const backendUrl = process.env.REACT_APP_BACKEND_URL;
  
  /**
   * BUTTON 1: Recalculate Round Stats
   */
  const recalculateRoundStats = async () => {
    const { fight_id, round } = roundForm;
    
    if (!fight_id || !round) {
      toast.error('Please enter fight ID and round number');
      return;
    }
    
    setIsLoading(prev => ({ ...prev, round: true }));
    
    try {
      const response = await fetch(
        `${backendUrl}/api/stats/aggregate/round?fight_id=${encodeURIComponent(fight_id)}&round_num=${round}&trigger=manual`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          }
        }
      );
      
      const data = await response.json();
      
      if (response.ok) {
        // Fetch the actual round stats to display
        const statsResponse = await fetch(
          `${backendUrl}/api/stats/round/${encodeURIComponent(fight_id)}/${round}/fighter_1`
        );
        
        let roundStats = null;
        if (statsResponse.ok) {
          roundStats = await statsResponse.json();
        }
        
        setResults(prev => ({
          ...prev,
          round: {
            success: true,
            job_id: data.job_id,
            status: data.status,
            rows_updated: data.rows_updated,
            stats: roundStats,
            timestamp: new Date().toISOString()
          }
        }));
        
        toast.success(`Round ${round} stats recalculated: ${data.rows_updated} fighters updated`);
      } else {
        throw new Error(data.detail || 'Failed to recalculate round stats');
      }
      
    } catch (error) {
      console.error('Error recalculating round stats:', error);
      
      setResults(prev => ({
        ...prev,
        round: {
          success: false,
          error: error.message,
          timestamp: new Date().toISOString()
        }
      }));
      
      toast.error(`Failed: ${error.message}`);
      
    } finally {
      setIsLoading(prev => ({ ...prev, round: false }));
    }
  };
  
  /**
   * BUTTON 2: Recalculate Fight Stats
   */
  const recalculateFightStats = async () => {
    const { fight_id } = fightForm;
    
    if (!fight_id) {
      toast.error('Please enter fight ID');
      return;
    }
    
    setIsLoading(prev => ({ ...prev, fight: true }));
    
    try {
      const response = await fetch(
        `${backendUrl}/api/stats/aggregate/fight?fight_id=${encodeURIComponent(fight_id)}&trigger=manual`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          }
        }
      );
      
      const data = await response.json();
      
      if (response.ok) {
        // Fetch all fight stats to display
        const statsResponse = await fetch(
          `${backendUrl}/api/stats/fight/${encodeURIComponent(fight_id)}/all`
        );
        
        let fightStats = null;
        if (statsResponse.ok) {
          fightStats = await statsResponse.json();
        }
        
        setResults(prev => ({
          ...prev,
          fight: {
            success: true,
            job_id: data.job_id,
            status: data.status,
            rows_updated: data.rows_updated,
            stats: fightStats,
            timestamp: new Date().toISOString()
          }
        }));
        
        toast.success(`Fight stats recalculated: ${data.rows_updated} fighters updated`);
      } else {
        throw new Error(data.detail || 'Failed to recalculate fight stats');
      }
      
    } catch (error) {
      console.error('Error recalculating fight stats:', error);
      
      setResults(prev => ({
        ...prev,
        fight: {
          success: false,
          error: error.message,
          timestamp: new Date().toISOString()
        }
      }));
      
      toast.error(`Failed: ${error.message}`);
      
    } finally {
      setIsLoading(prev => ({ ...prev, fight: false }));
    }
  };
  
  /**
   * BUTTON 3: Recalculate Career Stats
   */
  const recalculateCareerStats = async () => {
    const { fighter_id } = careerForm;
    
    setIsLoading(prev => ({ ...prev, career: true }));
    
    try {
      const url = fighter_id
        ? `${backendUrl}/api/stats/aggregate/career?fighter_id=${encodeURIComponent(fighter_id)}&trigger=manual`
        : `${backendUrl}/api/stats/aggregate/career?trigger=manual`;
      
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        }
      });
      
      const data = await response.json();
      
      if (response.ok) {
        // Fetch career stats if specific fighter
        let careerStats = null;
        if (fighter_id) {
          const statsResponse = await fetch(
            `${backendUrl}/api/stats/career/${encodeURIComponent(fighter_id)}`
          );
          
          if (statsResponse.ok) {
            careerStats = await statsResponse.json();
          }
        }
        
        setResults(prev => ({
          ...prev,
          career: {
            success: true,
            job_id: data.job_id,
            status: data.status,
            rows_updated: data.rows_updated,
            stats: careerStats,
            timestamp: new Date().toISOString(),
            scope: fighter_id ? `fighter: ${fighter_id}` : 'all fighters'
          }
        }));
        
        const scope = fighter_id ? `for fighter ${fighter_id}` : 'for all fighters';
        toast.success(`Career stats recalculated ${scope}: ${data.rows_updated} updated`);
      } else {
        throw new Error(data.detail || 'Failed to recalculate career stats');
      }
      
    } catch (error) {
      console.error('Error recalculating career stats:', error);
      
      setResults(prev => ({
        ...prev,
        career: {
          success: false,
          error: error.message,
          timestamp: new Date().toISOString()
        }
      }));
      
      toast.error(`Failed: ${error.message}`);
      
    } finally {
      setIsLoading(prev => ({ ...prev, career: false }));
    }
  };
  
  return (
    <div className="max-w-7xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white flex items-center gap-3">
            <Shield className="w-8 h-8 text-yellow-500" />
            Supervisor Admin Panel
          </h1>
          <p className="text-gray-400 mt-1">Statistics Recalculation & Management</p>
        </div>
        <div className="px-4 py-2 bg-yellow-900/30 border border-yellow-600 rounded-lg text-yellow-200 text-sm">
          <Shield className="w-4 h-4 inline mr-2" />
          Supervisor Access Only
        </div>
      </div>
      
      {/* Info Card */}
      <Card className="bg-blue-900/20 border-blue-600 p-4">
        <div className="flex items-start gap-3">
          <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center flex-shrink-0">
            ℹ️
          </div>
          <div>
            <h3 className="text-white font-semibold mb-1">About These Actions</h3>
            <p className="text-gray-300 text-sm">
              All recalculation actions are <strong>idempotent</strong> (safe to run multiple times),
              <strong> audit-logged</strong>, and return real-time statistics. Use these to:
            </p>
            <ul className="text-gray-300 text-sm mt-2 space-y-1 ml-4">
              <li>• Fix incorrect statistics after event corrections</li>
              <li>• Update stats after system maintenance</li>
              <li>• Verify stat accuracy for specific fights</li>
            </ul>
          </div>
        </div>
      </Card>
      
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* BUTTON 1: Recalculate Round Stats */}
        <Card className="bg-gray-800 border-gray-700 p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 bg-purple-600 rounded-lg flex items-center justify-center">
              <RefreshCw className="w-5 h-5 text-white" />
            </div>
            <h2 className="text-xl font-bold text-white">Round Stats</h2>
          </div>
          
          <div className="space-y-4">
            <div>
              <Label className="text-gray-300">Fight ID</Label>
              <Input
                value={roundForm.fight_id}
                onChange={(e) => setRoundForm(prev => ({ ...prev, fight_id: e.target.value }))}
                placeholder="e.g., ufc301_main"
                className="bg-gray-700 border-gray-600 text-white"
              />
            </div>
            
            <div>
              <Label className="text-gray-300">Round Number</Label>
              <Input
                type="number"
                min="1"
                max="12"
                value={roundForm.round}
                onChange={(e) => setRoundForm(prev => ({ ...prev, round: parseInt(e.target.value) }))}
                className="bg-gray-700 border-gray-600 text-white"
              />
            </div>
            
            <Button
              onClick={recalculateRoundStats}
              disabled={isLoading.round}
              className="w-full bg-purple-600 hover:bg-purple-700 text-white"
            >
              {isLoading.round ? (
                <>
                  <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                  Recalculating...
                </>
              ) : (
                <>
                  <RefreshCw className="w-4 h-4 mr-2" />
                  Recalculate Round Stats
                </>
              )}
            </Button>
          </div>
          
          {/* Results Display */}
          {results.round && (
            <ResultDisplay result={results.round} type="round" />
          )}
        </Card>
        
        {/* BUTTON 2: Recalculate Fight Stats */}
        <Card className="bg-gray-800 border-gray-700 p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center">
              <TrendingUp className="w-5 h-5 text-white" />
            </div>
            <h2 className="text-xl font-bold text-white">Fight Stats</h2>
          </div>
          
          <div className="space-y-4">
            <div>
              <Label className="text-gray-300">Fight ID</Label>
              <Input
                value={fightForm.fight_id}
                onChange={(e) => setFightForm(prev => ({ ...prev, fight_id: e.target.value }))}
                placeholder="e.g., ufc301_main"
                className="bg-gray-700 border-gray-600 text-white"
              />
            </div>
            
            <div className="text-sm text-gray-400 bg-gray-900/50 rounded p-3">
              <strong>Note:</strong> This will recalculate all rounds for this fight first,
              then aggregate them into fight-level statistics.
            </div>
            
            <Button
              onClick={recalculateFightStats}
              disabled={isLoading.fight}
              className="w-full bg-blue-600 hover:bg-blue-700 text-white"
            >
              {isLoading.fight ? (
                <>
                  <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                  Recalculating...
                </>
              ) : (
                <>
                  <TrendingUp className="w-4 h-4 mr-2" />
                  Recalculate Fight Stats
                </>
              )}
            </Button>
          </div>
          
          {/* Results Display */}
          {results.fight && (
            <ResultDisplay result={results.fight} type="fight" />
          )}
        </Card>
        
        {/* BUTTON 3: Recalculate Career Stats */}
        <Card className="bg-gray-800 border-gray-700 p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 bg-green-600 rounded-lg flex items-center justify-center">
              <User className="w-5 h-5 text-white" />
            </div>
            <h2 className="text-xl font-bold text-white">Career Stats</h2>
          </div>
          
          <div className="space-y-4">
            <div>
              <Label className="text-gray-300">Fighter ID (Optional)</Label>
              <Input
                value={careerForm.fighter_id}
                onChange={(e) => setCareerForm(prev => ({ ...prev, fighter_id: e.target.value }))}
                placeholder="Leave empty for all fighters"
                className="bg-gray-700 border-gray-600 text-white"
              />
            </div>
            
            <div className="text-sm text-gray-400 bg-gray-900/50 rounded p-3">
              <strong>Tip:</strong> Leave fighter ID empty to recalculate career stats
              for <strong>all fighters</strong> (use for nightly updates).
            </div>
            
            <Button
              onClick={recalculateCareerStats}
              disabled={isLoading.career}
              className="w-full bg-green-600 hover:bg-green-700 text-white"
            >
              {isLoading.career ? (
                <>
                  <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                  Recalculating...
                </>
              ) : (
                <>
                  <User className="w-4 h-4 mr-2" />
                  Recalculate Career Stats
                </>
              )}
            </Button>
          </div>
          
          {/* Results Display */}
          {results.career && (
            <ResultDisplay result={results.career} type="career" />
          )}
        </Card>
      </div>
    </div>
  );
}

/**
 * Result Display Component
 */
function ResultDisplay({ result, type }) {
  if (!result) return null;
  
  return (
    <div className="mt-4 pt-4 border-t border-gray-700">
      <div className="flex items-center gap-2 mb-3">
        {result.success ? (
          <CheckCircle className="w-5 h-5 text-green-400" />
        ) : (
          <XCircle className="w-5 h-5 text-red-400" />
        )}
        <span className={`font-semibold ${result.success ? 'text-green-400' : 'text-red-400'}`}>
          {result.success ? 'Success' : 'Failed'}
        </span>
        <div className="flex items-center gap-1 text-xs text-gray-400 ml-auto">
          <Clock className="w-3 h-3" />
          {new Date(result.timestamp).toLocaleTimeString()}
        </div>
      </div>
      
      {result.success ? (
        <div className="space-y-2">
          <div className="text-sm text-gray-300 bg-gray-900/50 rounded p-3">
            <div className="grid grid-cols-2 gap-2">
              <div>
                <span className="text-gray-400">Status:</span>
                <span className="ml-2 font-medium text-white">{result.status}</span>
              </div>
              <div>
                <span className="text-gray-400">Updated:</span>
                <span className="ml-2 font-medium text-white">{result.rows_updated}</span>
              </div>
              {result.scope && (
                <div className="col-span-2">
                  <span className="text-gray-400">Scope:</span>
                  <span className="ml-2 font-medium text-white">{result.scope}</span>
                </div>
              )}
              {result.job_id && (
                <div className="col-span-2">
                  <span className="text-gray-400 text-xs">Job ID:</span>
                  <span className="ml-2 text-xs text-gray-500 font-mono">{result.job_id.slice(0, 20)}...</span>
                </div>
              )}
            </div>
          </div>
          
          {/* Display actual stats if available */}
          {result.stats && type === 'round' && (
            <div className="text-xs bg-blue-900/20 border border-blue-700 rounded p-3">
              <div className="font-semibold text-blue-300 mb-2">Round Stats Preview:</div>
              <div className="grid grid-cols-2 gap-1 text-gray-300">
                <div>Sig Strikes: {result.stats.sig_strikes_landed}</div>
                <div>Knockdowns: {result.stats.knockdowns}</div>
                <div>TD Landed: {result.stats.td_landed}</div>
                <div>Control: {result.stats.total_control_secs}s</div>
              </div>
            </div>
          )}
          
          {result.stats && type === 'fight' && result.stats.fighters && (
            <div className="text-xs bg-blue-900/20 border border-blue-700 rounded p-3">
              <div className="font-semibold text-blue-300 mb-2">
                Fight Stats: {result.stats.fighters.length} Fighter(s)
              </div>
              {result.stats.fighters.map((fighter, idx) => (
                <div key={idx} className="text-gray-300 mb-2">
                  <div className="font-medium">{fighter.fighter_id}</div>
                  <div className="grid grid-cols-2 gap-1 text-xs">
                    <div>Rounds: {fighter.total_rounds}</div>
                    <div>Accuracy: {fighter.sig_strike_accuracy?.toFixed(1)}%</div>
                  </div>
                </div>
              ))}
            </div>
          )}
          
          {result.stats && type === 'career' && (
            <div className="text-xs bg-blue-900/20 border border-blue-700 rounded p-3">
              <div className="font-semibold text-blue-300 mb-2">Career Stats Preview:</div>
              <div className="grid grid-cols-2 gap-1 text-gray-300">
                <div>Total Fights: {result.stats.total_fights}</div>
                <div>Total Rounds: {result.stats.total_rounds}</div>
                <div>Avg SS/min: {result.stats.avg_sig_strikes_per_min?.toFixed(2)}</div>
                <div>Accuracy: {result.stats.avg_sig_strike_accuracy?.toFixed(1)}%</div>
              </div>
            </div>
          )}
        </div>
      ) : (
        <div className="text-sm text-red-400 bg-red-900/20 border border-red-700 rounded p-3">
          <strong>Error:</strong> {result.error}
        </div>
      )}
    </div>
  );
}
