import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Label } from '@/components/ui/label';
import { toast } from 'sonner';
import { 
  Swords, 
  Target, 
  User, 
  Monitor, 
  Wifi, 
  Check, 
  ChevronRight,
  Zap,
  Shield
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

// Device role configurations with visual styling
const DEVICE_ROLES = {
  RED_STRIKING: {
    id: 'RED_STRIKING',
    label: 'Red Corner - Striking',
    shortLabel: 'Red Striking',
    corner: 'RED',
    aspect: 'STRIKING',
    color: 'red',
    icon: Swords,
    description: 'Track punches, kicks, elbows, knees, knockdowns for RED fighter',
    events: ['Jab', 'Cross', 'Hook', 'Uppercut', 'Elbow', 'Knee', 'Kick', 'KD', 'Rocked/Stunned'],
    gradient: 'from-red-600 to-red-800',
    border: 'border-red-500',
    bg: 'bg-red-500/10'
  },
  RED_GRAPPLING: {
    id: 'RED_GRAPPLING',
    label: 'Red Corner - Grappling',
    shortLabel: 'Red Grappling',
    corner: 'RED',
    aspect: 'GRAPPLING',
    color: 'red',
    icon: Shield,
    description: 'Track takedowns, submissions, sweeps, control for RED fighter',
    events: ['Takedown', 'Submission Attempt', 'Sweep/Reversal', 'Guard Passing', 'Ground Control'],
    gradient: 'from-red-700 to-red-900',
    border: 'border-red-600',
    bg: 'bg-red-600/10'
  },
  BLUE_STRIKING: {
    id: 'BLUE_STRIKING',
    label: 'Blue Corner - Striking',
    shortLabel: 'Blue Striking',
    corner: 'BLUE',
    aspect: 'STRIKING',
    color: 'blue',
    icon: Swords,
    description: 'Track punches, kicks, elbows, knees, knockdowns for BLUE fighter',
    events: ['Jab', 'Cross', 'Hook', 'Uppercut', 'Elbow', 'Knee', 'Kick', 'KD', 'Rocked/Stunned'],
    gradient: 'from-blue-600 to-blue-800',
    border: 'border-blue-500',
    bg: 'bg-blue-500/10'
  },
  BLUE_GRAPPLING: {
    id: 'BLUE_GRAPPLING',
    label: 'Blue Corner - Grappling',
    shortLabel: 'Blue Grappling',
    corner: 'BLUE',
    aspect: 'GRAPPLING',
    color: 'blue',
    icon: Shield,
    description: 'Track takedowns, submissions, sweeps, control for BLUE fighter',
    events: ['Takedown', 'Submission Attempt', 'Sweep/Reversal', 'Guard Passing', 'Ground Control'],
    gradient: 'from-blue-700 to-blue-900',
    border: 'border-blue-600',
    bg: 'bg-blue-600/10'
  }
};

export default function OperatorSetup() {
  const navigate = useNavigate();
  const [selectedRole, setSelectedRole] = useState(localStorage.getItem('device_role') || '');
  const [operatorName, setOperatorName] = useState(localStorage.getItem('sync_device_name') || '');
  const [boutId, setBoutId] = useState('');
  const [activeBouts, setActiveBouts] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [deviceId] = useState(() => {
    let id = localStorage.getItem('sync_device_id');
    if (!id) {
      id = `device-${Date.now()}-${Math.random().toString(36).substr(2, 6)}`;
      localStorage.setItem('sync_device_id', id);
    }
    return id;
  });

  // Fetch active bouts
  useEffect(() => {
    const fetchBouts = async () => {
      try {
        const response = await fetch(`${API}/api/bouts/active`);
        if (response.ok) {
          const data = await response.json();
          setActiveBouts(data.bouts || []);
        }
      } catch (error) {
        console.error('Error fetching bouts:', error);
      }
    };
    fetchBouts();
  }, []);

  const handleRoleSelect = (roleId) => {
    setSelectedRole(roleId);
    localStorage.setItem('device_role', roleId);
    toast.success(`Role set to: ${DEVICE_ROLES[roleId].shortLabel}`);
  };

  const handleSaveName = () => {
    if (operatorName.trim()) {
      localStorage.setItem('sync_device_name', operatorName.trim());
      toast.success('Operator name saved');
    }
  };

  const handleStartScoring = async () => {
    if (!selectedRole) {
      toast.error('Please select a device role');
      return;
    }
    if (!boutId) {
      toast.error('Please select or enter a bout ID');
      return;
    }
    if (!operatorName.trim()) {
      toast.error('Please enter your operator name');
      return;
    }

    setIsLoading(true);
    
    // Save settings
    localStorage.setItem('device_role', selectedRole);
    localStorage.setItem('sync_device_name', operatorName.trim());

    // Register device with backend
    try {
      await fetch(`${API}/api/sync/register-device`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          bout_id: boutId,
          device_id: deviceId,
          account_id: 'default',
          device_name: operatorName.trim(),
          device_role: selectedRole
        })
      });
      console.log('[SETUP] Device registered for unified scoring');
    } catch (error) {
      console.warn('Device registration failed (non-critical):', error);
    }

    setIsLoading(false);
    
    // Navigate to operator panel
    navigate(`/operator/${boutId}`);
  };

  const selectedRoleConfig = selectedRole ? DEVICE_ROLES[selectedRole] : null;

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 p-6">
      <div className="max-w-4xl mx-auto space-y-8">
        
        {/* Header */}
        <div className="text-center space-y-2">
          <div className="flex items-center justify-center gap-3">
            <Monitor className="w-10 h-10 text-amber-500" />
            <h1 className="text-4xl font-bold text-white">Operator Setup</h1>
          </div>
          <p className="text-gray-400 text-lg">
            Configure your device role for multi-operator scoring
          </p>
          <div className="flex items-center justify-center gap-2 text-sm text-gray-500">
            <Wifi className="w-4 h-4 text-green-400" />
            <span>Device ID: {deviceId.slice(-8)}</span>
          </div>
        </div>

        {/* Step 1: Operator Name */}
        <Card className="p-6 bg-gray-800/50 border-gray-700">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-8 h-8 rounded-full bg-amber-500 flex items-center justify-center text-black font-bold">1</div>
            <h2 className="text-xl font-semibold text-white">Operator Name</h2>
          </div>
          <div className="flex gap-3">
            <Input
              value={operatorName}
              onChange={(e) => setOperatorName(e.target.value)}
              placeholder="Enter your name (e.g., John - Striking)"
              className="bg-gray-700 border-gray-600 text-white"
              data-testid="operator-name-input"
            />
            <Button onClick={handleSaveName} variant="outline" className="border-gray-600">
              <Check className="w-4 h-4" />
            </Button>
          </div>
        </Card>

        {/* Step 2: Select Role */}
        <Card className="p-6 bg-gray-800/50 border-gray-700">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-8 h-8 rounded-full bg-amber-500 flex items-center justify-center text-black font-bold">2</div>
            <h2 className="text-xl font-semibold text-white">Select Your Scoring Role</h2>
          </div>
          <p className="text-gray-400 text-sm mb-6">
            Each operator tracks a specific aspect. All events combine into ONE unified score.
          </p>
          
          <div className="grid grid-cols-2 gap-4">
            {Object.entries(DEVICE_ROLES).map(([roleId, config]) => {
              const Icon = config.icon;
              const isSelected = selectedRole === roleId;
              
              return (
                <button
                  key={roleId}
                  onClick={() => handleRoleSelect(roleId)}
                  className={`relative p-6 rounded-xl border-2 transition-all duration-200 text-left
                    ${isSelected 
                      ? `${config.border} ${config.bg} ring-2 ring-offset-2 ring-offset-gray-900 ring-${config.color}-500` 
                      : 'border-gray-700 bg-gray-800/30 hover:border-gray-600'
                    }`}
                  data-testid={`role-${roleId}`}
                >
                  {/* Selected indicator */}
                  {isSelected && (
                    <div className={`absolute top-3 right-3 w-6 h-6 rounded-full bg-${config.color}-500 flex items-center justify-center`}>
                      <Check className="w-4 h-4 text-white" />
                    </div>
                  )}
                  
                  {/* Role icon and label */}
                  <div className="flex items-center gap-3 mb-3">
                    <div className={`w-12 h-12 rounded-lg bg-gradient-to-br ${config.gradient} flex items-center justify-center`}>
                      <Icon className="w-6 h-6 text-white" />
                    </div>
                    <div>
                      <div className={`font-bold text-lg ${config.color === 'red' ? 'text-red-400' : 'text-blue-400'}`}>
                        {config.corner}
                      </div>
                      <div className="text-white font-medium">
                        {config.aspect}
                      </div>
                    </div>
                  </div>
                  
                  {/* Description */}
                  <p className="text-gray-400 text-sm mb-3">
                    {config.description}
                  </p>
                  
                  {/* Event types */}
                  <div className="flex flex-wrap gap-1">
                    {config.events.slice(0, 5).map((event) => (
                      <Badge 
                        key={event} 
                        variant="outline" 
                        className={`text-xs ${config.color === 'red' ? 'border-red-700 text-red-400' : 'border-blue-700 text-blue-400'}`}
                      >
                        {event}
                      </Badge>
                    ))}
                    {config.events.length > 5 && (
                      <Badge variant="outline" className="text-xs border-gray-600 text-gray-400">
                        +{config.events.length - 5} more
                      </Badge>
                    )}
                  </div>
                </button>
              );
            })}
          </div>
        </Card>

        {/* Step 3: Select Bout */}
        <Card className="p-6 bg-gray-800/50 border-gray-700">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-8 h-8 rounded-full bg-amber-500 flex items-center justify-center text-black font-bold">3</div>
            <h2 className="text-xl font-semibold text-white">Select or Enter Bout</h2>
          </div>
          
          {/* Active bouts */}
          {activeBouts.length > 0 && (
            <div className="mb-4">
              <Label className="text-gray-400 text-sm mb-2 block">Active Bouts</Label>
              <div className="grid grid-cols-2 gap-2">
                {activeBouts.map((bout) => (
                  <button
                    key={bout.bout_id || bout.boutId}
                    onClick={() => setBoutId(bout.bout_id || bout.boutId)}
                    className={`p-3 rounded-lg border text-left transition-all
                      ${boutId === (bout.bout_id || bout.boutId)
                        ? 'border-amber-500 bg-amber-500/10'
                        : 'border-gray-700 bg-gray-800/30 hover:border-gray-600'
                      }`}
                  >
                    <div className="text-white font-medium text-sm">
                      {bout.fighter1} vs {bout.fighter2}
                    </div>
                    <div className="text-gray-500 text-xs">
                      Round {bout.currentRound || 1} of {bout.totalRounds || 5}
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}
          
          {/* Manual bout ID input */}
          <div>
            <Label className="text-gray-400 text-sm mb-2 block">Or Enter Bout ID</Label>
            <Input
              value={boutId}
              onChange={(e) => setBoutId(e.target.value)}
              placeholder="Enter bout ID"
              className="bg-gray-700 border-gray-600 text-white"
              data-testid="bout-id-input"
            />
          </div>
        </Card>

        {/* Preview Panel */}
        {selectedRoleConfig && (
          <Card className={`p-6 ${selectedRoleConfig.bg} ${selectedRoleConfig.border} border-2`}>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className={`w-16 h-16 rounded-xl bg-gradient-to-br ${selectedRoleConfig.gradient} flex items-center justify-center`}>
                  <selectedRoleConfig.icon className="w-8 h-8 text-white" />
                </div>
                <div>
                  <div className="text-gray-400 text-sm">Your Role</div>
                  <div className={`text-2xl font-bold ${selectedRoleConfig.color === 'red' ? 'text-red-400' : 'text-blue-400'}`}>
                    {selectedRoleConfig.label}
                  </div>
                  <div className="text-gray-400 text-sm mt-1">
                    {operatorName || 'Unnamed Operator'}
                  </div>
                </div>
              </div>
              
              <div className="text-right">
                <div className="text-gray-400 text-sm">Bout</div>
                <div className="text-white font-mono text-lg">
                  {boutId || 'Not selected'}
                </div>
              </div>
            </div>
          </Card>
        )}

        {/* Start Button */}
        <Button
          onClick={handleStartScoring}
          disabled={!selectedRole || !boutId || !operatorName.trim() || isLoading}
          className="w-full h-14 text-lg bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600 text-black font-bold"
          data-testid="start-scoring-btn"
        >
          {isLoading ? (
            <span className="flex items-center gap-2">
              <Zap className="w-5 h-5 animate-pulse" />
              Connecting...
            </span>
          ) : (
            <span className="flex items-center gap-2">
              Start Scoring
              <ChevronRight className="w-5 h-5" />
            </span>
          )}
        </Button>

        {/* Info footer */}
        <div className="text-center text-gray-500 text-sm space-y-1">
          <p>All 4 operators' events combine into ONE unified score</p>
          <p className="flex items-center justify-center gap-1">
            <Wifi className="w-3 h-3 text-green-400" />
            Real-time sync via WebSocket
          </p>
        </div>
      </div>
    </div>
  );
}
