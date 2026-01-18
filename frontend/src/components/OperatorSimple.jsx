import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import { 
  Swords, 
  Shield, 
  Target,
  Wifi,
  WifiOff,
  ArrowLeft,
  Zap
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

// Event configurations - SIMPLIFIED STRIKING
const STRIKING_EVENTS = [
  { type: 'Jab', color: 'bg-gray-600', tier: null },
  { type: 'Cross', color: 'bg-orange-600', tier: null },
  { type: 'Hook', color: 'bg-orange-600', tier: null },
  { type: 'Uppercut', color: 'bg-orange-600', tier: null },
  { type: 'Elbow', color: 'bg-orange-700', tier: null },
  { type: 'Knee', color: 'bg-orange-700', tier: null },
  { type: 'Kick', color: 'bg-yellow-600', tier: null },
  { type: 'Rocked/Stunned', color: 'bg-red-700', tier: null },
  { type: 'KD', color: 'bg-red-800', tier: 'Flash', label: 'KD (Flash)' },
  { type: 'KD', color: 'bg-red-900', tier: 'Hard', label: 'KD (Hard)' },
  { type: 'KD', color: 'bg-purple-800', tier: 'Near-Finish', label: 'KD (Near Finish)' },
];

const GRAPPLING_EVENTS = [
  { type: 'Takedown Landed', color: 'bg-teal-600', tier: null, label: 'TD Landed' },
  { type: 'Takedown Defended', color: 'bg-teal-500', tier: null, label: 'TD Defended' },
  { type: 'Back Control', color: 'bg-indigo-600', tier: null, label: 'Back Control' },
  { type: 'Mount Control', color: 'bg-indigo-600', tier: null, label: 'Mount' },
  { type: 'Side Control', color: 'bg-indigo-500', tier: null, label: 'Side Control' },
  { type: 'Submission Attempt', color: 'bg-purple-600', tier: 'Standard', label: 'Sub Attempt' },
  { type: 'Submission Attempt', color: 'bg-purple-800', tier: 'Deep', label: 'Sub (Deep)' },
  { type: 'Submission Attempt', color: 'bg-purple-900', tier: 'Near-Finish', label: 'Sub (Near Finish)' },
  { type: 'Ground Strike', color: 'bg-amber-600', tier: null, label: 'Ground Strike' },
];

/**
 * OperatorSimple - Streamlined event logging for operators
 * 
 * This component ONLY logs events to the server.
 * NO local scoring, NO complex state management.
 * Events are sent to server → Supervisor Dashboard shows combined totals.
 * Auto-syncs round changes from supervisor.
 */
export default function OperatorSimple() {
  const { boutId } = useParams();
  const navigate = useNavigate();
  
  const [deviceRole, setDeviceRole] = useState(localStorage.getItem('device_role') || 'RED_STRIKING');
  const [operatorName, setOperatorName] = useState(localStorage.getItem('sync_device_name') || 'Operator');
  const [currentRound, setCurrentRound] = useState(1);
  const [totalRounds, setTotalRounds] = useState(5);
  const [isConnected, setIsConnected] = useState(true);
  const [eventCount, setEventCount] = useState(0);
  const [lastEvent, setLastEvent] = useState(null);
  const [boutInfo, setBoutInfo] = useState({ fighter1: 'Red Corner', fighter2: 'Blue Corner' });
  const [roundLocked, setRoundLocked] = useState(false);
  const [roundJustChanged, setRoundJustChanged] = useState(false);

  // Determine corner from role
  const corner = deviceRole.startsWith('RED') ? 'RED' : 'BLUE';
  const fighterName = corner === 'RED' ? boutInfo.fighter1 : boutInfo.fighter2;
  
  // Determine which events to show
  const getEventsForRole = () => {
    if (deviceRole === 'RED_STRIKING') return STRIKING_EVENTS;
    if (deviceRole === 'RED_GRAPPLING') return GRAPPLING_EVENTS;
    if (deviceRole === 'BLUE_ALL') return [...STRIKING_EVENTS, ...GRAPPLING_EVENTS];
    return STRIKING_EVENTS;
  };

  // Keyboard shortcuts handler - Red Dragon K585 compatible
  useEffect(() => {
    const handleKeyDown = async (event) => {
      // Don't trigger in input fields
      if (event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA') return;
      if (!boutId) return;

      const key = event.key;
      const shortcutKeys = ['1', '2', '3', '4', '5', '6', '7', '8', 't', 'v', 'b', 'a', 's', 'd', 'q', 'w', 'e', 'r', 'g'];
      
      if (shortcutKeys.includes(key.toLowerCase())) {
        event.preventDefault();
      }

      try {
        // STRIKING - Numbers 1-7 (no more sig/non-sig, just the strike)
        if (key === '1') {
          await logEvent('Jab');
          toast.success('Jab logged (Key 1)');
        } else if (key === '2') {
          await logEvent('Cross');
          toast.success('Cross logged (Key 2)');
        } else if (key === '3') {
          await logEvent('Hook');
          toast.success('Hook logged (Key 3)');
        } else if (key === '4') {
          await logEvent('Uppercut');
          toast.success('Uppercut logged (Key 4)');
        } else if (key === '5') {
          await logEvent('Elbow');
          toast.success('Elbow logged (Key 5)');
        } else if (key === '6') {
          await logEvent('Knee');
          toast.success('Knee logged (Key 6)');
        } else if (key === '7' || key.toLowerCase() === 't') {
          await logEvent('Kick');
          toast.success('Kick logged (Key 7/T)');
        } else if (key === '8' || key.toLowerCase() === 'g') {
          await logEvent('Ground Strike');
          toast.success('Ground Strike logged (Key 8/G)');
        }
        
        // GRAPPLING - V and B
        else if (key.toLowerCase() === 'v') {
          await logEvent('Takedown Landed');
          toast.success('TD Landed logged (Key V)');
        } else if (key.toLowerCase() === 'b') {
          await logEvent('Takedown Defended');
          toast.success('TD Defended logged (Key B)');
        }
        
        // SUBMISSIONS - A, S, D
        else if (key.toLowerCase() === 'a') {
          await logEvent('Submission Attempt', 'Standard');
          toast.success('Sub Attempt logged (Key A)');
        } else if (key.toLowerCase() === 's') {
          await logEvent('Submission Attempt', 'Deep');
          toast.success('Sub (Deep) logged (Key S)');
        } else if (key.toLowerCase() === 'd') {
          await logEvent('Submission Attempt', 'Near-Finish');
          toast.success('Sub (Near-Finish) logged (Key D)');
        }
        
        // DAMAGE - Q, W, E, R
        else if (key.toLowerCase() === 'q') {
          await logEvent('Rocked/Stunned');
          toast.success('Rocked/Stunned logged (Key Q)');
        } else if (key.toLowerCase() === 'w') {
          await logEvent('KD', 'Flash');
          toast.success('KD (Flash) logged (Key W)');
        } else if (key.toLowerCase() === 'e') {
          await logEvent('KD', 'Hard');
          toast.success('KD (Hard) logged (Key E)');
        } else if (key.toLowerCase() === 'r') {
          await logEvent('KD', 'Near-Finish');
          toast.success('KD (Near-Finish) logged (Key R)');
        }
      } catch (error) {
        console.error('Keyboard shortcut error:', error);
        toast.error('Failed to log event');
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [boutId, corner, currentRound, deviceRole, fighterName]);

  // Poll for round changes from supervisor
  useEffect(() => {
    if (!boutId) return;
    
    const syncRound = async () => {
      try {
        const response = await fetch(`${API}/api/bouts/${boutId}/current-round`);
        if (response.ok) {
          const data = await response.json();
          setIsConnected(true);
          setBoutInfo({
            fighter1: data.fighter1 || 'Red Corner',
            fighter2: data.fighter2 || 'Blue Corner'
          });
          setTotalRounds(data.total_rounds || 5);
          
          // Check if round changed
          if (data.current_round !== currentRound) {
            setCurrentRound(data.current_round);
            setEventCount(0); // Reset event count for new round
            setRoundJustChanged(true);
            toast.success(`Round ${data.current_round} started!`, { duration: 3000 });
            
            // Clear the "just changed" indicator after 2 seconds
            setTimeout(() => setRoundJustChanged(false), 2000);
          }
        }
      } catch (error) {
        setIsConnected(false);
      }
    };
    
    // Poll every 1 second for round changes
    const interval = setInterval(syncRound, 1000);
    syncRound(); // Initial sync
    
    return () => clearInterval(interval);
  }, [boutId, currentRound]);

  // Fetch bout info (initial)
  useEffect(() => {
    const fetchBout = async () => {
      try {
        const response = await fetch(`${API}/api/bouts/${boutId}`);
        if (response.ok) {
          const data = await response.json();
          setBoutInfo({
            fighter1: data.fighter1 || 'Red Corner',
            fighter2: data.fighter2 || 'Blue Corner'
          });
          setCurrentRound(data.currentRound || 1);
        }
      } catch (error) {
        console.error('Error fetching bout:', error);
      }
    };
    
    if (boutId) fetchBout();
  }, [boutId]);

  // Log event to server
  const logEvent = async (eventType, tier = null) => {
    try {
      const response = await fetch(`${API}/api/events`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          bout_id: boutId,
          round_number: currentRound,
          corner: corner,
          aspect: deviceRole.includes('GRAPPLING') ? 'GRAPPLING' : 
                  deviceRole === 'BLUE_ALL' ? 'ALL' : 'STRIKING',
          event_type: eventType,
          device_role: deviceRole,
          metadata: tier ? { tier } : {}
        })
      });
      
      if (response.ok) {
        setEventCount(prev => prev + 1);
        setLastEvent({ type: eventType, tier, time: new Date() });
        setIsConnected(true);
        
        const tierLabel = tier ? ` (${tier})` : '';
        toast.success(`${eventType}${tierLabel} → ${fighterName}`, { duration: 1500 });
      } else {
        throw new Error('Server error');
      }
    } catch (error) {
      setIsConnected(false);
      toast.error('Failed to log event - check connection');
    }
  };

  // Get role display info
  const getRoleInfo = () => {
    switch (deviceRole) {
      case 'RED_STRIKING':
        return { icon: Swords, label: 'Red Striking', color: 'red' };
      case 'RED_GRAPPLING':
        return { icon: Shield, label: 'Red Grappling', color: 'red' };
      case 'BLUE_ALL':
        return { icon: Target, label: 'Blue All', color: 'blue' };
      default:
        return { icon: Target, label: deviceRole, color: 'gray' };
    }
  };

  const roleInfo = getRoleInfo();
  const RoleIcon = roleInfo.icon;

  return (
    <div className={`min-h-screen ${corner === 'RED' ? 'bg-red-950' : 'bg-blue-950'}`}>
      {/* Header */}
      <div className={`${corner === 'RED' ? 'bg-red-900' : 'bg-blue-900'} px-4 py-3 flex items-center justify-between`}>
        <div className="flex items-center gap-3">
          <Button size="sm" variant="ghost" onClick={() => navigate('/operator-setup')}>
            <ArrowLeft className="w-4 h-4" />
          </Button>
          <RoleIcon className="w-6 h-6 text-white" />
          <div>
            <div className="font-bold text-white">{roleInfo.label}</div>
            <div className="text-xs text-gray-300">{operatorName}</div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Badge className={isConnected ? 'bg-green-500' : 'bg-red-500'}>
            {isConnected ? <Wifi className="w-3 h-3 mr-1" /> : <WifiOff className="w-3 h-3 mr-1" />}
            {isConnected ? 'LIVE' : 'OFFLINE'}
          </Badge>
          <Badge className="bg-amber-500 text-black">
            R{currentRound}
          </Badge>
        </div>
      </div>

      {/* Fighter Info */}
      <div className={`${corner === 'RED' ? 'bg-red-800' : 'bg-blue-800'} px-4 py-3 text-center`}>
        <div className="text-2xl font-bold text-white">{fighterName}</div>
        <div className="text-sm text-gray-300">
          Logging events for {corner} corner • {eventCount} events logged
        </div>
      </div>

      {/* Event Buttons */}
      <div className="p-4">
        <div className="grid grid-cols-3 gap-2">
          {getEventsForRole().map((event, idx) => (
            <Button
              key={`${event.type}-${event.tier || idx}`}
              onClick={() => logEvent(event.type, event.tier)}
              className={`${event.color} hover:opacity-80 text-white font-medium h-16 text-sm`}
            >
              <div className="text-center">
                <div>{event.label || event.type}</div>
                {event.tier && <div className="text-xs opacity-75">{event.tier}</div>}
              </div>
            </Button>
          ))}
        </div>
      </div>

      {/* Last Event */}
      {lastEvent && (
        <div className="px-4">
          <Card className={`${corner === 'RED' ? 'bg-red-900/50 border-red-700' : 'bg-blue-900/50 border-blue-700'} p-3`}>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Zap className="w-4 h-4 text-amber-400" />
                <span className="text-white">Last: {lastEvent.type}{lastEvent.tier ? ` (${lastEvent.tier})` : ''}</span>
              </div>
              <span className="text-gray-400 text-sm">
                {lastEvent.time.toLocaleTimeString()}
              </span>
            </div>
          </Card>
        </div>
      )}

      {/* Round Indicator - Controlled by Supervisor */}
      <div className="fixed bottom-0 left-0 right-0 p-4 bg-black/90 backdrop-blur border-t border-gray-800">
        <div className={`flex items-center justify-center gap-4 p-3 rounded-lg ${roundJustChanged ? 'bg-green-500/20 border border-green-500 animate-pulse' : 'bg-gray-800'}`}>
          <div className="text-center">
            <div className="text-gray-400 text-xs uppercase tracking-wider">Current Round</div>
            <div className="text-3xl font-bold text-amber-400">
              Round {currentRound}
              <span className="text-gray-500 text-lg ml-2">/ {totalRounds}</span>
            </div>
          </div>
          {roundJustChanged && (
            <Badge className="bg-green-500 animate-bounce">NEW ROUND!</Badge>
          )}
        </div>
        <div className="text-center text-xs text-gray-500 mt-2">
          Round controlled by Supervisor • {eventCount} events logged this round
        </div>
      </div>
    </div>
  );
}
