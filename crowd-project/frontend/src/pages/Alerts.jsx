import React, { useState } from "react";
import { AlertTriangle, ShieldAlert, CheckCircle2, Filter, RefreshCw } from "lucide-react";

export default function Alerts({ alerts, onRefresh, isConnected }) {
  const [filter, setFilter] = useState("ALL");

  const filteredAlerts = (alerts || []).filter((a) => {
    if (filter === "ALL") return true;
    return (a.risk || "").toUpperCase() === filter;
  });

  const getRiskBadge = (risk) => {
    const r = (risk || "Low").toLowerCase();
    let badgeClass = "badge-risk low";
    if (r === "high") badgeClass = "badge-risk high";
    else if (r === "medium") badgeClass = "badge-risk medium";

    return (
      <span className={badgeClass}>
        {risk || "Unknown"}
      </span>
    );
  };

  const highCount = (alerts || []).filter(a => (a.risk || "").toUpperCase() === "HIGH").length;
  const medCount = (alerts || []).filter(a => (a.risk || "").toUpperCase() === "MEDIUM").length;
  const lowCount = (alerts || []).filter(a => (a.risk || "").toUpperCase() === "LOW").length;

  return (
    <div className="page-content">
      <div className="page-header">
        <div>
          <h1>Stampede Risk Alerts & Incident Log</h1>
          <p>Automated hazard event log captured by AI crowd monitoring and threshold breach detection</p>
        </div>
        <div>
          <button className="btn" onClick={onRefresh}>
            <RefreshCw size={14} />
            Refresh Log
          </button>
        </div>
      </div>

      {/* Mini metric counters */}
      <div className="stats-grid" style={{ marginBottom: "20px" }}>
        <div className="stat-card" style={{ borderLeft: "4px solid #ef4444" }}>
          <div className="stat-header">
            <span>Critical Incidents</span>
            <AlertTriangle size={18} color="#ef4444" />
          </div>
          <div className="stat-value" style={{ color: "#ef4444" }}>{highCount}</div>
          <div className="stat-footer">High risk stampede hazards</div>
        </div>

        <div className="stat-card" style={{ borderLeft: "4px solid #f59e0b" }}>
          <div className="stat-header">
            <span>Elevated Warnings</span>
            <AlertTriangle size={18} color="#f59e0b" />
          </div>
          <div className="stat-value" style={{ color: "#f59e0b" }}>{medCount}</div>
          <div className="stat-footer">Bottleneck / surge advisories</div>
        </div>

        <div className="stat-card" style={{ borderLeft: "4px solid #10b981" }}>
          <div className="stat-header">
            <span>Normal Informational</span>
            <CheckCircle2 size={18} color="#10b981" />
          </div>
          <div className="stat-value" style={{ color: "#10b981" }}>{lowCount}</div>
          <div className="stat-footer">Flow stabilization logs</div>
        </div>
      </div>

      {/* Table Card */}
      <div className="table-card">
        <div className="table-header-tools">
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <Filter size={16} color="var(--text-muted)" />
            <span style={{ fontSize: "13px", fontWeight: 600 }}>Filter by Severity:</span>
            <div className="filter-btn-group">
              <button 
                className={`btn-filter ${filter === "ALL" ? "active" : ""}`}
                onClick={() => setFilter("ALL")}
              >
                All ({alerts.length})
              </button>
              <button 
                className={`btn-filter ${filter === "HIGH" ? "active" : ""}`}
                onClick={() => setFilter("HIGH")}
              >
                High ({highCount})
              </button>
              <button 
                className={`btn-filter ${filter === "MEDIUM" ? "active" : ""}`}
                onClick={() => setFilter("MEDIUM")}
              >
                Medium ({medCount})
              </button>
              <button 
                className={`btn-filter ${filter === "LOW" ? "active" : ""}`}
                onClick={() => setFilter("LOW")}
              >
                Low ({lowCount})
              </button>
            </div>
          </div>

          <div style={{ fontSize: "12px", color: "var(--text-dim)" }}>
            Auto-refresh active (2s interval)
          </div>
        </div>

        <div style={{ overflowX: "auto" }}>
          <table className="custom-table">
            <thead>
              <tr>
                <th style={{ width: "120px" }}>Time</th>
                <th style={{ width: "140px" }}>Risk Level</th>
                <th style={{ width: "120px" }}>Density (Count)</th>
                <th>Alert Description & Operational Guidance</th>
              </tr>
            </thead>
            <tbody>
              {filteredAlerts.length > 0 ? (
                filteredAlerts.map((alert, idx) => (
                  <tr key={idx}>
                    <td style={{ fontFamily: "monospace", color: "var(--text-muted)" }}>
                      {alert.time || "--:--:--"}
                    </td>
                    <td>{getRiskBadge(alert.risk)}</td>
                    <td>
                      <strong style={{ color: "#38bdf8" }}>{alert.count}</strong>
                      <span style={{ fontSize: "11px", color: "var(--text-dim)", marginLeft: "4px" }}>people</span>
                    </td>
                    <td style={{ color: alert.risk === "High" ? "#fca5a5" : "var(--text-main)" }}>
                      {alert.msg}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={4} style={{ textAlign: "center", padding: "40px 20px", color: "var(--text-muted)" }}>
                    No alerts found for selected severity filter.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
