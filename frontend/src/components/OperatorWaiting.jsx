import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import { 
  Monitor, 
  Wifi, 
  WifiOff, 
  Clock,
  User,
  Loader2
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

/**
 * OperatorWaiting - Waiting room for operators
 * 
 * Operators register here and wait for supervisor to assign them a role.
 * Once assigned, they're automatically redirected to the scoring screen.
 */
export default function OperatorWaiting() {
  const { boutId: paramBoutId } = useParams();
  const navigate = useNavigate();
  
  const [boutId, setBoutId] = useState(paramBoutId || '');
  const [deviceName, setDeviceName] = useState(localStorage.getItem('device_name') || '');
  const [isRegistered, setIsRegistered] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [assignedRole, setAssignedRole] = useState(null);
  const [waitingMessage, setWaitingMessage] = useState('Waiting for supervisor to assign role...');
  
  // Generate or get device ID
  const [deviceId] = useState(() => {
    let id = localStorage.getItem('operator_device_id');
    if (!id) {
      id = `op-${Date.now()}-${Math.random().toString(36).substr(2, 6)}`;
      localStorage.setItem('operator_device_id', id);
    }
    return id;
  });

  // Register device with server
  const registerDevice = async () => {
    if (!boutId || !deviceName.trim()) {
      toast.error('Please enter bout ID and your name');
      return;
    }
    
    try {
      const response = await fetch(`${API}/api/operators/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          bout_id: boutId,
          device_id: deviceId,
          device_name: deviceName.trim()
        })
      });
      
      if (response.ok) {
        localStorage.setItem('device_name', deviceName.trim());
        localStorage.setItem('current_bout_id', boutId);
        setIsRegistered(true);
        setIsConnected(true);
        toast.success('Registered! Waiting for role assignment...');
      } else {
        throw new Error('Registration failed');
      }
    } catch (error) {
      toast.error('Failed to register. Check connection.');
      setIsConnected(false);
    }
  };

  // Poll for role assignment
  useEffect(() => {
    if (!isRegistered || !boutId) return;
    
    const checkAssignment = async () => {
      try {
        const response = await fetch(`${API}/api/operators/status?bout_id=${boutId}&device_id=${deviceId}`);
        if (response.ok) {
          const data = await response.json();
          setIsConnected(true);
          
          if (data.assigned_role) {
            setAssignedRole(data.assigned_role);
            localStorage.setItem('device_role', data.assigned_role);
            localStorage.setItem('sync_device_name', deviceName);
            
            toast.success(`Role assigned: ${data.assigned_role}`);
            
            // Redirect to operator panel after short delay
            setTimeout(() => {
              navigate(`/op/${boutId}`);
            }, 1500);
          }
        }
      } catch (error) {
        setIsConnected(false);
      }
    };
    
    // Poll every 1 second
    const interval = setInterval(checkAssignment, 1000);
    checkAssignment(); // Initial check
    
    return () => clearInterval(interval);
  }, [isRegistered, boutId, deviceId, deviceName, navigate]);

  // Heartbeat to keep device alive
  useEffect(() => {
    if (!isRegistered || !boutId) return;
    
    const heartbeat = async () => {
      try {
        await fetch(`${API}/api/operators/heartbeat`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            bout_id: boutId,
            device_id: deviceId
          })
        });
      } catch (error) {
        // Silent fail
      }
    };
    
    const interval = setInterval(heartbeat, 5000);
    return () => clearInterval(interval);
  }, [isRegistered, boutId, deviceId]);

  // Registration form
  if (!isRegistered) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 flex items-center justify-center p-6">
        <Card className="p-8 bg-gray-800/50 border-gray-700 max-w-md w-full space-y-6">
          <div className="text-center space-y-2">
            <Monitor className="w-12 h-12 text-amber-500 mx-auto" />
            <h1 className="text-2xl font-bold text-white">Operator Registration</h1>
            <p className="text-gray-400">Register your device for this bout</p>
          </div>
          
          <div className="space-y-4">
            <div>
              <label className="text-sm text-gray-400 block mb-1">Your Name</label>
              <Input
                value={deviceName}
                onChange={(e) => setDeviceName(e.target.value)}
                placeholder="e.g., John, Mike's Laptop, Station 1"
                className="bg-gray-700 border-gray-600 text-white"
              />
            </div>
            
            <div>
              <label className="text-sm text-gray-400 block mb-1">Bout ID</label>
              <Input
                value={boutId}
                onChange={(e) => setBoutId(e.target.value)}
                placeholder="Enter bout ID"
                className="bg-gray-700 border-gray-600 text-white"
              />
            </div>
            
            <Button 
              onClick={registerDevice}
              className="w-full bg-amber-500 hover:bg-amber-600 text-black font-bold"
            >
              Register & Wait for Assignment
            </Button>
          </div>
          
          <div className="text-center text-xs text-gray-500">
            Device ID: {deviceId.slice(-8)}
          </div>
        </Card>
      </div>
    );
  }

  // Waiting screen
  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 flex items-center justify-center p-6">
      <Card className="p-8 bg-gray-800/50 border-gray-700 max-w-md w-full space-y-6">
        <div className="text-center space-y-4">
          {/* Connection status */}
          <div className="flex justify-center">
            <Badge className={isConnected ? 'bg-green-500' : 'bg-red-500'}>
              {isConnected ? (
                <><Wifi className="w-3 h-3 mr-1" /> Connected</>
              ) : (
                <><WifiOff className="w-3 h-3 mr-1" /> Disconnected</>
              )}
            </Badge>
          </div>
          
          {/* Waiting animation */}
          {!assignedRole ? (
            <>
              <Loader2 className="w-16 h-16 text-amber-500 mx-auto animate-spin" />
              <h1 className="text-2xl font-bold text-white">Waiting for Assignment</h1>
              <p className="text-gray-400">{waitingMessage}</p>
            </>
          ) : (
            <>
              <div className={`w-16 h-16 rounded-full mx-auto flex items-center justify-center ${
                assignedRole.includes('RED') ? 'bg-red-500' : 'bg-blue-500'
              }`}>
                <User className="w-8 h-8 text-white" />
              </div>
              <h1 className="text-2xl font-bold text-white">Role Assigned!</h1>
              <Badge className={`text-lg px-4 py-2 ${
                assignedRole.includes('RED') ? 'bg-red-600' : 'bg-blue-600'
              }`}>
                {assignedRole.replace('_', ' ')}
              </Badge>
              <p className="text-gray-400">Redirecting to scoring panel...</p>
            </>
          )}
        </div>
        
        {/* Device info */}
        <div className="bg-gray-900/50 rounded-lg p-4 space-y-2">
          <div className="flex justify-between text-sm">
            <span className="text-gray-400">Name:</span>
            <span className="text-white font-medium">{deviceName}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-gray-400">Bout:</span>
            <span className="text-white font-mono">{boutId}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-gray-400">Device:</span>
            <span className="text-gray-500 font-mono text-xs">{deviceId.slice(-12)}</span>
          </div>
        </div>
        
        {/* Cancel button */}
        {!assignedRole && (
          <Button 
            variant="outline" 
            onClick={() => setIsRegistered(false)}
            className="w-full border-gray-600"
          >
            Cancel & Re-register
          </Button>
        )}
      </Card>
    </div>
  );
}
