import { memo } from "react";

export const SignalLostOverlay = memo(function SignalLostOverlay({ isVisible }) {
  if (!isVisible) return null;

  return (
    <div className="absolute inset-0 bg-black/95 flex flex-col items-center justify-center z-50 backdrop-blur-sm">
      <div className="w-20 h-20 mb-8 relative">
        <div className="absolute inset-0 border-4 border-lb-gold rounded-full animate-ping opacity-30" />
        <div className="absolute inset-0 border-4 border-lb-gold rounded-full flex items-center justify-center">
          <svg className="w-10 h-10 text-lb-gold" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
        </div>
      </div>
      <div className="text-center">
        <h2 className="text-3xl font-bold tracking-[0.2em] uppercase text-lb-gold mb-4 lb-signal-pulse">Signal Lost</h2>
        <p className="text-xl font-medium tracking-widest uppercase text-gray-400">Official Scores Locked</p>
      </div>
      <div className="absolute bottom-0 left-0 right-0 h-1 bg-gradient-to-r from-transparent via-lb-gold to-transparent" />
    </div>
  );
});
