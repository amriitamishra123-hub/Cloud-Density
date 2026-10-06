"""
Mock Backend for Crowd Density & Stampede Risk Prediction System.
Provides simulated real-time data, history, alerts, and mock MJPEG video streams.
Used in Phase 1 for frontend testing and as fallback.
"""

import io
import time
import math
import random
from datetime import datetime
from collections import deque
from typing import List, Dict, Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from PIL import Image, ImageDraw, ImageFont

# ----------------- Configuration -----------------
PORT = 8000
HOST = "0.0.0.0"
MAX_HISTORY = 120
LOW_T = 50
HIGH_T = 150
TURB_T = 2.0

app = FastAPI(
    title="Crowd Density & Stampede Risk API (Mock Mode)",
    description="Simulated backend providing real-time crowd metrics and MJPEG video feeds",
    version="1.0.0"
)

# Enable CORS for all origins so React Vite can connect seamlessly
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------- In-Memory State & History -----------------
history_lock = False

# Risk rule evaluation helper
def compute_rule_risk(count: float, turb: float) -> str:
    """Computes risk category based on crowd count and turbulence."""
    if count < LOW_T:
        base = 0  # Low
    elif count < HIGH_T:
        base = 1  # Medium
    else:
        base = 2  # High

    # High turbulence elevates the risk level by one notch
    if turb >= TURB_T and base < 2:
        base += 1

    levels = ["Low", "Medium", "High"]
    return levels[base]

# Initialize state
current_state = {
    "count": 78,
    "speed": 1.85,
    "turb": 0.85,
    "risk": "Medium",
    "ts": datetime.now().strftime("%H:%M:%S")
}

history: deque = deque(maxlen=MAX_HISTORY)
alerts: List[Dict[str, Any]] = []
last_alert_time = 0.0

# Prepopulate history with realistic rolling data points
base_time = time.time() - (MAX_HISTORY * 2)
sim_count = 65.0
for i in range(MAX_HISTORY):
    t_val = base_time + (i * 2)
    t_str = datetime.fromtimestamp(t_val).strftime("%H:%M:%S")
    # Sine wave plus random walk for natural crowd fluctuations
    wave = math.sin(i * 0.12) * 35
    sim_count = max(20.0, min(195.0, 75.0 + wave + random.uniform(-6, 6)))
    sim_speed = max(0.4, min(4.5, 2.2 - (sim_count / 140.0) + random.uniform(-0.25, 0.25)))
    sim_turb = max(0.1, min(3.5, 0.4 + (sim_count / 90.0) * random.uniform(0.6, 1.3)))
    sim_risk = compute_rule_risk(sim_count, sim_turb)
    
    point = {
        "ts": t_str,
        "count": round(sim_count),
        "speed": round(sim_speed, 2),
        "turb": round(sim_turb, 2),
        "risk": sim_risk
    }
    history.append(point)

# Seed initial realistic alerts
alerts = [
    {
        "time": datetime.fromtimestamp(time.time() - 320).strftime("%H:%M:%S"),
        "risk": "High",
        "count": 168,
        "msg": "High crowd compression & abnormal turbulence detected near Gate 3."
    },
    {
        "time": datetime.fromtimestamp(time.time() - 740).strftime("%H:%M:%S"),
        "risk": "Medium",
        "count": 114,
        "msg": "Crowd gathering pace increasing in central concourse corridor."
    },
    {
        "time": datetime.fromtimestamp(time.time() - 1200).strftime("%H:%M:%S"),
        "risk": "Low",
        "count": 42,
        "msg": "Flow normalized across all monitored camera zones."
    }
]

