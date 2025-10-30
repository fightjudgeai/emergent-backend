import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { toast } from 'sonner';
import { Shield, CheckCircle, AlertTriangle, Download, Lock, Search, User, Clock } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export default function AuditLogViewer() {
  const navigate = useNavigate();
  const [logs, setLogs] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState({ action_type: '', user_id: '', resource_type: '' });
  const [verifying, setVerifying] = useState(null);
  const [isOwner, setIsOwner] = useState(false);
  const [judgeId, setJudgeId] = useState(null);

  useEffect(() => {
    // Check if user is owner
    const judgeProfile = JSON.parse(localStorage.getItem('judgeProfile') || '{}');
    const currentJudgeId = judgeProfile.judgeId;
    setJudgeId(currentJudgeId);
    
    // Owner check - owner-001 is the owner
    if (currentJudgeId === 'owner-001') {
      setIsOwner(true);
      loadData(currentJudgeId);
    } else {
      setIsOwner(false);
      setLoading(false);
    }
  }, [filter]);

  const loadData = async (currentJudgeId) => {
    try {
      setLoading(true);
      
      // Build query params
      const params = new URLSearchParams();
      params.append('judge_id', currentJudgeId);
      if (filter.action_type) params.append('action_type', filter.action_type);
      if (filter.user_id) params.append('user_id', filter.user_id);
      if (filter.resource_type) params.append('resource_type', filter.resource_type);
      
      // Load logs
      const logsResponse = await fetch(`${BACKEND_URL}/api/audit/logs?${params.toString()}`);
      if (logsResponse.status === 403) {
        setIsOwner(false);
        setLoading(false);
        return;
      }
      const logsData = await logsResponse.json();
      setLogs(logsData.logs || []);
      
      // Load stats
      const statsResponse = await fetch(`${BACKEND_URL}/api/audit/stats?judge_id=${currentJudgeId}`);
      const statsData = await statsResponse.json();
      setStats(statsData);
    } catch (error) {
      console.error('Error loading audit logs:', error);
      toast.error('Failed to load audit logs');
    } finally {
      setLoading(false);
    }
  };

  const verifySignature = async (logId) => {
    try {
      setVerifying(logId);
      const response = await fetch(`${BACKEND_URL}/api/audit/verify/${logId}?judge_id=${judgeId}`);
      const result = await response.json();
      
      if (result.valid) {
        toast.success('Signature verified - log is authentic');
      } else {
        toast.error('WARNING: Signature verification failed!');
      }
    } catch (error) {
      console.error('Error verifying signature:', error);
      toast.error('Failed to verify signature');
    } finally {
      setVerifying(null);
    }
  };

  const exportLogs = async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/audit/export`);
      const data = await response.json();
      
      // Create download
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `audit_logs_${new Date().toISOString()}.json`;
      a.click();
      
      toast.success(`Exported ${data.record_count} audit logs`);
    } catch (error) {
      console.error('Error exporting logs:', error);
      toast.error('Failed to export logs');
    }
  };

  const formatTimestamp = (timestamp) => {
    const date = new Date(timestamp);
    return date.toLocaleString();
  };

  const getActionIcon = (actionType) => {
    switch (actionType) {
      case 'score_calculation':
        return <Shield className="w-4 h-4 text-blue-400" />;
      case 'flag_created':
        return <AlertTriangle className="w-4 h-4 text-amber-400" />;
      case 'profile_changed':
        return <User className="w-4 h-4 text-purple-400" />;
      default:
        return <Clock className="w-4 h-4 text-gray-400" />;
    }
  };

  return (
    <div className="min-h-screen bg-[#0a0a0b] p-4 md:p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <Card className="bg-[#13151a] border-[#2a2d35] p-8 mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-4xl font-bold text-white mb-2 flex items-center gap-3">
                <Shield className="w-10 h-10 text-green-500" />
                Security & Audit Logs
              </h1>
              <p className="text-gray-400 text-lg">
                Immutable WORM (Write Once Read Many) audit trail with cryptographic verification
              </p>
            </div>
            <div className="flex gap-3">
              <Button
                onClick={exportLogs}
                className="bg-green-600 hover:bg-green-700 text-white"
              >
                <Download className="mr-2 h-4 w-4" />
                Export Logs
              </Button>
              <Button
                onClick={() => navigate('/')}
                className="bg-[#1a1d24] hover:bg-[#22252d] text-gray-300"
              >
                Back to Events
              </Button>
            </div>
          </div>
        </Card>

        {/* Stats Overview */}
        {stats && (
          <div className="grid md:grid-cols-4 gap-4 mb-8">
            <Card className="bg-[#13151a] border-[#2a2d35] p-6">
              <div className="flex items-center gap-3">
                <Lock className="w-8 h-8 text-green-500" />
                <div>
                  <div className="text-sm text-gray-400">Total Logs</div>
                  <div className="text-2xl font-bold text-white">{stats.total_logs}</div>
                </div>
              </div>
            </Card>
            
            <Card className="bg-[#13151a] border-[#2a2d35] p-6">
              <div className="flex items-center gap-3">
                <CheckCircle className="w-8 h-8 text-blue-500" />
                <div>
                  <div className="text-sm text-gray-400">WORM Compliant</div>
                  <div className="text-2xl font-bold text-green-400">YES</div>
                </div>
              </div>
            </Card>
            
            <Card className="bg-[#13151a] border-[#2a2d35] p-6">
              <div className="flex items-center gap-3">
                <Shield className="w-8 h-8 text-purple-500" />
                <div>
                  <div className="text-sm text-gray-400">Signatures</div>
                  <div className="text-2xl font-bold text-purple-400">SHA-256</div>
                </div>
              </div>
            </Card>
            
            <Card className="bg-[#13151a] border-[#2a2d35] p-6">
              <div className="flex items-center gap-3">
                <User className="w-8 h-8 text-amber-500" />
                <div>
                  <div className="text-sm text-gray-400">Top User</div>
                  <div className="text-sm font-bold text-white truncate">
                    {stats.top_users[0]?.user_name || 'N/A'}
                  </div>
                </div>
              </div>
            </Card>
          </div>
        )}

        {/* Filters */}
        <Card className="bg-[#13151a] border-[#2a2d35] p-6 mb-6">
          <div className="flex items-center gap-4">
            <Search className="w-5 h-5 text-gray-400" />
            <div className="grid md:grid-cols-3 gap-4 flex-1">
              <div>
                <Label className="text-gray-400 text-sm">Action Type</Label>
                <Input
                  value={filter.action_type}
                  onChange={(e) => setFilter({ ...filter, action_type: e.target.value })}
                  placeholder="e.g., score_calculation"
                  className="bg-[#1a1d24] border-[#2a2d35] text-white mt-1"
                />
              </div>
              <div>
                <Label className="text-gray-400 text-sm">User ID</Label>
                <Input
                  value={filter.user_id}
                  onChange={(e) => setFilter({ ...filter, user_id: e.target.value })}
                  placeholder="Filter by user"
                  className="bg-[#1a1d24] border-[#2a2d35] text-white mt-1"
                />
              </div>
              <div>
                <Label className="text-gray-400 text-sm">Resource Type</Label>
                <Input
                  value={filter.resource_type}
                  onChange={(e) => setFilter({ ...filter, resource_type: e.target.value })}
                  placeholder="e.g., round_score"
                  className="bg-[#1a1d24] border-[#2a2d35] text-white mt-1"
                />
              </div>
            </div>
            <Button
              onClick={() => setFilter({ action_type: '', user_id: '', resource_type: '' })}
              className="bg-gray-600 hover:bg-gray-700 mt-6"
            >
              Clear
            </Button>
          </div>
        </Card>

        {/* Audit Logs */}
        <div className="space-y-3">
          {loading ? (
            <Card className="bg-[#13151a] border-[#2a2d35] p-12">
              <div className="text-center text-gray-400">Loading audit logs...</div>
            </Card>
          ) : logs.length === 0 ? (
            <Card className="bg-[#13151a] border-[#2a2d35] p-12">
              <div className="text-center text-gray-500">
                <Lock className="w-16 h-16 mx-auto mb-4 opacity-50" />
                <div className="text-xl">No audit logs found</div>
                <div className="text-sm mt-2">Adjust filters to see results</div>
              </div>
            </Card>
          ) : (
            logs.map((log) => (
              <Card key={log.id} className="bg-[#13151a] border-[#2a2d35] p-4">
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-3 flex-1">
                    {getActionIcon(log.action_type)}
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-white font-semibold">{log.action_type}</span>
                        <Badge className="bg-[#1a1d24] text-gray-300 border-[#2a2d35]">
                          {log.resource_type}
                        </Badge>
                        {log.immutable && (
                          <Badge className="bg-green-900/30 text-green-400 border-green-700/30">
                            <Lock className="w-3 h-3 mr-1" />
                            WORM
                          </Badge>
                        )}
                      </div>
                      
                      <div className="text-sm text-gray-400 mb-2">
                        <span className="text-gray-500">By:</span> {log.user_name} ({log.user_id})
                        {' • '}
                        <span className="text-gray-500">Resource:</span> {log.resource_id}
                        {' • '}
                        <span className="text-gray-500">Time:</span> {formatTimestamp(log.timestamp)}
                      </div>
                      
                      {Object.keys(log.action_data).length > 0 && (
                        <div className="bg-[#1a1d24] rounded p-2 text-xs font-mono text-gray-400">
                          {JSON.stringify(log.action_data, null, 2)}
                        </div>
                      )}
                      
                      <div className="mt-2 text-xs text-gray-500 font-mono">
                        Signature: {log.signature.substring(0, 32)}...
                      </div>
                    </div>
                  </div>
                  
                  <Button
                    onClick={() => verifySignature(log.id)}
                    disabled={verifying === log.id}
                    size="sm"
                    className="bg-green-600 hover:bg-green-700 text-white ml-4"
                  >
                    <Shield className="mr-1 h-3 w-3" />
                    {verifying === log.id ? 'Verifying...' : 'Verify'}
                  </Button>
                </div>
              </Card>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
