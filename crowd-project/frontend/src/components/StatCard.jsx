import React from "react";

export default function StatCard({ title, value, unit = "", icon: Icon, badge, footer, iconColor = "#38bdf8" }) {
  return (
    <div className="stat-card">
      <div className="stat-header">
        <span>{title}</span>
        {Icon && <Icon size={18} color={iconColor} />}
      </div>
      <div style={{ display: "flex", alignItems: "baseline", gap: "6px" }}>
        {badge ? (
          badge
        ) : (
          <>
            <div className="stat-value">{value !== undefined && value !== null ? value : "--"}</div>
            {unit && <span style={{ fontSize: "14px", color: "var(--text-muted)", fontWeight: 600 }}>{unit}</span>}
          </>
        )}
      </div>
      {footer && <div className="stat-footer">{footer}</div>}
    </div>
  );
}
