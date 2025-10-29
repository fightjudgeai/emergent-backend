import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { db } from '@/firebase';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { toast } from 'sonner';
import { HelpCircle, AlertTriangle, CheckCircle2, TrendingUp, Activity } from 'lucide-react';
import { generateExplainability } from '@/utils/advancedFeatures';

export default function ExplainabilityCard({ roundScore, events, roundNum }) {
  const [explainability, setExplainability] = useState(null);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (roundScore && events) {
      const explain = generateExplainability(roundScore, events);
      setExplainability(explain);
    }
  }, [roundScore, events]);

  if (!explainability) return null;

  const getCardIcon = () => {
    if (roundScore.reasons.to_107) return <AlertTriangle className="w-6 h-6 text-red-500" />;
    if (roundScore.reasons.to_108) return <TrendingUp className="w-6 h-6 text-orange-500" />;
    return <Activity className="w-6 h-6 text-amber-500" />;
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button
          data-testid={`explain-round-${roundNum}-btn`}
          className="h-10 px-4 bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 text-white"
        >
          <HelpCircle className="mr-2 h-4 w-4" />
          Why {roundScore.card}?
        </Button>
      </DialogTrigger>
      
      <DialogContent className="bg-[#13151a] border-[#2a2d35] max-w-2xl">
        <DialogHeader>
          <DialogTitle className="text-white text-2xl flex items-center gap-3">
            {getCardIcon()}
            Round {roundNum} Explainability
          </DialogTitle>
        </DialogHeader>
        
        <div className="space-y-6 py-4">
          {/* Official Card */}
          <Card className="bg-gradient-to-r from-amber-900/30 to-orange-900/30 border-amber-700/50 p-6">
            <div className="text-center">
              <div className="text-sm text-amber-400 mb-2">Official Score Card</div>
              <div className="text-5xl font-bold text-white" style={{ fontFamily: 'Space Grotesk' }}>
                {roundScore.card}
              </div>
              <div className="text-sm text-gray-400 mt-2">
                Δ = {explainability.delta.toFixed(0)} points
              </div>
            </div>
          </Card>

          {/* Explanation Bullets */}
          <div className="space-y-3">
            <div className="text-sm text-gray-400 font-semibold uppercase tracking-wide">
              Why This Score?
            </div>
            <div className="space-y-2">
              {explainability.bullets.map((bullet, idx) => (
                <div key={idx} className="flex items-start gap-3 bg-[#1a1d24] p-3 rounded-lg border border-[#2a2d35]">
                  <CheckCircle2 className="w-5 h-5 text-green-500 mt-0.5 flex-shrink-0" />
                  <span className="text-gray-300">{bullet}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Flags */}
          {explainability.flags.length > 0 && (
            <div className="space-y-3">
              <div className="text-sm text-gray-400 font-semibold uppercase tracking-wide">
                Review Flags
              </div>
              <div className="flex flex-wrap gap-2">
                {explainability.flags.map((flag, idx) => (
                  <Badge key={idx} className="bg-yellow-900/30 text-yellow-400 border-yellow-700/30">
                    <AlertTriangle className="w-3 h-3 mr-1" />
                    {flag.replace(/_/g, ' ')}
                  </Badge>
                ))}
              </div>
            </div>
          )}

          {/* Gates Triggered */}
          <div className="space-y-3">
            <div className="text-sm text-gray-400 font-semibold uppercase tracking-wide">
              Dominance Gates
            </div>
            <div className="grid grid-cols-3 gap-3">
              <Card className={`p-3 text-center ${
                explainability.gates.gates_winner.finish_threat 
                  ? 'bg-red-900/30 border-red-700/50' 
                  : 'bg-[#1a1d24] border-[#2a2d35]'
              }`}>
                <div className="text-xs text-gray-400 mb-1">Finish Threat</div>
                <div className="text-lg font-bold text-white">
                  {explainability.gates.gates_winner.finish_threat ? 'YES' : 'NO'}
                </div>
              </Card>
              
              <Card className={`p-3 text-center ${
                explainability.gates.gates_winner.control_dom 
                  ? 'bg-red-900/30 border-red-700/50' 
                  : 'bg-[#1a1d24] border-[#2a2d35]'
              }`}>
                <div className="text-xs text-gray-400 mb-1">Control Dom</div>
                <div className="text-lg font-bold text-white">
                  {explainability.gates.gates_winner.control_dom ? 'YES' : 'NO'}
                </div>
              </Card>
              
              <Card className={`p-3 text-center ${
                explainability.gates.gates_winner.multi_cat_dom 
                  ? 'bg-red-900/30 border-red-700/50' 
                  : 'bg-[#1a1d24] border-[#2a2d35]'
              }`}>
                <div className="text-xs text-gray-400 mb-1">Multi-Cat Dom</div>
                <div className="text-lg font-bold text-white">
                  {explainability.gates.gates_winner.multi_cat_dom ? 'YES' : 'NO'}
                </div>
              </Card>
            </div>
          </div>

          <Separator className="bg-[#2a2d35]" />

          <div className="text-xs text-gray-500 text-center">
            Commission-approved explainability for transparency and review
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
