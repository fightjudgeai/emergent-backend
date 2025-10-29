import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Slider } from '@/components/ui/slider';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { toast } from 'sonner';
import { Settings, Plus, Edit, Trash2, Award, Target } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const DEFAULT_WEIGHTS = {
  KD: 0.30,
  ISS: 0.20,
  TSR: 0.15,
  GCQ: 0.10,
  TDQ: 0.08,
  OC: 0.06,
  SUBQ: 0.05,
  AGG: 0.05,
  RP: 0.01
};

export default function TuningProfileManager() {
  const navigate = useNavigate();
  const [profiles, setProfiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [editingProfile, setEditingProfile] = useState(null);
  const [currentUser, setCurrentUser] = useState(null);
  
  // Form state
  const [profileName, setProfileName] = useState('');
  const [promotion, setPromotion] = useState('');
  const [description, setDescription] = useState('');
  const [weights, setWeights] = useState(DEFAULT_WEIGHTS);
  const [threshold109, setThreshold109] = useState(600);
  const [threshold108, setThreshold108] = useState(900);

  useEffect(() => {
    // Get current user
    const judgeProfile = JSON.parse(localStorage.getItem('judgeProfile') || '{}');
    setCurrentUser({
      id: judgeProfile.judgeId,
      name: judgeProfile.judgeName
    });
    
    loadProfiles();
  }, []);

  const loadProfiles = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${BACKEND_URL}/api/tuning-profiles`);
      const data = await response.json();
      setProfiles(data.profiles || []);
    } catch (error) {
      console.error('Error loading profiles:', error);
      toast.error('Failed to load tuning profiles');
    } finally {
      setLoading(false);
    }
  };

  const createProfile = async () => {
    if (!profileName.trim() || !promotion.trim()) {
      toast.error('Please enter profile name and promotion');
      return;
    }

    try {
      const response = await fetch(`${BACKEND_URL}/api/tuning-profiles/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: profileName,
          promotion: promotion,
          description: description,
          weights: weights,
          thresholds: {
            threshold_10_9: threshold109,
            threshold_10_8: threshold108
          },
          created_by: currentUser?.id || 'unknown'
        })
      });

      if (!response.ok) throw new Error('Failed to create profile');

      toast.success('Tuning profile created');
      setShowCreateDialog(false);
      resetForm();
      loadProfiles();
    } catch (error) {
      console.error('Error creating profile:', error);
      toast.error('Failed to create profile');
    }
  };

  const isOwner = (profile) => {
    return profile.created_by === currentUser?.id || profile.is_default;
  };

  const deleteProfile = async (profileId) => {
    if (!confirm('Are you sure you want to delete this profile?')) return;

    try {
      const response = await fetch(`${BACKEND_URL}/api/tuning-profiles/${profileId}`, {
        method: 'DELETE'
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Failed to delete profile');
      }

      toast.success('Profile deleted');
      loadProfiles();
    } catch (error) {
      console.error('Error deleting profile:', error);
      toast.error(error.message || 'Failed to delete profile');
    }
  };

  const resetForm = () => {
    setProfileName('');
    setPromotion('');
    setDescription('');
    setWeights(DEFAULT_WEIGHTS);
    setThreshold109(600);
    setThreshold108(900);
  };

  const updateWeight = (metric, value) => {
    setWeights({ ...weights, [metric]: value / 100 });
  };

  const getWeightPercentage = (metric) => {
    return Math.round(weights[metric] * 100);
  };

  return (
    <div className="min-h-screen bg-[#0a0a0b] p-4 md:p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <Card className="bg-[#13151a] border-[#2a2d35] p-8 mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-4xl font-bold text-white mb-2 flex items-center gap-3">
                <Settings className="w-10 h-10 text-amber-500" />
                Tuning Profile Manager
              </h1>
              <p className="text-gray-400 text-lg">
                Customize scoring parameters for different promotions
              </p>
            </div>
            <div className="flex gap-3">
              <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
                <DialogTrigger asChild>
                  <Button className="bg-gradient-to-r from-amber-600 to-amber-700 hover:from-amber-700 hover:to-amber-800 text-white">
                    <Plus className="mr-2 h-4 w-4" />
                    Create Profile
                  </Button>
                </DialogTrigger>
                <DialogContent className="bg-[#13151a] border-[#2a2d35] max-w-3xl max-h-[90vh] overflow-y-auto">
                  <DialogHeader>
                    <DialogTitle className="text-white text-2xl">Create Tuning Profile</DialogTitle>
                  </DialogHeader>
                  
                  <Tabs defaultValue="basic" className="w-full">
                    <TabsList className="bg-[#1a1d24] border-[#2a2d35]">
                      <TabsTrigger value="basic">Basic Info</TabsTrigger>
                      <TabsTrigger value="weights">Metric Weights</TabsTrigger>
                      <TabsTrigger value="thresholds">Thresholds</TabsTrigger>
                    </TabsList>
                    
                    {/* Basic Info Tab */}
                    <TabsContent value="basic" className="space-y-4 mt-4">
                      <div>
                        <Label className="text-gray-300">Profile Name</Label>
                        <Input
                          value={profileName}
                          onChange={(e) => setProfileName(e.target.value)}
                          placeholder="e.g., Bellator Standard"
                          className="bg-[#1a1d24] border-[#2a2d35] text-white mt-2"
                        />
                      </div>
                      
                      <div>
                        <Label className="text-gray-300">Promotion</Label>
                        <Input
                          value={promotion}
                          onChange={(e) => setPromotion(e.target.value)}
                          placeholder="e.g., Bellator, ONE Championship, PFL"
                          className="bg-[#1a1d24] border-[#2a2d35] text-white mt-2"
                        />
                      </div>
                      
                      <div>
                        <Label className="text-gray-300">Description</Label>
                        <Textarea
                          value={description}
                          onChange={(e) => setDescription(e.target.value)}
                          placeholder="Describe this tuning profile..."
                          className="bg-[#1a1d24] border-[#2a2d35] text-white mt-2"
                          rows={3}
                        />
                      </div>
                    </TabsContent>
                    
                    {/* Weights Tab */}
                    <TabsContent value="weights" className="space-y-4 mt-4">
                      {Object.keys(weights).map((metric) => (
                        <div key={metric}>
                          <div className="flex items-center justify-between mb-2">
                            <Label className="text-gray-300">{metric}</Label>
                            <span className="text-amber-400 font-bold">{getWeightPercentage(metric)}%</span>
                          </div>
                          <Slider
                            value={[getWeightPercentage(metric)]}
                            onValueChange={(value) => updateWeight(metric, value[0])}
                            max={50}
                            step={1}
                            className="w-full"
                          />
                        </div>
                      ))}
                      <div className="text-xs text-gray-500 mt-4">
                        Note: Weights should sum to approximately 100%
                      </div>
                    </TabsContent>
                    
                    {/* Thresholds Tab */}
                    <TabsContent value="thresholds" className="space-y-4 mt-4">
                      <div>
                        <Label className="text-gray-300">10-9 Threshold (1 to this value)</Label>
                        <Input
                          type="number"
                          value={threshold109}
                          onChange={(e) => setThreshold109(parseInt(e.target.value) || 600)}
                          className="bg-[#1a1d24] border-[#2a2d35] text-white mt-2"
                        />
                        <div className="text-xs text-gray-500 mt-1">
                          Default: 600 (1-600 = 10-9)
                        </div>
                      </div>
                      
                      <div>
                        <Label className="text-gray-300">10-8 Threshold (above 10-9 to this value)</Label>
                        <Input
                          type="number"
                          value={threshold108}
                          onChange={(e) => setThreshold108(parseInt(e.target.value) || 900)}
                          className="bg-[#1a1d24] border-[#2a2d35] text-white mt-2"
                        />
                        <div className="text-xs text-gray-500 mt-1">
                          Default: 900 (601-900 = 10-8, 901+ = 10-7)
                        </div>
                      </div>
                    </TabsContent>
                  </Tabs>
                  
                  <div className="flex gap-3 mt-6">
                    <Button
                      onClick={createProfile}
                      className="flex-1 bg-amber-600 hover:bg-amber-700"
                    >
                      Create Profile
                    </Button>
                    <Button
                      onClick={() => {
                        setShowCreateDialog(false);
                        resetForm();
                      }}
                      className="flex-1 bg-gray-600 hover:bg-gray-700"
                    >
                      Cancel
                    </Button>
                  </div>
                </DialogContent>
              </Dialog>
              
              <Button
                onClick={() => navigate('/')}
                className="bg-[#1a1d24] hover:bg-[#22252d] text-gray-300"
              >
                Back to Events
              </Button>
            </div>
          </div>
        </Card>

        {/* Profiles List */}
        <div className="grid md:grid-cols-2 gap-6">
          {loading ? (
            <div className="col-span-2 text-center text-gray-400 py-12">
              Loading profiles...
            </div>
          ) : profiles.length === 0 ? (
            <Card className="col-span-2 bg-[#13151a] border-[#2a2d35] p-12">
              <div className="text-center text-gray-500">
                <Target className="w-16 h-16 mx-auto mb-4 opacity-50" />
                <div className="text-xl">No tuning profiles yet</div>
                <div className="text-sm mt-2">Create your first profile to customize scoring</div>
              </div>
            </Card>
          ) : (
            profiles.map((profile) => (
              <Card key={profile.id} className="bg-[#13151a] border-[#2a2d35] p-6">
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <div className="flex items-center gap-2 mb-2">
                      <h3 className="text-xl font-bold text-white">{profile.name}</h3>
                      {profile.is_default && (
                        <Badge className="bg-amber-900/30 text-amber-400 border-amber-700/30">
                          <Award className="w-3 h-3 mr-1" />
                          Default
                        </Badge>
                      )}
                      {!isOwner(profile) && (
                        <Badge className="bg-gray-900/30 text-gray-400 border-gray-700/30">
                          <Eye className="w-3 h-3 mr-1" />
                          View Only
                        </Badge>
                      )}
                    </div>
                    <div className="text-gray-400 mb-1">{profile.promotion}</div>
                    {profile.description && (
                      <div className="text-gray-500 text-sm">{profile.description}</div>
                    )}
                  </div>
                  
                  {!profile.is_default && isOwner(profile) && (
                    <Button
                      onClick={() => deleteProfile(profile.id)}
                      size="sm"
                      className="bg-red-900/30 hover:bg-red-900/50 text-red-400"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  )}
                </div>
                
                {/* Weight Summary - Only for Owners */}
                {isOwner(profile) ? (
                  <>
                    <div className="space-y-2">
                      <div className="text-sm font-semibold text-gray-400 uppercase tracking-wide">
                        Weights (Owner Only)
                      </div>
                      <div className="grid grid-cols-3 gap-2 text-sm">
                        {Object.entries(profile.weights).map(([key, value]) => (
                          <div key={key} className="bg-[#1a1d24] rounded p-2">
                            <span className="text-gray-400">{key}:</span>{' '}
                            <span className="text-white font-bold">{(value * 100).toFixed(0)}%</span>
                          </div>
                        ))}
                      </div>
                    </div>
                    
                    {/* Thresholds - Only for Owners */}
                    <div className="mt-4 pt-4 border-t border-[#2a2d35]">
                      <div className="text-sm font-semibold text-gray-400 uppercase tracking-wide mb-2">
                        Thresholds (Owner Only)
                      </div>
                      <div className="flex gap-4 text-sm">
                        <div>
                          <span className="text-gray-400">10-9:</span>{' '}
                          <span className="text-green-400">1-{profile.thresholds.threshold_10_9}</span>
                        </div>
                        <div>
                          <span className="text-gray-400">10-8:</span>{' '}
                          <span className="text-amber-400">{profile.thresholds.threshold_10_9 + 1}-{profile.thresholds.threshold_10_8}</span>
                        </div>
                        <div>
                          <span className="text-gray-400">10-7:</span>{' '}
                          <span className="text-red-400">{profile.thresholds.threshold_10_8 + 1}+</span>
                        </div>
                      </div>
                    </div>
                  </>
                ) : (
                  <div className="bg-[#1a1d24] border border-[#2a2d35] rounded p-4">
                    <div className="flex items-center gap-3 text-gray-400">
                      <EyeOff className="w-5 h-5" />
                      <div>
                        <div className="font-semibold mb-1">Restricted Access</div>
                        <div className="text-sm text-gray-500">
                          Metric weights and thresholds are only visible to the profile owner
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </Card>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
