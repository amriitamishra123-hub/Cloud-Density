import React, { useState, useEffect, useCallback } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Sidebar from "./components/Sidebar";
import WarningBanner from "./components/WarningBanner";
import LiveVideo from "./pages/LiveVideo";
import DensityMap from "./pages/DensityMap";
import Alerts from "./pages/Alerts";
import { API_BASE_URL, POLL_INTERVAL_MS } from "./config";

export default function App() {
  const [densityData, setDensityData] = useState(null);
  const [history, setHistory] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [isConnected, setIsConnected] = useState(false);
  const [lastFetchTime, setLastFetchTime] = useState(null);

  // Fetch /density, /history, /alerts
  const fetchData = useCallback(async () => {
    try {
      // 1. Fetch latest density reading
      const densityRes = await fetch(`${API_BASE_URL}/density`, { signal: AbortSignal.timeout(3000) });
      if (!densityRes.ok) throw new Error(`HTTP ${densityRes.status}`);
      const densityJson = await densityRes.json();
      setDensityData(densityJson);

      // 2. Fetch history
      const historyRes = await fetch(`${API_BASE_URL}/history`, { signal: AbortSignal.timeout(3000) });
      if (historyRes.ok) {
        const historyJson = await historyRes.json();
        setHistory(historyJson);
      }

      // 3. Fetch alerts
      const alertsRes = await fetch(`${API_BASE_URL}/alerts`, { signal: AbortSignal.timeout(3000) });
      if (alertsRes.ok) {
        const alertsJson = await alertsRes.json();
        setAlerts(alertsJson);
      }

      setIsConnected(true);
      setLastFetchTime(new Date());
    } catch (err) {
      console.warn("API poll failed:", err.message);
      setIsConnected(false);
    }
  }, []);

  // Polling loop every 2 seconds
  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [fetchData]);

  const isHighRisk = (densityData?.risk || "").toUpperCase() === "HIGH";

  return (
    <BrowserRouter>
      <div className="app-container">
        {/* Persistent Navigation Sidebar */}
        <Sidebar 
          isConnected={isConnected} 
          currentRisk={densityData?.risk} 
        />

        {/* Main Content Area */}
        <div className="main-wrapper">
          {/* Full-width Red Warning Banner (shown on all pages when High Risk) */}
          <WarningBanner
            isHighRisk={isHighRisk}
            isConnected={isConnected}
            densityData={densityData}
          />

          <Routes>
            <Route 
              path="/" 
              element={
                <LiveVideo 
                  densityData={densityData} 
                  isConnected={isConnected} 
                />
              } 
            />
            <Route 
              path="/density-map" 
              element={
                <DensityMap 
                  history={history} 
                  isConnected={isConnected} 
                />
              } 
            />
            <Route 
              path="/alerts" 
              element={
                <Alerts 
                  alerts={alerts} 
                  onRefresh={fetchData} 
                  isConnected={isConnected} 
                />
              } 
            />
            {/* Catch-all redirect to live feed */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </div>
      </div>
    </BrowserRouter>
  );
}
