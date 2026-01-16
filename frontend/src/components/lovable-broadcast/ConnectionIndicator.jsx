import { memo } from "react";
import { Wifi, WifiOff, AlertTriangle, Shield } from "lucide-react";

export const ConnectionIndicator = memo(function ConnectionIndicator({
  connectionStatus,
  boutId,
  isDemo = false,
  isOverride = false,
}) {
  const getStatusConfig = () => {
    if (isOverride) {
      return {
        icon: Shield,
        label: "OVERRIDE",
        bgClass: "bg-amber-600/30 border-amber-500",
        textClass: "text-amber-300",
        dotClass: "bg-amber-400",
        pulse: true,
      };
    }

    if (isDemo) {
      return {
        icon: Wifi,
        label: "DEMO MODE",
        bgClass: "bg-amber-500/20 border-amber-500/50",
        textClass: "text-amber-400",
        dotClass: "bg-amber-400",
        pulse: false,
      };
    }

    switch (connectionStatus) {
      case "connected":
        return {
          icon: Wifi,
          label: "PFC 50 LIVE",
          bgClass: "bg-green-500/20 border-green-500/50",
          textClass: "text-green-400",
          dotClass: "bg-green-400",
          pulse: true,
        };
      case "disconnected":
        return {
          icon: WifiOff,
          label: "DISCONNECTED",
          bgClass: "bg-red-500/20 border-red-500/50",
          textClass: "text-red-400",
          dotClass: "bg-red-500",
          pulse: false,
        };
      case "error":
        return {
          icon: AlertTriangle,
          label: "ERROR",
          bgClass: "bg-red-500/20 border-red-500/50",
          textClass: "text-red-400",
          dotClass: "bg-red-500",
          pulse: false,
        };
      default:
        return {
          icon: WifiOff,
          label: "STANDBY",
          bgClass: "bg-gray-500/50 border-gray-600",
          textClass: "text-gray-400",
          dotClass: "bg-gray-500",
          pulse: false,
        };
    }
  };

  const config = getStatusConfig();
  const Icon = config.icon;

  return (
    <div
      className={`fixed top-4 right-4 z-50 flex items-center gap-2 px-3 py-1.5 rounded-full border backdrop-blur-sm ${config.bgClass}`}
    >
      <span className="relative flex h-2.5 w-2.5">
        {config.pulse && (
          <span
            className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${config.dotClass}`}
          />
        )}
        <span
          className={`relative inline-flex rounded-full h-2.5 w-2.5 ${config.dotClass}`}
        />
      </span>
      <Icon className={`w-3.5 h-3.5 ${config.textClass}`} />
      <span className={`text-xs font-semibold tracking-wide ${config.textClass}`}>
        {config.label}
      </span>
      {boutId && !isDemo && !isOverride && connectionStatus === "connected" && (
        <span className="text-xs text-gray-500 font-mono">
          [{boutId.slice(0, 8)}]
        </span>
      )}
    </div>
  );
});
