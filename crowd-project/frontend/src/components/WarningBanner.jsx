import React from "react";
import { AlertOctagon, WifiOff } from "lucide-react";

export default function WarningBanner({ isHighRisk, isConnected, densityData }) {
  return (
    <>
      {/* High Stampede Risk Alert Banner */}
      {isHighRisk && (
        <div className="high-risk-banner" role="alert">
          <div className="banner-content">
            <AlertOctagon size={24} color="#fff" />
            <div>
              <div className="banner-title">
                ⚠️ CRITICAL STAMPEDE HAZARD DETECTED
              </div>
              <div className="banner-desc">
                High crowd compression ({densityData?.count || "High"} individuals) and turbulence level ({densityData?.turb || "Spike"}) detected! Deploy emergency marshals immediately.
              </div>
            </div>
          </div>
          <div style={{ display: "flex", gap: "8px" }}>
            <span style={{ 
              background: "rgba(0,0,0,0.3)", 
              padding: "4px 10px", 
              borderRadius: "4px", 
              fontSize: "12px", 
              fontWeight: 700 
            }}>
              TRIGGERED AT {densityData?.ts || "NOW"}
            </span>
          </div>
        </div>
      )}

      {/* Backend Disconnected Banner */}
      {!isConnected && (
        <div className="offline-banner">
          <WifiOff size={18} />
          <span>
            <strong>Backend Connection Offline:</strong> Unable to connect to API at port 8000. Polling automatically every 2 seconds. Ensure <code>python mock_main.py</code> (or <code>main.py</code>) is running.
          </span>
        </div>
      )}
    </>
  );
}
