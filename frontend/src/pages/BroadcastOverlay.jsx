/**
 * Broadcast Overlay Page
 * Clean overlay for OBS/streaming - transparent background
 * URL: /overlay/{boutId}
 * 
 * Query params:
 * - stats=1 : Show strike counter
 * - lowerRed=1 : Show red fighter lower third
 * - lowerBlue=1 : Show blue fighter lower third
 * - lowerBoth=1 : Show both fighters lower thirds
 */

import { useState, useEffect, useCallback } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import { StrikeCounter, LowerThird, DualLowerThirds } from '../components/broadcast/StrikeCounterLowerThird';
import '@/styles/fjai-broadcast.css';

const API = process.env.REACT_APP_BACKEND_URL;

export default function BroadcastOverlay() {
  const { boutId } = useParams();
  const [searchParams] = useSearchParams();
  
  // Visibility from URL params (for static overlays) or from supervisor control
  const [showStats, setShowStats] = useState(searchParams.get('stats') === '1');
  const [showLowerRed, setShowLowerRed] = useState(searchParams.get('lowerRed') === '1');
  const [showLowerBlue, setShowLowerBlue] = useState(searchParams.get('lowerBlue') === '1');
  const [showLowerBoth, setShowLowerBoth] = useState(searchParams.get('lowerBoth') === '1');
  
  // Fight data
  const [boutInfo, setBoutInfo] = useState({
    fighter1: 'Red Corner',
    fighter1_record: '',
    fighter1_photo: '',
    fighter1Record: '',
    fighter1Photo: '',
    fighter2: 'Blue Corner',
    fighter2_record: '',
    fighter2_photo: '',
    fighter2Record: '',
    fighter2Photo: '',
    weight_class: ''
  });
  
  // Live stats
  const [stats, setStats] = useState({
    total: { red: 0, blue: 0 },
    significant: { red: 0, blue: 0 },
    knockdowns: { red: 0, blue: 0 },
    takedowns: { red: 0, blue: 0 },
    controlTime: { red: 0, blue: 0 }
  });
  
  // Fetch bout info
  const fetchBoutInfo = useCallback(async () => {
    if (!boutId) return;
    try {
      const response = await fetch(`${API}/api/bouts/${boutId}`);
      if (response.ok) {
        const data = await response.json();
        setBoutInfo(data);
      }
    } catch (error) {
      console.error('Error fetching bout info:', error);
    }
  }, [boutId]);
  
  // Fetch live stats
  const fetchStats = useCallback(async () => {
    if (!boutId) return;
    try {
      const response = await fetch(`${API}/api/overlay/stats/${boutId}`);
      if (response.ok) {
        const data = await response.json();
        setStats(data);
      }
    } catch (error) {
      console.error('Error fetching stats:', error);
    }
  }, [boutId]);
  
  // Poll for broadcast control signals
  const fetchBroadcastControl = useCallback(async () => {
    if (!boutId) return;
    try {
      const response = await fetch(`${API}/api/broadcast/control/${boutId}`);
      if (response.ok) {
        const data = await response.json();
        // Only update if supervisor is controlling (not URL params)
        if (!searchParams.get('stats')) setShowStats(data.showStats || false);
        if (!searchParams.get('lowerRed')) setShowLowerRed(data.showLowerRed || false);
        if (!searchParams.get('lowerBlue')) setShowLowerBlue(data.showLowerBlue || false);
        if (!searchParams.get('lowerBoth')) setShowLowerBoth(data.showLowerBoth || false);
      }
    } catch (error) {
      // Ignore - supervisor control is optional
    }
  }, [boutId, searchParams]);
  
  // Initial fetch
  useEffect(() => {
    fetchBoutInfo();
    fetchStats();
    fetchBroadcastControl();
  }, [fetchBoutInfo, fetchStats, fetchBroadcastControl]);
  
  // Poll for updates
  useEffect(() => {
    const statsInterval = setInterval(fetchStats, 1000);
    const controlInterval = setInterval(fetchBroadcastControl, 500);
    
    return () => {
      clearInterval(statsInterval);
      clearInterval(controlInterval);
    };
  }, [fetchStats, fetchBroadcastControl]);
  
  // Fighter objects for components
  const redFighter = {
    name: boutInfo.fighter1,
    record: boutInfo.fighter1_record,
    photo: boutInfo.fighter1_photo,
    weightClass: boutInfo.weight_class?.replace('M-', '').replace('W-', "Women's ")
  };
  
  const blueFighter = {
    name: boutInfo.fighter2,
    record: boutInfo.fighter2_record,
    photo: boutInfo.fighter2_photo,
    weightClass: boutInfo.weight_class?.replace('M-', '').replace('W-', "Women's ")
  };

  return (
    <div className="min-h-screen bg-transparent" data-testid="broadcast-overlay">
      {/* Strike Counter - Top Right */}
      {showStats && (
        <div className="fixed top-4 right-4 z-50">
          <StrikeCounter
            stats={stats}
            redName={boutInfo.fighter1}
            blueName={boutInfo.fighter2}
            isVisible={true}
          />
        </div>
      )}
      
      {/* Lower Thirds */}
      {showLowerBoth && (
        <DualLowerThirds
          redFighter={redFighter}
          blueFighter={blueFighter}
          isVisible={true}
        />
      )}
      
      {showLowerRed && !showLowerBoth && (
        <LowerThird
          fighter={redFighter}
          corner="red"
          isVisible={true}
        />
      )}
      
      {showLowerBlue && !showLowerBoth && (
        <div className="fixed bottom-20 right-12">
          <LowerThird
            fighter={blueFighter}
            corner="blue"
            isVisible={true}
          />
        </div>
      )}
    </div>
  );
}
