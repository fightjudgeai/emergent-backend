import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { toast } from 'sonner';
import { AlertTriangle, CheckCircle, XCircle, Clock, BarChart3, Eye } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export default function ReviewDashboard() {
  const navigate = useNavigate();
  const [flags, setFlags] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');
  const [selectedFlag, setSelectedFlag] = useState(null);
  const [resolutionNotes, setResolutionNotes] = useState('');

  useEffect(() => {
    loadData();
  }, [filter]);

  const loadData = async () => {
    try {
      setLoading(true);
      
      // Load flags
      const filterParam = filter !== 'all' ? `?status=${filter}` : '';
      const flagsResponse = await fetch(`${BACKEND_URL}/api/review/flags${filterParam}`);
      const flagsData = await flagsResponse.json();
      setFlags(flagsData.flags || []);
      
      // Load stats
      const statsResponse = await fetch(`${BACKEND_URL}/api/review/stats`);
      const statsData = await statsResponse.json();
      setStats(statsData);
    } catch (error) {
      console.error('Error loading review data:', error);
      toast.error('Failed to load review data');
    } finally {
      setLoading(false);
    }
  };

  const resolveFlag = async (flagId, status) => {
    try {
      const judgeProfile = JSON.parse(localStorage.getItem('judgeProfile') || '{}');
      const judgeName = judgeProfile.judgeName || 'Unknown';
      
      const response = await fetch(`${BACKEND_URL}/api/review/resolve/${flagId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          resolved_by: judgeName,
          resolution_notes: resolutionNotes,
          status: status
        })
      });
      
      if (!response.ok) throw new Error('Failed to resolve flag');
      
      toast.success(`Flag ${status === 'resolved' ? 'resolved' : 'dismissed'}`);
      setSelectedFlag(null);
      setResolutionNotes('');
      loadData();
    } catch (error) {
      console.error('Error resolving flag:', error);
      toast.error('Failed to resolve flag');
    }
  };

  const getSeverityColor = (severity) => {
    switch (severity) {
      case 'high': return 'bg-red-900/30 text-red-400 border-red-700/30';
      case 'medium': return 'bg-amber-900/30 text-amber-400 border-amber-700/30';
      case 'low': return 'bg-blue-900/30 text-blue-400 border-blue-700/30';
      default: return 'bg-gray-900/30 text-gray-400 border-gray-700/30';
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'pending': return <Clock className="w-4 h-4" />;
      case 'under_review': return <Eye className="w-4 h-4" />;
      case 'resolved': return <CheckCircle className="w-4 h-4" />;
      case 'dismissed': return <XCircle className="w-4 h-4" />;
      default: return <AlertTriangle className="w-4 h-4" />;
    }
  };

  const formatFlagType = (type) => {
    return type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0a0a0b] p-4 flex items-center justify-center">
        <div className="text-gray-400">Loading review dashboard...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0a0a0b] p-4 md:p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <Card className="bg-[#13151a] border-[#2a2d35] p-8 mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-4xl font-bold text-white mb-2 flex items-center gap-3">
                <AlertTriangle className="w-10 h-10 text-amber-500" />
                Review Dashboard
              </h1>
              <p className="text-gray-400 text-lg">
                Flagged rounds requiring official review
              </p>
            </div>
            <Button
              onClick={() => navigate('/')}
              className="bg-[#1a1d24] hover:bg-[#22252d] text-gray-300"
            >
              Back to Events
            </Button>
          </div>
        </Card>

        {/* Stats Overview */}
        {stats && (
          <div className="grid md:grid-cols-5 gap-4 mb-8">
            <Card className="bg-amber-900/20 border-amber-700/30 p-6">
              <div className="text-center">
                <div className="text-sm text-amber-400 mb-2">Pending</div>
                <div className="text-4xl font-bold text-amber-400">{stats.by_status.pending}</div>
              </div>
            </Card>
            
            <Card className="bg-blue-900/20 border-blue-700/30 p-6">
              <div className="text-center">
                <div className="text-sm text-blue-400 mb-2">Under Review</div>
                <div className="text-4xl font-bold text-blue-400">{stats.by_status.under_review}</div>
              </div>
            </Card>
            
            <Card className="bg-green-900/20 border-green-700/30 p-6">
              <div className="text-center">
                <div className="text-sm text-green-400 mb-2">Resolved</div>
                <div className="text-4xl font-bold text-green-400">{stats.by_status.resolved}</div>
              </div>
            </Card>
            
            <Card className="bg-gray-900/20 border-gray-700/30 p-6">
              <div className="text-center">
                <div className="text-sm text-gray-400 mb-2">Dismissed</div>
                <div className="text-4xl font-bold text-gray-400">{stats.by_status.dismissed}</div>
              </div>
            </Card>
            
            <Card className="bg-[#1a1d24] border-[#2a2d35] p-6">
              <div className="text-center">
                <div className="text-sm text-gray-400 mb-2">Total Flags</div>
                <div className="text-4xl font-bold text-white">{stats.by_status.total}</div>
              </div>
            </Card>
          </div>
        )}

        {/* Filter Tabs */}
        <Tabs value={filter} onValueChange={setFilter} className="mb-6">
          <TabsList className="bg-[#1a1d24] border-[#2a2d35]">
            <TabsTrigger value="all">All Flags</TabsTrigger>
            <TabsTrigger value="pending">Pending</TabsTrigger>
            <TabsTrigger value="under_review">Under Review</TabsTrigger>
            <TabsTrigger value="resolved">Resolved</TabsTrigger>
          </TabsList>
        </Tabs>

        {/* Flags List */}
        <div className="space-y-4">
          {flags.length === 0 ? (
            <Card className="bg-[#13151a] border-[#2a2d35] p-12">
              <div className="text-center text-gray-500">
                <BarChart3 className="w-16 h-16 mx-auto mb-4 opacity-50" />
                <div className="text-xl">No flags found</div>
                <div className="text-sm mt-2">All rounds are clear for this filter</div>
              </div>
            </Card>
          ) : (
            flags.map((flag) => (
              <Card key={flag.id} className="bg-[#13151a] border-[#2a2d35] p-6">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <Badge className={getSeverityColor(flag.severity)}>
                        {flag.severity.toUpperCase()}
                      </Badge>
                      <Badge className="bg-[#1a1d24] text-gray-300 border-[#2a2d35]">
                        {formatFlagType(flag.flag_type)}
                      </Badge>
                      <Badge className="bg-[#1a1d24] text-gray-400 border-[#2a2d35] flex items-center gap-1">
                        {getStatusIcon(flag.status)}
                        {flag.status}
                      </Badge>
                    </div>
                    
                    <div className="text-white text-lg font-semibold mb-2">
                      Bout ID: {flag.bout_id} - Round {flag.round_num}
                    </div>
                    
                    <div className="text-gray-300 mb-3">
                      {flag.description}
                    </div>
                    
                    {flag.context && (
                      <div className="bg-[#1a1d24] border border-[#2a2d35] rounded p-3 mb-3">
                        <div className="text-xs text-gray-400 font-semibold mb-2">Context:</div>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-sm">
                          {Object.entries(flag.context).map(([key, value]) => (
                            <div key={key}>
                              <span className="text-gray-500">{key}:</span>{' '}
                              <span className="text-white">
                                {typeof value === 'object' ? JSON.stringify(value) : value}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                    
                    {flag.resolution_notes && (
                      <div className="bg-[#1a1d24] border border-[#2a2d35] rounded p-3">
                        <div className="text-xs text-gray-400 font-semibold mb-1">
                          Resolution by {flag.resolved_by}:
                        </div>
                        <div className="text-gray-300 text-sm">{flag.resolution_notes}</div>
                      </div>
                    )}
                  </div>
                  
                  <div className="flex gap-2 ml-4">
                    {flag.status === 'pending' && (
                      <Dialog>
                        <DialogTrigger asChild>
                          <Button
                            className="bg-amber-600 hover:bg-amber-700 text-white"
                            onClick={() => setSelectedFlag(flag)}
                          >
                            Review
                          </Button>
                        </DialogTrigger>
                        <DialogContent className="bg-[#13151a] border-[#2a2d35] max-w-2xl">
                          <DialogHeader>
                            <DialogTitle className="text-white">Review Flag</DialogTitle>
                          </DialogHeader>
                          <div className="space-y-4">
                            <div>
                              <Label className="text-gray-300">Resolution Notes</Label>
                              <Textarea
                                value={resolutionNotes}
                                onChange={(e) => setResolutionNotes(e.target.value)}
                                placeholder="Add notes about your review decision..."
                                className="bg-[#1a1d24] border-[#2a2d35] text-white mt-2"
                                rows={4}
                              />
                            </div>
                            <div className="flex gap-3">
                              <Button
                                onClick={() => resolveFlag(flag.id, 'resolved')}
                                className="flex-1 bg-green-600 hover:bg-green-700"
                              >
                                <CheckCircle className="mr-2 h-4 w-4" />
                                Resolve
                              </Button>
                              <Button
                                onClick={() => resolveFlag(flag.id, 'dismissed')}
                                className="flex-1 bg-gray-600 hover:bg-gray-700"
                              >
                                <XCircle className="mr-2 h-4 w-4" />
                                Dismiss
                              </Button>
                            </div>
                          </div>
                        </DialogContent>
                      </Dialog>
                    )}
                  </div>
                </div>
              </Card>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
