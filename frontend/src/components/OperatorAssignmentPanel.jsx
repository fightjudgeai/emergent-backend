import { useState, useEffect, useCallback } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { 
  Users, 
  Wifi, 
  WifiOff, 
  Swords, 
  Shield, 
  Target,
  Check,
  X,
  RefreshCw,
  Monitor
} from 'lucide-react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

// Available roles - All operator options
const ROLES = [
  { id: 'RED_ALL', label: 'Red All', icon: Target, color: 'red', bg: 'bg-red-500' },
  { id: 'RED_STRIKING', label: 'Red Striking', icon: Swords, color: 'red', bg: 'bg-red-600' },
  { id: 'RED_GRAPPLING', label: 'Red Grappling', icon: Shield, color: 'red', bg: 'bg-red-700' },
  { id: 'BLUE_ALL', label: 'Blue All', icon: Target, color: 'blue', bg: 'bg-blue-500' },
  { id: 'BLUE_STRIKING', label: 'Blue Striking', icon: Swords, color: 'blue', bg: 'bg-blue-600' },
  { id: 'BLUE_GRAPPLING', label: 'Blue Grappling', icon: Shield, color: 'blue', bg: 'bg-blue-700' }
];

/**
 * OperatorAssignmentPanel - Supervisor assigns roles to operators
 * 
 * Shows all registered operator devices and allows drag-drop role assignment.
 */
