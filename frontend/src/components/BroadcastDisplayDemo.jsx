/**
 * Broadcast Display Demo - Standalone Test Version
 * Full-screen display for showing fight scores (with demo data)
 */

import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { RoundWinner } from './broadcast/RoundWinner.jsx';
import { FinalResult } from './broadcast/FinalResult.jsx';
import '../styles/broadcast.css';

export default function BroadcastDisplay() {
  const { boutId } = useParams();

  // Demo mode: Use static data for testing
  const [boutData] = useState({
    fighter1: 'John "The Hammer" Doe',
    fighter2: 'Jane "Lightning" Smith',
    status: 'in_progress',
    currentRound: 3
  });

  const [rounds] = useState([
    { fighter1_total: 10, fighter2_total: 9, locked: true },
    { fighter1_total: 10, fighter2_total: 9, locked: true },
    { fighter1_total: 10, fighter2_total: 8, locked: true }
  ]);

  const [currentRound, setCurrentRound] = useState(null);
  const [showFinal, setShowFinal] = useState(false);

  // Demo: Show round winner after 2 seconds
  useEffect(() => {
    const timer = setTimeout(() => {
      if (rounds.length > 0) {
        const latestRound = rounds[rounds.length - 1];
        setCurrentRound({
          round: rounds.length,
          unified_red: latestRound.fighter1_total || 0,
          unified_blue: latestRound.fighter2_total || 0
        });

        // Auto-hide after 10 seconds
        setTimeout(() => {
          setCurrentRound(null);
          // Then show final result
          setTimeout(() => {
            setShowFinal(true);
          }, 2000);
        }, 10000);
      }
    }, 2000);

    return () => clearTimeout(timer);
  }, [rounds]);

  const redTotal = rounds.reduce((sum, r) => sum + (r.fighter1_total || 0), 0);
  const blueTotal = rounds.reduce((sum, r) => sum + (r.fighter2_total || 0), 0);
  const winner = redTotal > blueTotal ? 'red' : blueTotal > redTotal ? 'blue' : 'draw';

  return (
    <div className="min-h-screen bg-[#0a0a0a] flex flex-col items-center justify-center p-8">
      {/* Demo Banner */}
      <div className="fixed top-4 left-1/2 transform -translate-x-1/2 z-50 px-6 py-2 rounded-full text-sm font-semibold" style={{
        background: 'linear-gradient(to right, hsl(348 83% 47%), hsl(195 100% 70%))',
        color: '#fff'
      }}>
        🎬 DEMO MODE - Bout ID: {boutId}
      </div>

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
              {boutData.fighter1}
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
              {boutData.fighter2}
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
              background: 'hsl(120 100% 50%)',
              boxShadow: '0 0 10px hsl(120 100% 50%)',
              animation: 'pulse 2s ease-in-out infinite'
            }} />
            <span className="text-sm uppercase tracking-wider" style={{ color: 'hsl(195 100% 70%)' }}>
              DEMO MODE
            </span>
          </div>
        </div>

        {/* Demo Instructions */}
        <div className="mt-8 p-4 rounded-lg border" style={{
          borderColor: 'hsl(195 100% 70% / 0.3)',
          background: 'hsl(0 0% 12% / 0.4)'
        }}>
          <div className="text-center text-sm text-gray-400">
            <p className="mb-2">🎬 This is a demo with animated components</p>
            <p className="text-xs">Watch for: Round Winner → Auto-hide → Final Result</p>
            <p className="text-xs mt-2">Press F11 for full-screen • Refresh to restart demo</p>
          </div>
        </div>
      </div>
    </div>
  );
}
