import { memo } from "react";

export const StandbyScreen = memo(function StandbyScreen({ event, isVisible }) {
  if (!isVisible) return null;

  return (
    <div className="absolute inset-0 bg-black flex flex-col items-center justify-center z-50">
      <div className="lb-broadcast-frame p-12 bg-gradient-to-b from-lb-muted/20 to-transparent mb-0">
        <div className="flex flex-col items-center mb-6">
          <div className="relative">
            <div className="absolute -left-10 top-1/2 -translate-y-1/2 w-8 h-px bg-gradient-to-r from-transparent to-lb-gold" />
            <div className="absolute -right-10 top-1/2 -translate-y-1/2 w-8 h-px bg-gradient-to-l from-transparent to-lb-gold" />
            <span className="text-2xl font-light tracking-[0.4em] text-lb-gold">PFC 50</span>
          </div>
          <div className="mt-2 w-16 h-px bg-gradient-to-r from-transparent via-lb-gold to-transparent" />
        </div>
        <h1 className="text-6xl font-bold tracking-[0.3em] uppercase text-white text-center mb-4">{event}</h1>
        <div className="flex items-center justify-center gap-4 mb-8">
          <span className="text-2xl font-medium tracking-wider text-lb-gold">✦</span>
          <span className="text-xl font-medium tracking-[0.3em] uppercase text-lb-gold">Unofficial Scoring Standby</span>
          <span className="text-2xl font-medium tracking-wider text-lb-gold">✦</span>
        </div>
        <div className="h-px w-64 mx-auto bg-gradient-to-r from-transparent via-lb-gold/50 to-transparent" />
      </div>
      <div className="absolute bottom-6 left-0 right-0 flex justify-center">
        <span className="text-[10px] font-normal tracking-[0.15em] uppercase text-gray-600">Powered by Fight Judge AI</span>
      </div>
      <div className="absolute top-4 left-4 w-8 h-8 border-t-2 border-l-2 border-lb-gold/30" />
      <div className="absolute top-4 right-4 w-8 h-8 border-t-2 border-r-2 border-lb-gold/30" />
      <div className="absolute bottom-4 left-4 w-8 h-8 border-b-2 border-l-2 border-lb-gold/30" />
      <div className="absolute bottom-4 right-4 w-8 h-8 border-b-2 border-r-2 border-lb-gold/30" />
    </div>
  );
});