def update_mock_metrics():
    """Generates next continuous step in mock simulation."""
    global current_state, last_alert_time
    now = time.time()
    now_str = datetime.now().strftime("%H:%M:%S")

    # Gentle random walk
    prev_count = current_state["count"]
    delta = random.choice([-8, -5, -2, 0, 3, 6, 9])
    # Occasionally trigger high surges
    if random.random() < 0.15:
        delta += random.randint(15, 30)
    elif prev_count > 165 and random.random() < 0.5:
        delta -= random.randint(15, 25)

    new_count = int(max(25, min(210, prev_count + delta)))
    # Speed decreases as crowd gets denser
    new_speed = round(max(0.3, min(4.2, 2.4 - (new_count / 150.0) + random.uniform(-0.2, 0.2))), 2)
    # Turbulence spikes when crowd is dense and moving erratically
    new_turb = round(max(0.2, min(3.8, (new_count / 110.0) + random.uniform(-0.3, 0.5))), 2)
    new_risk = compute_rule_risk(new_count, new_turb)

    current_state = {
        "count": new_count,
        "speed": new_speed,
        "turb": new_turb,
        "risk": new_risk,
        "ts": now_str
    }

    # Record in history if last reading is different or every 2 seconds
    if not history or history[-1]["ts"] != now_str:
        history.append(dict(current_state))

    # Add alert if High risk and at least 10 seconds since last alert
    if new_risk == "High" and (now - last_alert_time > 10.0):
        last_alert_time = now
        alerts.insert(0, {
            "time": now_str,
            "risk": "High",
            "count": new_count,
            "msg": f"CRITICAL: Crowd density reached {new_count} persons with turbulence {new_turb}! Stampede hazard."
        })
        # Keep alerts list reasonable in memory
        if len(alerts) > 50:
            alerts.pop()
    elif new_risk == "Medium" and (now - last_alert_time > 45.0) and random.random() < 0.3:
        last_alert_time = now
        alerts.insert(0, {
            "time": now_str,
            "risk": "Medium",
            "count": new_count,
            "msg": f"Advisory: Crowd density climbing ({new_count} persons). Monitoring bottleneck flow."
        })
        if len(alerts) > 50:
            alerts.pop()


# ----------------- Mock Frame Generators -----------------
# Keep track of simulated crowd particles for animated video
num_particles = 45
particles = [
    {
        "x": random.uniform(80, 560),
        "y": random.uniform(100, 420),
        "vx": random.uniform(-2, 2),
        "vy": random.uniform(-1.5, 1.5)
    }
    for _ in range(num_particles)
]

def generate_mock_video_frame() -> bytes:
    """Creates a 640x480 simulated surveillance video frame with bounding boxes and overlays."""
    img = Image.new("RGB", (640, 480), color=(18, 24, 38))
    draw = ImageDraw.Draw(img)

    # Perspective grid lines for CCTV surveillance look
    for x in range(0, 641, 64):
        draw.line([(x, 140), (int(x * 1.3 - 96), 480)], fill=(32, 44, 66), width=1)
    for y in range(140, 481, 40):
        draw.line([(0, y), (640, y)], fill=(30, 42, 62), width=1)

    # Animate simulated crowd particles
    for p in particles:
        p["x"] += p["vx"]
        p["y"] += p["vy"]
        if p["x"] < 50 or p["x"] > 590:
            p["vx"] *= -1
        if p["y"] < 130 or p["y"] > 440:
            p["vy"] *= -1

        # Draw person figure / box
        px, py = int(p["x"]), int(p["y"])
        # Head
        draw.ellipse([px - 4, py - 14, px + 4, py - 6], fill=(56, 189, 248), outline=(14, 165, 233))
        # Bounding box
        draw.rectangle([px - 10, py - 6, px + 10, py + 22], outline=(34, 197, 94), width=1)
        # Bounding label
        draw.text((px - 10, py - 20), "person", fill=(34, 197, 94))

    # Dark HUD overlay bar at top
    draw.rectangle([0, 0, 640, 46], fill=(10, 15, 26))
    draw.line([(0, 46), (640, 46)], fill=(51, 65, 85), width=2)

    # REC blinking indicator
    blink = int(time.time() * 2) % 2 == 0
    rec_col = (239, 68, 68) if blink else (120, 20, 20)
    draw.ellipse([16, 16, 28, 28], fill=rec_col)
    draw.text((36, 14), "REC  •  LIVE FEED  •  CAM-01 [MAIN GATE]", fill=(226, 232, 240))

    # Timestamp in top right
    cur_time = datetime.now().strftime("%Y-%m-%d  %H:%M:%S")
    draw.text((450, 14), cur_time, fill=(148, 163, 184))

    # Large MOCK Banner in center
    draw.rectangle([210, 215, 430, 275], fill=(15, 23, 42, 220), outline=(245, 158, 11), width=2)
    draw.text((250, 230), "[ MOCK VIDEO FEED ]", fill=(251, 191, 36))
    draw.text((230, 250), "Simulated CCTV Video Stream", fill=(148, 163, 184))

    # Bottom info status bar
    draw.rectangle([0, 444, 640, 480], fill=(10, 15, 26))
    status_text = f"Count: {current_state['count']} | Speed: {current_state['speed']}m/s | Turb: {current_state['turb']} | Risk: {current_state['risk']}"
    draw.text((16, 452), status_text, fill=(203, 213, 225))

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=75)
    return buf.getvalue()


