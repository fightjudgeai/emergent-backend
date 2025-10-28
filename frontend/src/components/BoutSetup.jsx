import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { collection, addDoc, serverTimestamp } from 'firebase/firestore';
import { db } from '@/firebase';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { toast } from 'sonner';
import { Swords } from 'lucide-react';

export default function BoutSetup() {
  const navigate = useNavigate();
  const [fighter1, setFighter1] = useState('');
  const [fighter2, setFighter2] = useState('');
  const [loading, setLoading] = useState(false);

  const createBout = async () => {
    if (!fighter1.trim() || !fighter2.trim()) {
      toast.error('Please enter both fighter names');
      return;
    }

    setLoading(true);
    try {
      const boutRef = await addDoc(collection(db, 'bouts'), {
        fighter1: fighter1.trim(),
        fighter2: fighter2.trim(),
        currentRound: 1,
        totalRounds: 3,
        status: 'active',
        createdAt: serverTimestamp()
      });

      toast.success('Bout created successfully!');
      
      // Navigate to operator panel
      navigate(`/operator/${boutRef.id}`);
    } catch (error) {
      console.error('Error creating bout:', error);
      toast.error('Failed to create bout');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4" style={{
      background: 'linear-gradient(135deg, #0f1419 0%, #1a1f2e 50%, #0f1419 100%)'
    }}>
      <Card className="w-full max-w-2xl bg-[#13151a]/95 border-[#2a2d35] backdrop-blur-xl shadow-2xl">
        <CardHeader className="text-center space-y-4 pb-8">
          <div className="mx-auto w-20 h-20 bg-gradient-to-br from-amber-500 to-orange-600 rounded-2xl flex items-center justify-center shadow-lg">
            <Swords className="w-10 h-10 text-white" />
          </div>
          <CardTitle className="text-4xl font-bold tracking-tight" style={{
            background: 'linear-gradient(135deg, #fbbf24 0%, #f97316 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent'
          }}>
            Combat Judging System
          </CardTitle>
          <CardDescription className="text-lg text-gray-400">
            Create a new bout to begin scoring
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="space-y-2">
            <Label htmlFor="fighter1" className="text-gray-300 text-sm font-medium">Fighter 1 (Red Corner)</Label>
            <Input
              id="fighter1"
              data-testid="fighter1-input"
              placeholder="Enter fighter name"
              value={fighter1}
              onChange={(e) => setFighter1(e.target.value)}
              className="h-12 bg-[#1a1d24] border-[#2a2d35] text-white placeholder:text-gray-500 focus:border-amber-500 focus:ring-amber-500/20"
            />
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="fighter2" className="text-gray-300 text-sm font-medium">Fighter 2 (Blue Corner)</Label>
            <Input
              id="fighter2"
              data-testid="fighter2-input"
              placeholder="Enter fighter name"
              value={fighter2}
              onChange={(e) => setFighter2(e.target.value)}
              className="h-12 bg-[#1a1d24] border-[#2a2d35] text-white placeholder:text-gray-500 focus:border-amber-500 focus:ring-amber-500/20"
            />
          </div>

          <div className="pt-4 space-y-3">
            <Button
              data-testid="create-bout-btn"
              onClick={createBout}
              disabled={loading}
              className="w-full h-14 text-lg font-semibold bg-gradient-to-r from-amber-500 to-orange-600 hover:from-amber-600 hover:to-orange-700 text-white shadow-lg transition-all duration-200"
            >
              {loading ? 'Creating Bout...' : 'Create Bout & Start Operator Panel'}
            </Button>
            
            <p className="text-center text-sm text-gray-500">
              3 rounds • Real-time scoring • Firestore sync
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}