export default function OperatorAssignmentPanel({ boutId, onClose }) {
  const [operators, setOperators] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedOperator, setSelectedOperator] = useState(null);

  // Fetch operators
  const fetchOperators = useCallback(async () => {
    if (!boutId) return;
    
    try {
      const response = await fetch(`${API}/api/operators/list?bout_id=${boutId}`);
      if (response.ok) {
        const data = await response.json();
        setOperators(data.operators || []);
      }
    } catch (error) {
      console.error('Error fetching operators:', error);
    }
  }, [boutId]);

  // Poll for operators
  useEffect(() => {
    fetchOperators();
    const interval = setInterval(fetchOperators, 2000);
    return () => clearInterval(interval);
  }, [fetchOperators]);

  // Assign role to operator
  const assignRole = async (deviceId, role) => {
    setIsLoading(true);
    try {
      const response = await fetch(`${API}/api/operators/assign`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          bout_id: boutId,
          device_id: deviceId,
          role: role
        })
      });
      
      if (response.ok) {
        toast.success(`Assigned ${role.replace('_', ' ')} to operator`);
        fetchOperators();
      } else {
        toast.error('Failed to assign role');
      }
    } catch (error) {
      toast.error('Error assigning role');
    } finally {
      setIsLoading(false);
      setSelectedOperator(null);
    }
  };

  // Unassign role
  const unassignRole = async (deviceId) => {
    try {
      const response = await fetch(`${API}/api/operators/unassign`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          bout_id: boutId,
          device_id: deviceId
        })
      });
      
      if (response.ok) {
        toast.success('Role removed');
        fetchOperators();
      }
    } catch (error) {
      toast.error('Error removing role');
    }
  };

  // Remove operator
  const removeOperator = async (deviceId) => {
    try {
      const response = await fetch(`${API}/api/operators/remove?bout_id=${boutId}&device_id=${deviceId}`, {
        method: 'DELETE'
      });
      
      if (response.ok) {
        toast.success('Operator removed');
        fetchOperators();
      }
    } catch (error) {
      toast.error('Error removing operator');
    }
  };

  // Get assigned operator for a role
  const getOperatorForRole = (roleId) => {
    return operators.find(op => op.assigned_role === roleId);
  };

  // Get unassigned operators
  const unassignedOperators = operators.filter(op => !op.assigned_role);

  return (
    <Card className="p-6 bg-gray-900 border-gray-700 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Users className="w-6 h-6 text-amber-500" />
          <h2 className="text-xl font-bold text-white">Operator Assignment</h2>
          <Badge className="bg-gray-700">
            {operators.length} registered
          </Badge>
        </div>
        <div className="flex items-center gap-2">
          <Button size="sm" variant="ghost" onClick={fetchOperators}>
            <RefreshCw className="w-4 h-4" />
          </Button>
          {onClose && (
            <Button size="sm" variant="ghost" onClick={onClose}>
              <X className="w-4 h-4" />
            </Button>
          )}
        </div>
      </div>

      {/* Role Slots */}
      <div className="space-y-3">
        <div className="text-sm text-gray-400 uppercase tracking-wider">Assigned Roles</div>
        
        {ROLES.map((role) => {
          const assignedOp = getOperatorForRole(role.id);
          const RoleIcon = role.icon;
          
          return (
            <div
              key={role.id}
              className={`flex items-center justify-between p-4 rounded-lg border-2 ${
                assignedOp 
                  ? `${role.bg}/20 border-${role.color}-500` 
                  : 'bg-gray-800/50 border-gray-700 border-dashed'
              }`}
            >
              <div className="flex items-center gap-3">
                <div className={`w-10 h-10 rounded-lg ${role.bg} flex items-center justify-center`}>
                  <RoleIcon className="w-5 h-5 text-white" />
                </div>
                <div>
                  <div className={`font-bold ${role.color === 'red' ? 'text-red-400' : 'text-blue-400'}`}>
                    {role.label}
                  </div>
                  {assignedOp ? (
                    <div className="flex items-center gap-2 text-sm">
                      <span className="text-white">{assignedOp.device_name}</span>
                      {assignedOp.is_active ? (
                        <Wifi className="w-3 h-3 text-green-400" />
                      ) : (
                        <WifiOff className="w-3 h-3 text-red-400" />
                      )}
                    </div>
                  ) : (
                    <div className="text-gray-500 text-sm">Not assigned</div>
                  )}
                </div>
              </div>
              
              {assignedOp ? (
                <Button 
                  size="sm" 
                  variant="ghost" 
                  onClick={() => unassignRole(assignedOp.device_id)}
                  className="text-gray-400 hover:text-red-400"
                >
                  <X className="w-4 h-4" />
                </Button>
              ) : (
                <Badge className="bg-gray-700 text-gray-400">
                  Waiting...
                </Badge>
              )}
            </div>
          );
        })}
      </div>

      {/* Unassigned Operators */}
      {unassignedOperators.length > 0 && (
        <div className="space-y-3">
          <div className="text-sm text-gray-400 uppercase tracking-wider">
            Waiting for Assignment ({unassignedOperators.length})
          </div>
          
          {unassignedOperators.map((op) => (
            <div
              key={op.device_id}
              className="flex items-center justify-between p-4 rounded-lg bg-amber-500/10 border border-amber-500/30"
            >
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-amber-500/20 flex items-center justify-center">
                  <Monitor className="w-5 h-5 text-amber-400" />
                </div>
                <div>
                  <div className="text-white font-medium">{op.device_name}</div>
                  <div className="flex items-center gap-2 text-xs text-gray-400">
                    <span>{op.device_id.slice(-8)}</span>
                    {op.is_active ? (
                      <Badge className="bg-green-500/20 text-green-400 text-xs">Online</Badge>
                    ) : (
                      <Badge className="bg-red-500/20 text-red-400 text-xs">Offline</Badge>
                    )}
                  </div>
                </div>
              </div>
              
              <div className="flex items-center gap-2">
                {/* Role assignment buttons */}
                {ROLES.map((role) => {
                  const isRoleTaken = getOperatorForRole(role.id);
                  const RoleIcon = role.icon;
                  
                  return (
                    <Button
                      key={role.id}
                      size="sm"
                      disabled={isRoleTaken || isLoading}
                      onClick={() => assignRole(op.device_id, role.id)}
                      className={`${role.bg} hover:opacity-80 disabled:opacity-30`}
                      title={isRoleTaken ? `${role.label} already assigned` : `Assign ${role.label}`}
                    >
                      <RoleIcon className="w-4 h-4" />
                    </Button>
                  );
                })}
                
                {/* Remove button */}
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => removeOperator(op.device_id)}
                  className="text-gray-400 hover:text-red-400"
                >
                  <X className="w-4 h-4" />
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Empty state */}
      {operators.length === 0 && (
        <div className="text-center py-8">
          <Monitor className="w-12 h-12 text-gray-600 mx-auto mb-3" />
          <div className="text-gray-400">No operators registered yet</div>
          <div className="text-gray-500 text-sm mt-1">
            Operators should go to <code className="text-amber-400">/waiting/{boutId}</code>
          </div>
        </div>
      )}

      {/* Instructions */}
      <div className="bg-gray-800/50 rounded-lg p-4 text-sm text-gray-400">
        <div className="font-medium text-white mb-2">How to use:</div>
        <ol className="list-decimal list-inside space-y-1">
          <li>Tell operators to open: <code className="text-amber-400">/waiting/{boutId}</code></li>
          <li>They enter their name and register</li>
          <li>They appear here - click a role button to assign</li>
          <li>Once assigned, they auto-redirect to scoring screen</li>
        </ol>
      </div>
    </Card>
  );
}
