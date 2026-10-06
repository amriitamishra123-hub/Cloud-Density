import React from "react";
import { NavLink } from "react-router-dom";
import { Video, Activity, AlertTriangle } from "lucide-react";

export default function Sidebar({ isConnected, currentRisk }) {
  const getRiskColor = (risk) => {
    switch (risk) {
      case "High": return "#ef4444";
      case "Medium": return "#f59e0b";
      default: return "#10b981";
    }
  };

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <span className="brand-badge">AI Surveillance</span>
        <h2 className="sidebar-title">Crowd Density & Stampede Risk</h2>
        <p className="sidebar-subtitle">Prediction & Early Warning System</p>
      </div>

      <nav className="sidebar-nav">
        <NavLink 
          to="/" 
          end
          className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}
        >
          <Video size={18} />
          <span>Live Video Feed</span>
        </NavLink>

        <NavLink 
          to="/density-map" 
          className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}
        >
          <Activity size={18} />
          <span>Density Map & Trends</span>
        </NavLink>

        <NavLink 
          to="/alerts" 
          className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}
        >
          <AlertTriangle size={18} />
          <span>Alerts Log</span>
        </NavLink>
      </nav>

      <div className="sidebar-footer">
        <div style={{ marginBottom: "12px" }}>
          <div style={{ fontSize: "11px", color: "var(--text-dim)", textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: "4px" }}>
            Current Threat Level
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <span style={{ 
              width: "10px", 
              height: "10px", 
              borderRadius: "50%", 
              backgroundColor: getRiskColor(currentRisk),
              boxShadow: `0 0 10px ${getRiskColor(currentRisk)}`
            }} />
            <strong style={{ color: getRiskColor(currentRisk), fontSize: "14px" }}>
              {currentRisk ? `${currentRisk} Risk` : "Analyzing..."}
            </strong>
          </div>
        </div>

        <div className="status-pill">
          <span className={`dot ${isConnected ? "online" : "offline"}`} />
          <span>{isConnected ? "Backend Connected (FastAPI)" : "Connecting to Backend..."}</span>
        </div>
      </div>
    </aside>
  );
}
