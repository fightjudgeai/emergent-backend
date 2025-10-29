import { createContext, useContext, useState, useEffect } from 'react';

const AccessibilityContext = createContext();

export const useAccessibility = () => {
  const context = useContext(AccessibilityContext);
  if (!context) {
    throw new Error('useAccessibility must be used within AccessibilityProvider');
  }
  return context;
};

export function AccessibilityProvider({ children }) {
  const [settings, setSettings] = useState({
    largeType: false,
    highContrast: false,
    noAnimations: false,
    audibleCues: false,
    singleTapConfirm: false
  });

  useEffect(() => {
    // Load settings from localStorage
    const saved = localStorage.getItem('accessibilitySettings');
    if (saved) {
      setSettings(JSON.parse(saved));
    }
  }, []);

  useEffect(() => {
    // Save settings to localStorage
    localStorage.setItem('accessibilitySettings', JSON.stringify(settings));
    
    // Apply global styles
    applyAccessibilityStyles(settings);
  }, [settings]);

  const applyAccessibilityStyles = (settings) => {
    const root = document.documentElement;
    
    if (settings.largeType) {
      root.style.setProperty('--base-font-size', '20px');
      root.style.setProperty('--heading-scale', '1.4');
    } else {
      root.style.setProperty('--base-font-size', '16px');
      root.style.setProperty('--heading-scale', '1.2');
    }

    if (settings.highContrast) {
      root.style.setProperty('--bg-primary', '#000000');
      root.style.setProperty('--text-primary', '#ffffff');
      root.style.setProperty('--border-color', '#ffffff');
    } else {
      root.style.setProperty('--bg-primary', '#0a0a0b');
      root.style.setProperty('--text-primary', '#e5e5e7');
      root.style.setProperty('--border-color', '#2a2d35');
    }

    if (settings.noAnimations) {
      root.style.setProperty('--transition-speed', '0ms');
    } else {
      root.style.setProperty('--transition-speed', '200ms');
    }
  };

  const toggleSetting = (key) => {
    setSettings(prev => ({ ...prev, [key]: !prev[key] }));
  };

  const playAudibleCue = (type) => {
    if (!settings.audibleCues) return;
    
    // Simple beep using Web Audio API
    const audioContext = new (window.AudioContext || window.webkitAudioContext)();
    const oscillator = audioContext.createOscillator();
    const gainNode = audioContext.createGain();
    
    oscillator.connect(gainNode);
    gainNode.connect(audioContext.destination);
    
    // Different frequencies for different cues
    const frequencies = {
      success: 800,
      error: 400,
      warning: 600,
      info: 700
    };
    
    oscillator.frequency.value = frequencies[type] || 500;
    gainNode.gain.value = 0.1;
    
    oscillator.start();
    setTimeout(() => oscillator.stop(), 100);
  };

  return (
    <AccessibilityContext.Provider value={{ settings, toggleSetting, playAudibleCue }}>
      {children}
    </AccessibilityContext.Provider>
  );
}

export function AccessibilitySettings() {
  const { settings, toggleSetting } = useAccessibility();

  return (
    <div className="space-y-4">
      <h3 className="text-white font-semibold text-lg">Accessibility Settings</h3>
      
      <div className="space-y-3">
        <label className="flex items-center justify-between bg-[#1a1d24] p-4 rounded-lg border border-[#2a2d35] cursor-pointer">
          <div>
            <div className="text-white font-medium">Large Type Mode</div>
            <div className="text-gray-400 text-sm">Increase all font sizes by 25%</div>
          </div>
          <input
            type="checkbox"
            checked={settings.largeType}
            onChange={() => toggleSetting('largeType')}
            className="w-5 h-5"
          />
        </label>

        <label className="flex items-center justify-between bg-[#1a1d24] p-4 rounded-lg border border-[#2a2d35] cursor-pointer">
          <div>
            <div className="text-white font-medium">High Contrast Theme</div>
            <div className="text-gray-400 text-sm">Pure black background, white text</div>
          </div>
          <input
            type="checkbox"
            checked={settings.highContrast}
            onChange={() => toggleSetting('highContrast')}
            className="w-5 h-5"
          />
        </label>

        <label className="flex items-center justify-between bg-[#1a1d24] p-4 rounded-lg border border-[#2a2d35] cursor-pointer">
          <div>
            <div className="text-white font-medium">No Animations</div>
            <div className="text-gray-400 text-sm">Disable all transitions and animations</div>
          </div>
          <input
            type="checkbox"
            checked={settings.noAnimations}
            onChange={() => toggleSetting('noAnimations')}
            className="w-5 h-5"
          />
        </label>

        <label className="flex items-center justify-between bg-[#1a1d24] p-4 rounded-lg border border-[#2a2d35] cursor-pointer">
          <div>
            <div className="text-white font-medium">Audible Cues</div>
            <div className="text-gray-400 text-sm">Play sounds for important actions</div>
          </div>
          <input
            type="checkbox"
            checked={settings.audibleCues}
            onChange={() => toggleSetting('audibleCues')}
            className="w-5 h-5"
          />
        </label>

        <label className="flex items-center justify-between bg-[#1a1d24] p-4 rounded-lg border border-[#2a2d35] cursor-pointer">
          <div>
            <div className="text-white font-medium">Single-Tap Confirmation</div>
            <div className="text-gray-400 text-sm">Skip confirmation dialogs</div>
          </div>
          <input
            type="checkbox"
            checked={settings.singleTapConfirm}
            onChange={() => toggleSetting('singleTapConfirm')}
            className="w-5 h-5"
          />
        </label>
      </div>
    </div>
  );
}
