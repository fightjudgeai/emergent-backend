import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useAccessibility } from '@/contexts/AccessibilityContext';
import { toast } from 'sonner';
import { Accessibility, Type, Eye, Volume2, Keyboard, RefreshCw } from 'lucide-react';

export default function AccessibilitySettings() {
  const navigate = useNavigate();
  const { settings, updateSetting, resetSettings } = useAccessibility();

  const handleReset = () => {
    resetSettings();
    toast.success('Accessibility settings reset to default');
  };

  return (
    <div className="min-h-screen bg-[#0a0a0b] p-4 md:p-8">
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <Card className="bg-[#13151a] border-[#2a2d35] p-8 mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-4xl font-bold text-white mb-2 flex items-center gap-3">
                <Accessibility className="w-10 h-10 text-blue-500" />
                Accessibility Settings
              </h1>
              <p className="text-gray-400 text-lg">
                Customize the interface for better readability and usability
              </p>
            </div>
            <div className="flex gap-3">
              <Button
                onClick={handleReset}
                className="bg-gray-600 hover:bg-gray-700 text-white"
              >
                <RefreshCw className="mr-2 h-4 w-4" />
                Reset to Default
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

        {/* Settings Sections */}
        <div className="space-y-6">
          {/* Large Type Mode */}
          <Card className="bg-[#13151a] border-[#2a2d35] p-6">
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 bg-blue-600 rounded-lg flex items-center justify-center">
                <Type className="w-6 h-6 text-white" />
              </div>
              <div className="flex-1">
                <h3 className="text-xl font-bold text-white mb-2">Large Type Mode</h3>
                <p className="text-gray-400 mb-4">
                  Increase text size throughout the application for better readability
                </p>
                
                <div className="grid grid-cols-3 gap-3">
                  <Button
                    onClick={() => updateSetting('largeType', 'normal')}
                    className={`${
                      settings.largeType === 'normal'
                        ? 'bg-blue-600 text-white'
                        : 'bg-[#1a1d24] text-gray-300'
                    } hover:bg-blue-700`}
                  >
                    Normal (16px)
                  </Button>
                  <Button
                    onClick={() => updateSetting('largeType', 'large')}
                    className={`${
                      settings.largeType === 'large'
                        ? 'bg-blue-600 text-white'
                        : 'bg-[#1a1d24] text-gray-300'
                    } hover:bg-blue-700`}
                  >
                    Large (18px)
                  </Button>
                  <Button
                    onClick={() => updateSetting('largeType', 'extra-large')}
                    className={`${
                      settings.largeType === 'extra-large'
                        ? 'bg-blue-600 text-white'
                        : 'bg-[#1a1d24] text-gray-300'
                    } hover:bg-blue-700`}
                  >
                    Extra Large (20px)
                  </Button>
                </div>
                
                {settings.largeType !== 'normal' && (
                  <Badge className="bg-green-900/30 text-green-400 border-green-700/30 mt-3">
                    ✓ Active
                  </Badge>
                )}
              </div>
            </div>
          </Card>

          {/* High Contrast Mode */}
          <Card className="bg-[#13151a] border-[#2a2d35] p-6">
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 bg-purple-600 rounded-lg flex items-center justify-center">
                <Eye className="w-6 h-6 text-white" />
              </div>
              <div className="flex-1">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-xl font-bold text-white">High Contrast Mode</h3>
                  <Switch
                    checked={settings.highContrast}
                    onCheckedChange={(checked) => updateSetting('highContrast', checked)}
                    aria-label="Toggle high contrast mode"
                  />
                </div>
                <p className="text-gray-400 mb-3">
                  Increase color contrast for better visibility. Uses stronger borders, darker backgrounds, and enhanced text contrast.
                </p>
                
                {settings.highContrast && (
                  <div className="bg-[#1a1d24] border-2 border-purple-500 rounded p-3">
                    <div className="text-sm text-purple-400 font-semibold mb-1">High Contrast Active</div>
                    <div className="text-xs text-gray-400">
                      Interface colors have been adjusted for maximum contrast
                    </div>
                  </div>
                )}
              </div>
            </div>
          </Card>

          {/* Reduced Motion */}
          <Card className="bg-[#13151a] border-[#2a2d35] p-6">
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 bg-amber-600 rounded-lg flex items-center justify-center">
                <Volume2 className="w-6 h-6 text-white" />
              </div>
              <div className="flex-1">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-xl font-bold text-white">Reduced Motion</h3>
                  <Switch
                    checked={settings.reducedMotion}
                    onCheckedChange={(checked) => updateSetting('reducedMotion', checked)}
                    aria-label="Toggle reduced motion"
                  />
                </div>
                <p className="text-gray-400 mb-3">
                  Minimize animations and transitions. Helpful for users with motion sensitivity or vestibular disorders.
                </p>
                
                {settings.reducedMotion && (
                  <Badge className="bg-amber-900/30 text-amber-400 border-amber-700/30">
                    ✓ Animations Reduced
                  </Badge>
                )}
              </div>
            </div>
          </Card>

          {/* Screen Reader Mode */}
          <Card className="bg-[#13151a] border-[#2a2d35] p-6">
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 bg-green-600 rounded-lg flex items-center justify-center">
                <Keyboard className="w-6 h-6 text-white" />
              </div>
              <div className="flex-1">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-xl font-bold text-white">Enhanced Screen Reader Support</h3>
                  <Switch
                    checked={settings.screenReaderMode}
                    onCheckedChange={(checked) => updateSetting('screenReaderMode', checked)}
                    aria-label="Toggle screen reader mode"
                  />
                </div>
                <p className="text-gray-400 mb-3">
                  Add extra ARIA labels and descriptions for screen readers. Improves navigation for visually impaired users.
                </p>
                
                {settings.screenReaderMode && (
                  <div className="bg-[#1a1d24] border border-green-700/30 rounded p-3">
                    <div className="text-sm text-green-400 font-semibold mb-1">Screen Reader Mode Active</div>
                    <div className="text-xs text-gray-400">
                      Enhanced ARIA labels and descriptions enabled
                    </div>
                  </div>
                )}
              </div>
            </div>
          </Card>

          {/* Keyboard Navigation Info */}
          <Card className="bg-blue-900/20 border-blue-700/30 p-6">
            <div className="flex items-start gap-4">
              <Keyboard className="w-6 h-6 text-blue-400 mt-1" />
              <div>
                <h3 className="text-lg font-bold text-blue-400 mb-2">Keyboard Navigation</h3>
                <div className="space-y-2 text-sm text-gray-300">
                  <div><kbd className="bg-[#1a1d24] px-2 py-1 rounded">Tab</kbd> - Navigate forward</div>
                  <div><kbd className="bg-[#1a1d24] px-2 py-1 rounded">Shift + Tab</kbd> - Navigate backward</div>
                  <div><kbd className="bg-[#1a1d24] px-2 py-1 rounded">Enter</kbd> or <kbd className="bg-[#1a1d24] px-2 py-1 rounded">Space</kbd> - Activate button</div>
                  <div><kbd className="bg-[#1a1d24] px-2 py-1 rounded">Esc</kbd> - Close dialogs</div>
                </div>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
