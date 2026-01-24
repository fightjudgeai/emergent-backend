/**
 * Fight Judge AI - Broadcast Components v3.0
 * Converted from Lovable.dev TypeScript to JavaScript
 * 
 * Components:
 * - StrikeCounter: Live strike statistics display
 * - LowerThird: Fighter introduction graphics
 */

import { memo, useState, useEffect, useRef } from "react";
import '@/styles/fjai-broadcast.css';

// ═══════════════════════════════════════════════════════════════════════════════
// ANIMATED NUMBER COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

const AnimatedNumber = memo(function AnimatedNumber({ value, color }) {
  const [displayValue, setDisplayValue] = useState(0);
  const prevValue = useRef(value);

  useEffect(() => {
    if (value !== prevValue.current) {
      const start = prevValue.current;
      const end = value;
      const duration = 800;
      const startTime = performance.now();

      const animate = (currentTime) => {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3);
        setDisplayValue(Math.round(start + (end - start) * eased));

        if (progress < 1) {
          requestAnimationFrame(animate);
        }
      };

      requestAnimationFrame(animate);
      prevValue.current = value;
    }
  }, [value]);

  return (
    <span className={`fjai-stat-number ${color === "red" ? "fjai-stat-red" : "fjai-stat-blue"}`}>
      {displayValue}
    </span>
  );
});

// ═══════════════════════════════════════════════════════════════════════════════
// STRIKE COUNTER COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

export const StrikeCounter = memo(function StrikeCounter({
  stats,
  redName,
  blueName,
  isVisible,
  isFullscreen = false,
}) {
  if (!isVisible) return null;

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const showKnockdowns = (stats.knockdowns?.red ?? 0) > 0 || (stats.knockdowns?.blue ?? 0) > 0;

  return (
    <div className={`fjai-stats-panel ${isFullscreen ? "fjai-stats-fullscreen" : ""}`} data-testid="strike-counter">
      <div className="fjai-stats-header">
        <span className="fjai-stats-name fjai-text-red">{redName}</span>
        <span className="fjai-stats-title">LIVE STATS</span>
        <span className="fjai-stats-name fjai-text-blue">{blueName}</span>
      </div>

      <div className="fjai-stats-grid">
        <div className="fjai-stat-row">
          <AnimatedNumber value={stats.total?.red ?? 0} color="red" />
          <span className="fjai-stat-label">Total Strikes</span>
          <AnimatedNumber value={stats.total?.blue ?? 0} color="blue" />
        </div>

        <div className="fjai-stat-row">
          <AnimatedNumber value={stats.significant?.red ?? 0} color="red" />
          <span className="fjai-stat-label">Sig. Strikes</span>
          <AnimatedNumber value={stats.significant?.blue ?? 0} color="blue" />
        </div>

        {showKnockdowns && (
          <div className="fjai-stat-row">
            <AnimatedNumber value={stats.knockdowns?.red ?? 0} color="red" />
            <span className="fjai-stat-label">Knockdowns</span>
            <AnimatedNumber value={stats.knockdowns?.blue ?? 0} color="blue" />
          </div>
        )}

        <div className="fjai-stat-row">
          <AnimatedNumber value={stats.takedowns?.red ?? 0} color="red" />
          <span className="fjai-stat-label">Takedowns</span>
          <AnimatedNumber value={stats.takedowns?.blue ?? 0} color="blue" />
        </div>

        <div className="fjai-stat-row">
          <span className="fjai-stat-number fjai-stat-red">{formatTime(stats.controlTime?.red ?? 0)}</span>
          <span className="fjai-stat-label">Control Time</span>
          <span className="fjai-stat-number fjai-stat-blue">{formatTime(stats.controlTime?.blue ?? 0)}</span>
        </div>
      </div>
    </div>
  );
});

// ═══════════════════════════════════════════════════════════════════════════════
// LOWER THIRD COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

