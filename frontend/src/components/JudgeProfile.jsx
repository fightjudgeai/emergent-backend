import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import { User, Edit2, Save, X, LogOut, Award, TrendingUp, Calendar, Target } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export default function JudgeProfile() {
  const navigate = useNavigate();
  const [profile, setProfile] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [editForm, setEditForm] = useState({});

  useEffect(() => {
    loadProfile();
  }, []);

  const loadProfile = async () => {
    try {
      const judgeProfile = JSON.parse(localStorage.getItem('judgeProfile'));
      if (!judgeProfile) {
        toast.error('No judge profile found');
        navigate('/login');
        return;
      }

      // Fetch profile from backend
      const profileResponse = await fetch(`${BACKEND_URL}/api/judges/${judgeProfile.judgeId}`);
      const profileData = await profileResponse.json();
      setProfile(profileData);
      setEditForm(profileData);

      // Fetch history
      const historyResponse = await fetch(`${BACKEND_URL}/api/judges/${judgeProfile.judgeId}/history`);
      const historyData = await historyResponse.json();
      setHistory(historyData.history || []);
    } catch (error) {
      console.error('Error loading profile:', error);
      // If profile doesn't exist in backend, use localStorage data
      const judgeProfile = JSON.parse(localStorage.getItem('judgeProfile'));
      setProfile({
        ...judgeProfile,
        totalRoundsJudged: 0,
        averageAccuracy: 0,
        perfectMatches: 0,
        certifications: []
      });
      setEditForm(profile || judgeProfile);
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = () => {
    setEditing(true);
  };

  const handleCancel = () => {
    setEditForm(profile);
    setEditing(false);
  };

  const handleSave = async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/judges/${profile.judgeId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          judgeName: editForm.judgeName,
          organization: editForm.organization,
          email: editForm.email
        })
      });

      if (response.ok) {
        toast.success('Profile updated successfully');
        
        // Update localStorage
        localStorage.setItem('judgeProfile', JSON.stringify({
          judgeId: profile.judgeId,
          judgeName: editForm.judgeName,
          organization: editForm.organization
        }));
        
        await loadProfile();
        setEditing(false);
      } else {
        toast.error('Failed to update profile');
      }
    } catch (error) {
      console.error('Error updating profile:', error);
      toast.error('Error updating profile');
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('judgeProfile');
    toast.success('Logged out successfully');
    navigate('/login');
  };

  const formatTimestamp = (timestamp) => {
    if (!timestamp) return 'N/A';
    const date = new Date(timestamp);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0a0a0b] p-8 flex items-center justify-center">
        <div className="text-white text-xl">Loading profile...</div>
      </div>
    );
  }

  if (!profile) {
    return (
      <div className="min-h-screen bg-[#0a0a0b] p-8 flex items-center justify-center">
        <div className="text-white text-xl">Profile not found</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0a0a0b] p-4 md:p-8">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <Card className="bg-[#13151a] border-[#2a2d35] p-8 mb-8">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-6">
              <div className="w-20 h-20 bg-gradient-to-br from-amber-500 to-orange-600 rounded-full flex items-center justify-center">
                <User className="w-10 h-10 text-white" />
              </div>
              <div>
                <h1 className="text-4xl font-bold text-white mb-2">{profile.judgeName}</h1>
                <div className="flex items-center gap-3">
                  <Badge className="bg-blue-900/30 text-blue-400 border-blue-700/30">
                    {profile.organization}
                  </Badge>
                  <Badge className="bg-gray-900/30 text-gray-400 border-gray-700/30">
                    ID: {profile.judgeId}
                  </Badge>
                </div>
              </div>
            </div>
            <div className="flex gap-3">
              <Button
                onClick={() => navigate('/')}
                className="bg-[#1a1d24] hover:bg-[#22252d] text-gray-300"
              >
                Back to Events
              </Button>
              <Button
                onClick={handleLogout}
                className="bg-red-600 hover:bg-red-700 text-white"
              >
                <LogOut className="mr-2 h-4 w-4" />
                Logout
              </Button>
            </div>
          </div>
        </Card>

        {/* Stats Overview */}
        <div className="grid md:grid-cols-4 gap-4 mb-8">
          <Card className="bg-[#13151a] border-[#2a2d35] p-6">
            <div className="flex items-center gap-3">
              <Target className="w-8 h-8 text-blue-500" />
              <div>
                <div className="text-sm text-gray-400">Total Rounds</div>
                <div className="text-2xl font-bold text-white">{profile.totalRoundsJudged || 0}</div>
              </div>
            </div>
          </Card>
          
          <Card className="bg-[#13151a] border-[#2a2d35] p-6">
            <div className="flex items-center gap-3">
              <TrendingUp className="w-8 h-8 text-green-500" />
              <div>
                <div className="text-sm text-gray-400">Avg Accuracy</div>
                <div className="text-2xl font-bold text-green-400">{profile.averageAccuracy || 0}%</div>
              </div>
            </div>
          </Card>
          
          <Card className="bg-[#13151a] border-[#2a2d35] p-6">
            <div className="flex items-center gap-3">
              <Award className="w-8 h-8 text-amber-500" />
              <div>
                <div className="text-sm text-gray-400">Perfect Matches</div>
                <div className="text-2xl font-bold text-amber-400">{profile.perfectMatches || 0}</div>
              </div>
            </div>
          </Card>
          
          <Card className="bg-[#13151a] border-[#2a2d35] p-6">
            <div className="flex items-center gap-3">
              <Calendar className="w-8 h-8 text-purple-500" />
              <div>
                <div className="text-sm text-gray-400">Member Since</div>
                <div className="text-sm font-bold text-white">
                  {profile.createdAt ? new Date(profile.createdAt).toLocaleDateString() : 'N/A'}
                </div>
              </div>
            </div>
          </Card>
        </div>

        {/* Tabs */}
        <Tabs defaultValue="info" className="space-y-6">
          <TabsList className="bg-[#13151a] border-[#2a2d35]">
            <TabsTrigger value="info">Profile Information</TabsTrigger>
            <TabsTrigger value="history">Scoring History</TabsTrigger>
          </TabsList>

          {/* Profile Information Tab */}
          <TabsContent value="info">
            <Card className="bg-[#13151a] border-[#2a2d35] p-6">
              <CardHeader className="flex flex-row items-center justify-between px-0 pt-0">
                <CardTitle className="text-white">Profile Details</CardTitle>
                {!editing ? (
                  <Button onClick={handleEdit} className="bg-blue-600 hover:bg-blue-700">
                    <Edit2 className="mr-2 h-4 w-4" />
                    Edit Profile
                  </Button>
                ) : (
                  <div className="flex gap-2">
                    <Button onClick={handleSave} className="bg-green-600 hover:bg-green-700">
                      <Save className="mr-2 h-4 w-4" />
                      Save
                    </Button>
                    <Button onClick={handleCancel} className="bg-gray-600 hover:bg-gray-700">
                      <X className="mr-2 h-4 w-4" />
                      Cancel
                    </Button>
                  </div>
                )}
              </CardHeader>
              
              <CardContent className="space-y-6 px-0 pb-0">
                <div className="grid md:grid-cols-2 gap-6">
                  <div className="space-y-2">
                    <Label className="text-gray-400">Judge ID</Label>
                    <Input
                      value={profile.judgeId}
                      disabled
                      className="bg-[#1a1d24] border-[#2a2d35] text-gray-500"
                    />
                  </div>
                  
                  <div className="space-y-2">
                    <Label className="text-gray-400">Full Name</Label>
                    <Input
                      value={editing ? editForm.judgeName : profile.judgeName}
                      onChange={(e) => setEditForm({ ...editForm, judgeName: e.target.value })}
                      disabled={!editing}
                      className="bg-[#1a1d24] border-[#2a2d35] text-white"
                    />
                  </div>
                  
                  <div className="space-y-2">
                    <Label className="text-gray-400">Organization</Label>
                    {editing ? (
                      <Select 
                        value={editForm.organization} 
                        onValueChange={(value) => setEditForm({ ...editForm, organization: value })}
                      >
                        <SelectTrigger className="bg-[#1a1d24] border-[#2a2d35] text-white">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent className="bg-[#1a1d24] border-[#2a2d35]">
                          <SelectItem value="UFC">UFC</SelectItem>
                          <SelectItem value="Bellator">Bellator</SelectItem>
                          <SelectItem value="ONE">ONE Championship</SelectItem>
                          <SelectItem value="PFL">PFL</SelectItem>
                          <SelectItem value="Regional">Regional</SelectItem>
                        </SelectContent>
                      </Select>
                    ) : (
                      <Input
                        value={profile.organization}
                        disabled
                        className="bg-[#1a1d24] border-[#2a2d35] text-white"
                      />
                    )}
                  </div>
                  
                  <div className="space-y-2">
                    <Label className="text-gray-400">Email (Optional)</Label>
                    <Input
                      value={editing ? (editForm.email || '') : (profile.email || '')}
                      onChange={(e) => setEditForm({ ...editForm, email: e.target.value })}
                      disabled={!editing}
                      placeholder="judge@example.com"
                      className="bg-[#1a1d24] border-[#2a2d35] text-white"
                    />
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Scoring History Tab */}
          <TabsContent value="history">
            <Card className="bg-[#13151a] border-[#2a2d35] p-6">
              <CardHeader className="px-0 pt-0">
                <CardTitle className="text-white">Recent Scoring History</CardTitle>
              </CardHeader>
              
              <CardContent className="px-0 pb-0">
                {history.length === 0 ? (
                  <div className="text-center text-gray-500 py-12">
                    <Award className="w-16 h-16 mx-auto mb-4 opacity-50" />
                    <div className="text-xl">No scoring history yet</div>
                    <div className="text-sm mt-2">Start judging to build your history</div>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {history.map((item, index) => (
                      <Card key={index} className="bg-[#1a1d24] border-[#2a2d35] p-4">
                        <div className="flex items-center justify-between">
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-1">
                              <span className="text-white font-semibold">Round #{item.roundId}</span>
                              {item.match && (
                                <Badge className="bg-green-900/30 text-green-400 border-green-700/30">
                                  Perfect Match
                                </Badge>
                              )}
                            </div>
                            <div className="text-sm text-gray-400">
                              Your Score: <span className="text-white font-semibold">{item.myScore}</span>
                              {' • '}
                              Official: <span className="text-white font-semibold">{item.officialScore}</span>
                              {' • '}
                              Accuracy: <span className="text-green-400 font-semibold">{item.accuracy}%</span>
                              {' • '}
                              MAE: <span className="text-blue-400 font-semibold">{item.mae}</span>
                            </div>
                            <div className="text-xs text-gray-500 mt-1">
                              {formatTimestamp(item.timestamp)}
                            </div>
                          </div>
                        </div>
                      </Card>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
