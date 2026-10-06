import React from "react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ReferenceLine
} from "recharts";
import { Flame, TrendingUp, Info } from "lucide-react";
import { API_BASE_URL } from "../config";

export default function DensityMap({ history, isConnected }) {
  // Compute basic stats from history
  const counts = (history || []).map((h) => h.count || 0);
  const peakCount = counts.length > 0 ? Math.max(...counts) : 0;
  const minCount = counts.length > 0 ? Math.min(...counts) : 0;
  const avgCount = counts.length > 0 ? Math.round(counts.reduce((a, b) => a + b, 0) / counts.length) : 0;

  // Custom chart tooltip
  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div style={{
          backgroundColor: "#0f172a",
          border: "1px solid #334155",
          padding: "10px 14px",
          borderRadius: "8px",
          boxShadow: "0 10px 25px -5px rgba(0, 0, 0, 0.5)",
          color: "#fff",
          fontSize: "12px"
        }}>
          <p style={{ fontWeight: 700, color: "#94a3b8", marginBottom: "4px" }}>Time: {label}</p>
          <p style={{ color: "#38bdf8", fontWeight: 600 }}>Count: {data.count} persons</p>
          <p style={{ color: "#a855f7" }}>Speed: {data.speed} m/s</p>
          <p style={{ color: "#f59e0b" }}>Turbulence: {data.turb}</p>
          <p style={{ 
            marginTop: "4px", 
            fontWeight: 700,
            color: data.risk === "High" ? "#ef4444" : data.risk === "Medium" ? "#f59e0b" : "#10b981" 
          }}>
            Risk: {data.risk}
          </p>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="page-content">
      <div className="page-header">
        <div>
          <h1>Density Map & Temporal Trends</h1>
          <p>Spatial crowd distribution heatmap and 120-second rolling density history</p>
        </div>
        <div style={{ display: "flex", gap: "16px" }}>
          <div style={{ fontSize: "12px", color: "var(--text-muted)", textAlign: "right" }}>
            <div>Historical Buffer: <strong>{history.length} samples</strong></div>
            <div>Peak in window: <strong style={{ color: "#ef4444" }}>{peakCount} persons</strong></div>
          </div>
        </div>
      </div>

      {/* Heatmap Stream Card */}
      <div className="video-card">
        <div className="video-card-header">
          <div className="video-title-wrap">
            <Flame size={18} color="#f59e0b" />
            <strong style={{ fontSize: "14px" }}>SPATIAL CROWD DENSITY HEATMAP (JET COLORMAP)</strong>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "12px", color: "var(--text-dim)" }}>
            <span>Model: CSRNet Density Map</span>
          </div>
        </div>

        <div className="video-frame-wrap">
          {isConnected ? (
            <img
              src={`${API_BASE_URL}/heatmap_feed`}
              alt="Crowd Density Heatmap"
              className="feed-img"
              onError={(e) => {
                e.target.style.display = "none";
              }}
            />
          ) : (
            <div className="feed-offline">
              <Flame size={42} color="#64748b" />
              <h3>Heatmap Stream Unavailable</h3>
              <p>Waiting for backend connection at {API_BASE_URL}...</p>
            </div>
          )}
        </div>
      </div>

      {/* Recharts Line Chart Card */}
      <div className="chart-card">
        <div className="chart-header">
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <TrendingUp size={18} color="#38bdf8" />
            <h3>Crowd Count Trend (Last 120 Readings)</h3>
          </div>

          <div className="chart-legend">
            <div className="legend-item">
              <div className="legend-indicator" style={{ backgroundColor: "#38bdf8" }} />
              <span>People Count</span>
            </div>
            <div className="legend-item">
              <div className="legend-indicator" style={{ backgroundColor: "#f59e0b" }} />
              <span>Medium Threshold (50)</span>
            </div>
            <div className="legend-item">
              <div className="legend-indicator" style={{ backgroundColor: "#ef4444" }} />
              <span>Critical Threshold (150)</span>
            </div>
          </div>
        </div>

        <div style={{ width: "100%", height: 320 }}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={history} margin={{ top: 10, right: 30, left: -10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis 
                dataKey="ts" 
                stroke="#64748b" 
                tick={{ fontSize: 11 }} 
                interval="preserveStartEnd" 
                minTickGap={25}
              />
              <YAxis 
                stroke="#64748b" 
                tick={{ fontSize: 11 }}
                domain={[0, (dataMax) => Math.max(180, Math.ceil(dataMax * 1.15))]}
              />
              <Tooltip content={<CustomTooltip />} />
              
              {/* Threshold guidelines */}
              <ReferenceLine y={50} stroke="#f59e0b" strokeDasharray="4 4" label={{ value: "Medium (50)", fill: "#f59e0b", fontSize: 11, position: "insideTopRight" }} />
              <ReferenceLine y={150} stroke="#ef4444" strokeDasharray="4 4" label={{ value: "High / Stampede Risk (150)", fill: "#ef4444", fontSize: 11, position: "insideTopRight" }} />

              <Line
                type="monotone"
                dataKey="count"
                stroke="#38bdf8"
                strokeWidth={2.5}
                dot={false}
                activeDot={{ r: 6, fill: "#38bdf8", stroke: "#0f172a", strokeWidth: 2 }}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Metric summary footer */}
        <div style={{ 
          marginTop: "16px", 
          paddingTop: "14px", 
          borderTop: "1px solid var(--border-color)",
          display: "flex", 
          gap: "24px",
          flexWrap: "wrap",
          fontSize: "13px",
          color: "var(--text-muted)"
        }}>
          <div>Average: <strong style={{ color: "#fff" }}>{avgCount}</strong></div>
          <div>Minimum: <strong style={{ color: "#fff" }}>{minCount}</strong></div>
          <div>Maximum: <strong style={{ color: "#ef4444" }}>{peakCount}</strong></div>
          <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: "6px", color: "var(--text-dim)", fontSize: "12px" }}>
            <Info size={14} />
            Data points auto-synchronize from <code>/history</code>
          </div>
        </div>
      </div>
    </div>
  );
}
