import React from "react";
import { Users, Gauge, Wind, ShieldAlert, Video, Eye, Radio } from "lucide-react";
import StatCard from "../components/StatCard";
import { API_BASE_URL } from "../config";

export default function LiveVideo({ densityData, isConnected }) {
  const getRiskBadge = (risk) => {
    const r = (risk || "Low").toLowerCase();
    let badgeClass = "badge-risk low";
    if (r === "high") badgeClass = "badge-risk high";
    else if (r === "medium") badgeClass = "badge-risk medium";

    return (
      <span className={badgeClass}>
        <ShieldAlert size={14} />
        {risk || "Unknown"} Risk
      </span>
    );
  };

  return (
    <div className="page-content">
      <div className="page-header">
        <div>
          <h1>Live Video Surveillance Feed</h1>
          <p>Real-time optical CCTV surveillance, crowd count, and motion analysis</p>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <span style={{ 
            display: "inline-flex", 
            alignItems: "center", 
            gap: "6px",
            background: "#1e293b", 
            padding: "6px 12px", 
            borderRadius: "6px", 
            fontSize: "13px",
            color: "#94a3b8" 
          }}>
            <Radio size={14} color="#10b981" />
            Camera 01 - Concourse
          </span>
          <span style={{ fontSize: "12px", color: "var(--text-dim)" }}>
            Updated: {densityData?.ts || "--:--:--"}
          </span>
        </div>
      </div>

      {/* Metric Cards Row */}
      <div className="stats-grid">
        <StatCard
          title="People Count"
          value={densityData ? densityData.count : "--"}
          unit="persons"
          icon={Users}
          iconColor="#38bdf8"
          footer="Spatial density estimation"
        />

        <StatCard
          title="Average Speed"
          value={densityData ? densityData.speed : "--"}
          unit="m/s"
          icon={Gauge}
          iconColor="#a855f7"
          footer="Optical flow displacement"
        />

        <StatCard
          title="Turbulence Index"
          value={densityData ? densityData.turb : "--"}
          unit=""
          icon={Wind}
          iconColor="#f59e0b"
          footer={densityData?.turb >= 2.0 ? "⚠️ High chaos/turbulence" : "Normal crowd laminar flow"}
        />

        <StatCard
          title="Stampede Risk Level"
          badge={getRiskBadge(densityData?.risk)}
          icon={ShieldAlert}
          iconColor={densityData?.risk === "High" ? "#ef4444" : densityData?.risk === "Medium" ? "#f59e0b" : "#10b981"}
          footer={
            densityData?.risk === "High"
              ? "Immediate intervention required"
              : densityData?.risk === "Medium"
              ? "Elevated compression; observe bottlenecks"
              : "Safe movement parameters"
          }
        />
      </div>

      {/* Video Feed Card */}
      <div className="video-card">
        <div className="video-card-header">
          <div className="video-title-wrap">
            <Video size={18} color="#38bdf8" />
            <strong style={{ fontSize: "14px" }}>CAM-01 [STADIUM / CONCOURSE PLAZA]</strong>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "12px", fontSize: "12px", color: "var(--text-dim)" }}>
            <span>Stream: MJPEG / 640x480</span>
            <span style={{ color: "#10b981", fontWeight: 600 }}>● LIVE</span>
          </div>
        </div>

        <div className="video-frame-wrap">
          {isConnected ? (
            <img
              src={`${API_BASE_URL}/video_feed`}
              alt="Live Video Feed"
              className="feed-img"
              onError={(e) => {
                e.target.style.display = "none";
              }}
            />
          ) : (
            <div className="feed-offline">
              <Eye size={42} color="#64748b" />
              <h3>Video Feed Unavailable</h3>
              <p>Waiting for backend server at {API_BASE_URL}...</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