def generate_mock_heatmap_frame() -> bytes:
    """Creates a 640x480 thermal / density heatmap placeholder frame."""
    img = Image.new("RGB", (640, 480), color=(10, 14, 28))
    draw = ImageDraw.Draw(img)

    # Simulated heatmap blobs around particles
    t_val = time.time()
    for i, p in enumerate(particles):
        px, py = int(p["x"]), int(p["y"])
        # Pulsing radius
        radius = int(22 + 10 * math.sin(t_val * 2 + i))
        # Color gradient mock
        if i % 3 == 0:
            color = (239, 68, 68)   # Red (high density hotspot)
        elif i % 2 == 0:
            color = (245, 158, 11)  # Amber (medium)
        else:
            color = (14, 165, 233)  # Cyan/Blue (low)
        draw.ellipse([px - radius, py - radius, px + radius, py + radius], outline=color, width=2)

    # Dark HUD overlay bar at top
    draw.rectangle([0, 0, 640, 46], fill=(10, 15, 26))
    draw.line([(0, 46), (640, 46)], fill=(51, 65, 85), width=2)
    draw.text((16, 14), "DENSITY HEATMAP  •  CSRNet ESTIMATION", fill=(226, 232, 240))
    cur_time = datetime.now().strftime("%Y-%m-%d  %H:%M:%S")
    draw.text((450, 14), cur_time, fill=(148, 163, 184))

    # Center banner
    draw.rectangle([190, 215, 450, 275], fill=(15, 23, 42), outline=(168, 85, 247), width=2)
    draw.text((225, 230), "[ MOCK DENSITY HEATMAP ]", fill=(192, 132, 252))
    draw.text((230, 250), "Simulated Spatial Density Map", fill=(148, 163, 184))

    # Color bar legend at bottom
    draw.rectangle([0, 444, 640, 480], fill=(10, 15, 26))
    draw.text((16, 452), "Low Density", fill=(56, 189, 248))
    # Draw mini gradient bar
    for x in range(120, 320):
        ratio = (x - 120) / 200.0
        r = int(255 * ratio)
        g = int(255 * (1 - abs(ratio - 0.5) * 2))
        b = int(255 * (1 - ratio))
        draw.line([(x, 454), (x, 468)], fill=(r, g, b))
    draw.text((330, 452), "High Density / Chokepoint", fill=(239, 68, 68))

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=75)
    return buf.getvalue()


# ----------------- API Endpoints -----------------

@app.get("/")
def root():
    return {
        "status": "online",
        "system": "Crowd Density & Stampede Risk Prediction System",
        "mode": "mock",
        "version": "1.0.0"
    }

@app.get("/density")
def get_density():
    """
    Returns latest live crowd density metrics.
    Shape: {count, speed, turb, risk, ts}
    """
    update_mock_metrics()
    return current_state

@app.get("/risk")
def get_risk():
    """Returns risk assessment."""
    update_mock_metrics()
    return {
        "risk": current_state["risk"],
        "count": current_state["count"],
        "speed": current_state["speed"],
        "turb": current_state["turb"],
        "timestamp": current_state["ts"]
    }

@app.get("/history")
def get_history():
    """
    Returns list of the last 120 readings for line chart plotting.
    """
    return list(history)

@app.get("/alerts")
def get_alerts():
    """
    Returns list of recent alerts, newest first.
    Shape: list of {time, risk, count, msg}
    """
    return alerts

@app.get("/status")
def get_status():
    """
    Returns system status metrics (for Phase 5 dashboard card).
    """
    return {
        "model_loaded": False,
        "mode": "mock",
        "fps": 12.5,
        "active_camera": "CAM-01 [Main Gate Concourse]",
        "total_alerts": len(alerts)
    }

@app.get("/video_feed")
def video_feed():
    """MJPEG stream for simulated live video feed."""
    def frame_stream():
        while True:
            frame = generate_mock_video_frame()
            yield (b"--frame\r\n"
                   b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")
            time.sleep(0.08)  # ~12 FPS

    return StreamingResponse(
        frame_stream(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

@app.get("/heatmap_feed")
def heatmap_feed():
    """MJPEG stream for simulated density heatmap."""
    def frame_stream():
        while True:
            frame = generate_mock_heatmap_frame()
            yield (b"--frame\r\n"
                   b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")
            time.sleep(0.08)  # ~12 FPS

    return StreamingResponse(
        frame_stream(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("mock_main:app", host=HOST, port=PORT, reload=False)
