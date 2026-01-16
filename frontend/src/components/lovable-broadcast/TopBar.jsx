import { memo } from "react";

export const TopBar = memo(function TopBar({ event, division, compact = false }) {
  const padding = compact ? "px-6 py-2" : "px-8 py-4";
  const eventSize = compact ? "text-xl" : "text-2xl";
  const divisionSize = compact ? "text-base" : "text-lg";
  const barHeight = compact ? "h-6" : "h-8";

  return (
    <header className={`flex items-center justify-between ${padding} border-b-2 border-lb-gold/50 bg-gradient-to-b from-lb-muted/30 to-transparent`}>
      <div className="flex items-center gap-3">
        <div className={`w-1 ${barHeight} bg-lb-gold`} />
        <span className={`${eventSize} font-semibold tracking-wider uppercase text-white`}>{event}</span>
      </div>
      <div className="flex flex-col items-center">
        <span className={`${divisionSize} font-medium tracking-widest uppercase text-gray-400`}>{division} Bout</span>
      </div>
      <div className="flex items-center gap-3">
        <span className="text-sm font-medium tracking-widest uppercase text-lb-gold">Fight Judge AI</span>
        <div className={`w-1 ${barHeight} bg-lb-gold`} />
      </div>
    </header>
  );
});
