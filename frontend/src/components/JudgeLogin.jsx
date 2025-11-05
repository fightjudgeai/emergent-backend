import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import firebase from 'firebase/compat/app';
import { db } from '@/firebase';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { toast } from 'sonner';
import { Shield, LogIn } from 'lucide-react';

export default function JudgeLogin() {
  const navigate = useNavigate();
  const [judgeId, setJudgeId] = useState('');
  const [judgeName, setJudgeName] = useState('');
  const [organization, setOrganization] = useState('UFC');
  const [customOrganization, setCustomOrganization] = useState('');
  const [loading, setLoading] = useState(false);

  const handleLogin = () => {
    if (!judgeId.trim() || !judgeName.trim()) {
      toast.error('Please enter both Judge ID and Name');
      return;
    }

    setLoading(true);
    
    // Store in localStorage
    localStorage.setItem('judgeProfile', JSON.stringify({
      judgeId: judgeId.trim(),
      judgeName: judgeName.trim(),
      organization
    }));

    toast.success(`Welcome, ${judgeName}!`);
    
    // Use window.location for more reliable navigation
    setTimeout(() => {
      window.location.href = '/';
    }, 500);
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4" style={{
      background: 'linear-gradient(135deg, #0f1419 0%, #1a1f2e 50%, #0f1419 100%)'
    }}>
      <Card className="w-full max-w-md bg-[#13151a]/95 border-[#2a2d35] backdrop-blur-xl shadow-2xl">
        <CardHeader className="text-center space-y-4 pb-8">
          <div className="mx-auto w-20 h-20 bg-gradient-to-br from-amber-500 to-orange-600 rounded-2xl flex items-center justify-center shadow-lg">
            <Shield className="w-10 h-10 text-white" />
          </div>
          <CardTitle className="text-4xl font-bold tracking-tight" style={{
            background: 'linear-gradient(135deg, #fbbf24 0%, #f97316 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent'
          }}>
            Judge Portal
          </CardTitle>
          <CardDescription className="text-lg text-gray-400">
            Sign in to access scoring system
          </CardDescription>
        </CardHeader>
        
        <CardContent className="space-y-6">
          <div className="space-y-2">
            <Label htmlFor="judgeId" className="text-gray-300 text-sm font-medium">Judge ID</Label>
            <Input
              id="judgeId"
              data-testid="judge-id-input"
              placeholder="Enter your Judge ID"
              value={judgeId}
              onChange={(e) => setJudgeId(e.target.value)}
              className="h-12 bg-[#1a1d24] border-[#2a2d35] text-white placeholder:text-gray-500 focus:border-amber-500 focus:ring-amber-500/20"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="judgeName" className="text-gray-300 text-sm font-medium">Full Name</Label>
            <Input
              id="judgeName"
              data-testid="judge-name-input"
              placeholder="Enter your full name"
              value={judgeName}
              onChange={(e) => setJudgeName(e.target.value)}
              className="h-12 bg-[#1a1d24] border-[#2a2d35] text-white placeholder:text-gray-500 focus:border-amber-500 focus:ring-amber-500/20"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="organization" className="text-gray-300 text-sm font-medium">Organization</Label>
            <Select value={organization} onValueChange={setOrganization}>
              <SelectTrigger className="h-12 bg-[#1a1d24] border-[#2a2d35] text-white">
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
          </div>

          <div className="pt-4">
            <Button
              data-testid="login-btn"
              onClick={handleLogin}
              disabled={loading}
              className="w-full h-14 text-lg font-semibold bg-gradient-to-r from-amber-500 to-orange-600 hover:from-amber-600 hover:to-orange-700 text-white shadow-lg transition-all duration-200"
            >
              <LogIn className="mr-2 h-5 w-5" />
              {loading ? 'Signing In...' : 'Sign In'}
            </Button>
          </div>

          <p className="text-center text-sm text-gray-500 pt-2">
            Your profile tracks all scored fights and certifications
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
