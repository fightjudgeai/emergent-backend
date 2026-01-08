/**
 * Broadcast Display - Arena Big Screen Mode
 * Full-screen display for showing fight scores to the audience
 */

import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { RoundWinner } from './broadcast/RoundWinner.jsx';
import { FinalResult } from './broadcast/FinalResult.jsx';
import '../styles/broadcast.css';

export default function BroadcastDisplay() {
  const { boutId } = useParams();
  const backendUrl = process.env.REACT_APP_BACKEND_URL;

  const [boutData, setBoutData] = useState(null);
  const [currentRound, setCurrentRound] = useState(null);
  const [showFinal, setShowFinal] = useState(false);
  const [rounds, setRounds] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Fetch bout data
  useEffect(() => {
    const fetchBoutData = async () => {
      try {
        const response = await fetch(`${backendUrl}/api/bouts/${boutId}`);
        if (!response.ok) throw new Error('Failed to fetch bout data');
        const data = await response.json();
        setBoutData(data);
        setLoading(false);
      } catch (err) {
        setError(err.message);
        setLoading(false);
      }
    };

    if (boutId) {
      fetchBoutData();
      // Poll every 5 seconds for updates
      const interval = setInterval(fetchBoutData, 5000);
      return () => clearInterval(interval);
    }
  }, [boutId, backendUrl]);

  // Fetch round scores
  useEffect(() => {
    const fetchRounds = async () => {
      try {
        const response = await fetch(`${backendUrl}/api/rounds/${boutId}`);
        if (!response.ok) return;
        const data = await response.json();
        setRounds(data.rounds || []);
      } catch (err) {
        console.error('Failed to fetch rounds:', err);
      }
    };

    if (boutId) {
      fetchRounds();
      const interval = setInterval(fetchRounds, 3000);
      return () => clearInterval(interval);
    }
  }, [boutId, backendUrl]);

  // Listen for round complete events via polling or WebSocket
  useEffect(() => {
    // Check if a new round was just completed
    if (rounds.length > 0) {
      const latestRound = rounds[rounds.length - 1];
      if (latestRound.locked) {
        // Show the latest completed round
        setCurrentRound({
          round: rounds.length,
          unified_red: latestRound.fighter1_total || 0,
          unified_blue: latestRound.fighter2_total || 0
        });
        
        // Auto-hide after 10 seconds
        const timeout = setTimeout(() => {
          setCurrentRound(null);
        }, 10000);
        
        return () => clearTimeout(timeout);
      }
    }
  }, [rounds]);

  // Check if fight is complete
  useEffect(() => {
    if (boutData && boutData.status === 'completed') {
      // Calculate total scores
      const redTotal = rounds.reduce((sum, r) => sum + (r.fighter1_total || 0), 0);
      const blueTotal = rounds.reduce((sum, r) => sum + (r.fighter2_total || 0), 0);
      
      const winner = redTotal > blueTotal ? 'red' : blueTotal > redTotal ? 'blue' : 'draw';
      
      setShowFinal(true);
      // Keep final result visible
    }
  }, [boutData, rounds]);

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0a0a0a] flex items-center justify-center">
        <div className="text-center">
          <div className="text-6xl font-bold mb-4" style={{ color: 'hsl(195 100% 70%)' }}>
            FIGHT JUDGE AI
          </div>
          <div className="text-2xl" style={{ color: 'hsl(0 0% 70%)' }}>
            Loading Broadcast...
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-[#0a0a0a] flex items-center justify-center">
        <div className="text-center">
          <div className="text-4xl font-bold mb-4 text-red-500">Error</div>
          <div className="text-xl text-gray-400">{error}</div>
        </div>
      </div>
    );
  }

  if (!boutData) {
    return (
      <div className="min-h-screen bg-[#0a0a0a] flex items-center justify-center">
        <div className="text-center">
          <div className="text-4xl font-bold text-gray-400">Bout Not Found</div>
        </div>
      </div>
    );
  }

  const redTotal = rounds.reduce((sum, r) => sum + (r.fighter1_total || 0), 0);
  const blueTotal = rounds.reduce((sum, r) => sum + (r.fighter2_total || 0), 0);
  const winner = redTotal > blueTotal ? 'red' : blueTotal > redTotal ? 'blue' : 'draw';

  return (
    <div className="min-h-screen bg-[#0a0a0a] flex flex-col items-center justify-center p-8">
      {/* Main Fight Card */}
      <div className="w-full max-w-6xl">
        {/* Header */}
        <div className="text-center mb-12">
          <div className="text-2xl font-bold mb-2" style={{ color: 'hsl(195 100% 70%)' }}>
            FIGHT JUDGE AI
          </div>
          <div className="text-lg" style={{ color: 'hsl(0 0% 70%)' }}>
            LIVE SCORING BROADCAST
          </div>
        </div>

        {/* Fighter Names */}
        <div className="grid grid-cols-2 gap-8 mb-8">
          <div className="text-center p-6 rounded-lg border-2" style={{ 
            borderColor: 'hsl(348 83% 47%)', 
            background: 'hsl(348 83% 47% / 0.1)',
            boxShadow: '0 0 30px hsl(348 83% 47% / 0.3)'
          }}>
            <div className="text-sm font-semibold tracking-[0.3em] uppercase mb-2" style={{ color: 'hsl(348 83% 47%)' }}>
              RED CORNER
            </div>
            <div className="text-4xl font-bold text-white mb-2">
              {boutData.fighter1 || 'Fighter 1'}
            </div>
            <div className="text-6xl font-bold tabular-nums" style={{ 
              color: 'hsl(348 83% 47%)',
              textShadow: '0 0 20px hsl(348 83% 47% / 0.6)'
            }}>
              {redTotal}
            </div>
          </div>

          <div className="text-center p-6 rounded-lg border-2" style={{ 
            borderColor: 'hsl(195 100% 70%)', 
            background: 'hsl(195 100% 70% / 0.1)',
            boxShadow: '0 0 30px hsl(195 100% 70% / 0.3)'
          }}>
            <div className="text-sm font-semibold tracking-[0.3em] uppercase mb-2" style={{ color: 'hsl(195 100% 70%)' }}>
              BLUE CORNER
            </div>
            <div className="text-4xl font-bold text-white mb-2">
              {boutData.fighter2 || 'Fighter 2'}
            </div>
            <div className="text-6xl font-bold tabular-nums" style={{ 
              color: 'hsl(195 100% 70%)',
              textShadow: '0 0 20px hsl(195 100% 70% / 0.6)'
            }}>
              {blueTotal}
            </div>
          </div>
        </div>

        {/* Current Round Score */}
        {currentRound && (
          <div className="mb-8">
            <RoundWinner
              round={currentRound}
              roundNumber={currentRound.round}
              redName={boutData.fighter1}
              blueName={boutData.fighter2}
              isVisible={true}
            />
          </div>
        )}

        {/* Final Result */}
        {showFinal && (
          <div className="mb-8">
            <FinalResult
              total={{ red: redTotal, blue: blueTotal }}
              winner={winner}
              redName={boutData.fighter1}
              blueName={boutData.fighter2}
              isVisible={true}
            />
          </div>
        )}

        {/* Round History */}
        {rounds.length > 0 && !currentRound && !showFinal && (
          <div className="mt-8 p-6 rounded-lg border" style={{ 
            borderColor: 'hsl(195 100% 70% / 0.3)',
            background: 'hsl(0 0% 12% / 0.4)'
          }}>
            <div className="text-center text-sm font-semibold tracking-[0.3em] uppercase mb-4" style={{ color: 'hsl(195 100% 70%)' }}>
              Round History
            </div>
            <div className="space-y-2">
              {rounds.map((round, idx) => (
                <div key={idx} className="flex items-center justify-between text-lg">
                  <span className="text-gray-400">Round {idx + 1}:</span>
                  <div className="flex gap-8">
                    <span style={{ color: 'hsl(348 83% 47%)' }} className="font-bold">
                      {round.fighter1_total || 0}
                    </span>
                    <span className="text-gray-500">-</span>
                    <span style={{ color: 'hsl(195 100% 70%)' }} className="font-bold">
                      {round.fighter2_total || 0}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Status Indicator */}
        <div className="mt-8 text-center">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full" style={{ 
            background: 'hsl(0 0% 15%)',
            border: '1px solid hsl(195 100% 70% / 0.3)'
          }}>
            <div className="w-3 h-3 rounded-full" style={{ 
              background: boutData.status === 'in_progress' ? 'hsl(120 100% 50%)' : 'hsl(0 0% 50%)',
              boxShadow: boutData.status === 'in_progress' ? '0 0 10px hsl(120 100% 50%)' : 'none',
              animation: boutData.status === 'in_progress' ? 'pulse 2s ease-in-out infinite' : 'none'
            }} />
            <span className="text-sm uppercase tracking-wider" style={{ color: 'hsl(195 100% 70%)' }}>
              {boutData.status === 'in_progress' ? 'LIVE' : boutData.status === 'completed' ? 'COMPLETED' : 'PENDING'}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
