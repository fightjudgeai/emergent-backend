import { memo } from "react";

export const FighterHeader = memo(function FighterHeader({
  redName,
  blueName,
  winner,
  compact = false,
}) {
  const padding = compact ? "px-6 py-3" : "px-8 py-6";
  const barHeight = compact ? "h-12" : "h-16";
  const nameSize = compact ? "text-2xl" : "text-3xl";

  return (
    <div className={`grid grid-cols-3 gap-4 ${padding}`}>
      <div className="flex items-center gap-4">
        <div className={`w-4 ${barHeight} bg-lb-corner-red transition-all duration-500 ${winner === "red" ? "animate-pulse shadow-[0_0_20px_hsl(348_83%_47%_/_0.6)]" : ""}`} />
        <div className="flex flex-col">
          <span className="text-xs font-medium tracking-[0.3em] uppercase text-lb-corner-red">Red Corner</span>
          <span className={`${nameSize} font-bold tracking-wide uppercase text-white`}>{redName}</span>
        </div>
      </div>
      <div className="flex items-center justify-center">
        <div className="w-12 h-px bg-lb-accent-gold" />
        <span className="px-4 text-lg font-bold tracking-widest text-lb-accent-gold">VS</span>
        <div className="w-12 h-px bg-lb-accent-gold" />
      </div>
      <div className="flex items-center justify-end gap-4">
        <div className="flex flex-col items-end">
          <span className="text-xs font-medium tracking-[0.3em] uppercase text-lb-corner-blue">Blue Corner</span>
          <span className={`${nameSize} font-bold tracking-wide uppercase text-white`}>{blueName}</span>
        </div>
        <div className={`w-4 ${barHeight} bg-lb-corner-blue transition-all duration-500 ${winner === "blue" ? "animate-pulse shadow-[0_0_20px_hsl(225_73%_57%_/_0.6)]" : "shadow-[0_0_20px_hsl(225_73%_57%_/_0.6)]"}`} />
      </div>
    </div>
  );
});