export const LowerThird = memo(function LowerThird({
  fighter,
  corner,
  isVisible,
  isFullscreen = false,
}) {
  if (!isVisible) return null;

  const isRed = corner === "red";
  const accentColor = isRed ? "hsl(348, 83%, 47%)" : "hsl(195, 100%, 70%)";

  return (
    <div className={`fjai-lower-third ${isFullscreen ? "fjai-lt-fullscreen" : ""}`} data-testid={`lower-third-${corner}`}>
      <div 
        className="fjai-lt-container"
        style={{ borderColor: accentColor }}
      >
        <div 
          className="fjai-lt-corner-bar"
          style={{ background: accentColor }}
        />

        {fighter.photo && (
          <img 
            src={fighter.photo} 
            alt={fighter.name}
            className={`fjai-lt-photo ${isRed ? 'fjai-lt-photo-red' : 'fjai-lt-photo-blue'}`}
          />
        )}

        <div className="fjai-lt-content">
          {fighter.nickname && (
            <div className="fjai-lt-nickname" style={{ color: accentColor }}>
              "{fighter.nickname}"
            </div>
          )}
          <div className="fjai-lt-name">{fighter.name}</div>
          <div className="fjai-lt-details">
            {fighter.record && <span>{fighter.record}</span>}
            {fighter.weightClass && <span> • {fighter.weightClass}</span>}
          </div>
          {fighter.gym && (
            <div className="fjai-lt-gym">{fighter.gym}</div>
          )}
        </div>

        <div 
          className="fjai-lt-corner-label"
          style={{ color: accentColor }}
        >
          {isRed ? "RED" : "BLUE"} CORNER
        </div>
      </div>
    </div>
  );
});

// ═══════════════════════════════════════════════════════════════════════════════
// DUAL LOWER THIRDS (Both fighters side by side)
// ═══════════════════════════════════════════════════════════════════════════════

export const DualLowerThirds = memo(function DualLowerThirds({
  redFighter,
  blueFighter,
  isVisible,
}) {
  if (!isVisible) return null;

  const accentRed = "hsl(348, 83%, 47%)";
  const accentBlue = "hsl(195, 100%, 70%)";

  return (
    <div className="fixed bottom-8 left-0 right-0 flex justify-center gap-8 px-8" data-testid="dual-lower-thirds">
      {/* Red Fighter */}
      <div 
        className="fjai-lt-container flex-1 max-w-md"
        style={{ borderColor: accentRed }}
      >
        <div className="fjai-lt-corner-bar" style={{ background: accentRed }} />
        
        {redFighter.photo && (
          <img 
            src={redFighter.photo} 
            alt={redFighter.name}
            className="fjai-lt-photo fjai-lt-photo-red"
          />
        )}

        <div className="fjai-lt-content">
          <div className="fjai-lt-name">{redFighter.name}</div>
          <div className="fjai-lt-details">
            {redFighter.record && <span>{redFighter.record}</span>}
            {redFighter.weightClass && <span> • {redFighter.weightClass}</span>}
          </div>
        </div>

        <div className="fjai-lt-corner-label" style={{ color: accentRed }}>
          RED CORNER
        </div>
      </div>

      {/* Blue Fighter */}
      <div 
        className="fjai-lt-container flex-1 max-w-md"
        style={{ borderColor: accentBlue }}
      >
        <div className="fjai-lt-corner-bar" style={{ background: accentBlue }} />
        
        {blueFighter.photo && (
          <img 
            src={blueFighter.photo} 
            alt={blueFighter.name}
            className="fjai-lt-photo fjai-lt-photo-blue"
          />
        )}

        <div className="fjai-lt-content">
          <div className="fjai-lt-name">{blueFighter.name}</div>
          <div className="fjai-lt-details">
            {blueFighter.record && <span>{blueFighter.record}</span>}
            {blueFighter.weightClass && <span> • {blueFighter.weightClass}</span>}
          </div>
        </div>

        <div className="fjai-lt-corner-label" style={{ color: accentBlue }}>
          BLUE CORNER
        </div>
      </div>
    </div>
  );
});

export default { StrikeCounter, LowerThird, DualLowerThirds };
