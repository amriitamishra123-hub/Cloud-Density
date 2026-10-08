"""
Main FastAPI Backend with Real-Time Video & AI Background Processing Worker.
Orchestrates:
  - Video stream reading and continuous looping (data/crowd.mp4)
  - CSRNet crowd density estimation (runs every Nth frame for CPU optimization)
  - Farneback optical flow motion & turbulence tracking
  - Stampede risk evaluation via risk.rule_risk
  - Real-time MJPEG live video and heatmap overlay streaming
  - Automatic fallback to simulated mock streams if weights or video are missing.
"""

import os
import io
import time
import math
import random
import threading
from datetime import datetime
from collections import deque
from contextlib import asynccontextmanager
from typing import List, Dict, Any

import cv2
import numpy as np
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

import csrnet
import flow
import risk

# ================= Configuration Constants =================
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
VIDEO_PATH = os.path.join(BACKEND_DIR, "data", "crowd.mp4")

# Processing interval: analyze every Nth frame (increase to 15 or 20 if CPU lags)
PROCESS_EVERY_N_FRAMES = 10
FRAME_SIZE = (640, 480)

PORT = 8000
HOST = "0.0.0.0"
MAX_HISTORY = 120

# ================= Shared Thread-Safe State =================
state_lock = threading.Lock()

state: Dict[str, Any] = {
    "count": 0,
    "speed": 0.0,
    "turb": 0.0,
    "risk": "Low",
    "ts": datetime.now().strftime("%H:%M:%S")
}

history: deque = deque(maxlen=MAX_HISTORY)
alerts: List[Dict[str, Any]] = []
latest: Dict[str, bytes] = {
    "video": b"",
    "heat": b""
}

stop_worker = False

# Check if real prerequisites are satisfied
video_exists = os.path.isfile(VIDEO_PATH)
weights_loaded = csrnet.WEIGHTS_LOADED
real_mode_active = video_exists and weights_loaded


# ================= Fallback Mock Generator Helpers =================
num_mock_particles = 40
mock_particles = [
    {
        "x": random.uniform(80, 560),
        "y": random.uniform(100, 420),
        "vx": random.uniform(-2, 2),
        "vy": random.uniform(-1.5, 1.5)
    }
    for _ in range(num_mock_particles)
]

def make_fallback_video_frame(cur_state: dict) -> bytes:
    """Creates a simulated 640x480 surveillance frame with particles and HUD."""
    frame = np.full((FRAME_SIZE[1], FRAME_SIZE[0], 3), (25, 20, 15), dtype=np.uint8)

    # Grid lines
    for x in range(0, 641, 64):
        cv2.line(frame, (x, 100), (int(x * 1.2 - 64), 480), (45, 38, 28), 1)
    for y in range(100, 481, 45):
        cv2.line(frame, (0, y), (640, y), (42, 35, 26), 1)

    # Move simulated particles
    for p in mock_particles:
        p["x"] += p["vx"]
        p["y"] += p["vy"]
        if p["x"] < 50 or p["x"] > 590:
            p["vx"] *= -1
        if p["y"] < 110 or p["y"] > 440:
            p["vy"] *= -1

        px, py = int(p["x"]), int(p["y"])
        cv2.circle(frame, (px, py), 5, (230, 180, 50), -1)
        cv2.rectangle(frame, (px - 9, py + 5), (px + 9, py + 24), (50, 180, 50), 1)

    # Top HUD
    cv2.rectangle(frame, (0, 0), (640, 42), (18, 14, 10), -1)
    cv2.putText(frame, "CAM-01 [LIVE] - MAIN CONCOURSE", (15, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (220, 220, 220), 1)
    cv2.putText(frame, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), (440, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (160, 160, 160), 1)

    # Mock Mode Warning
    cv2.rectangle(frame, (200, 210), (440, 270), (25, 20, 15), -1)
    cv2.rectangle(frame, (200, 210), (440, 270), (0, 165, 255), 2)
    cv2.putText(frame, "[ MOCK VIDEO FEED ]", (220, 238), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 200, 255), 2)
    cv2.putText(frame, "Place crowd.mp4 in data/", (224, 258), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 180, 180), 1)

    # Bottom status bar
    cv2.rectangle(frame, (0, 446), (640, 480), (18, 14, 10), -1)
    st_text = f"Count: {cur_state['count']} | Speed: {cur_state['speed']}m/s | Turb: {cur_state['turb']} | Risk: {cur_state['risk']}"
    cv2.putText(frame, st_text, (15, 468), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (200, 200, 200), 1)

    ret, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
    return buf.tobytes() if ret else b""


def make_fallback_heatmap_frame(cur_state: dict) -> bytes:
    """Creates a simulated thermal density heatmap."""
    heat = np.full((FRAME_SIZE[1], FRAME_SIZE[0], 3), (20, 12, 10), dtype=np.uint8)

    t_now = time.time()
    for i, p in enumerate(mock_particles):
        px, py = int(p["x"]), int(p["y"])
        radius = int(22 + 8 * math.sin(t_now * 2 + i))
        color = (0, 0, 240) if i % 3 == 0 else (0, 180, 240) if i % 2 == 0 else (220, 120, 20)
        cv2.circle(heat, (px, py), radius, color, 2)

    cv2.rectangle(heat, (0, 0), (640, 42), (15, 10, 8), -1)
    cv2.putText(heat, "DENSITY HEATMAP - SPATIAL ESTIMATION", (15, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (220, 220, 220), 1)

    cv2.rectangle(heat, (185, 210), (455, 270), (25, 20, 15), -1)
    cv2.rectangle(heat, (185, 210), (455, 270), (180, 80, 240), 2)
    cv2.putText(heat, "[ MOCK DENSITY HEATMAP ]", (205, 238), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (200, 120, 255), 2)
    cv2.putText(heat, "Simulated Density Map", (245, 258), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 180, 180), 1)

    ret, buf = cv2.imencode(".jpg", heat, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
    return buf.tobytes() if ret else b""


def init_mock_seed_data():
    """Initializes history and sample alerts so charts populate on start."""
    base_t = time.time() - (MAX_HISTORY * 2)
    for i in range(MAX_HISTORY):
        t_val = base_t + (i * 2)
        t_str = datetime.fromtimestamp(t_val).strftime("%H:%M:%S")
        wave = math.sin(i * 0.12) * 35
        sim_count = max(25.0, min(190.0, 75.0 + wave + random.uniform(-5, 5)))
        sim_speed = max(0.4, min(4.2, 2.2 - (sim_count / 140.0) + random.uniform(-0.2, 0.2)))
        sim_turb = max(0.1, min(3.2, 0.4 + (sim_count / 90.0) * random.uniform(0.6, 1.2)))
        r_idx = risk.rule_risk(sim_count, sim_turb)
        history.append({
            "ts": t_str,
            "count": round(sim_count),
            "speed": round(sim_speed, 2),
            "turb": round(sim_turb, 2),
            "risk": risk.LABELS[r_idx]
        })

    alerts.extend([
        {
            "time": datetime.fromtimestamp(time.time() - 250).strftime("%H:%M:%S"),
            "risk": "High",
            "count": 164,
            "msg": "High crowd compression & elevated turbulence detected near Concourse Gate 3."
        },
        {
            "time": datetime.fromtimestamp(time.time() - 600).strftime("%H:%M:%S"),
            "risk": "Medium",
            "count": 110,
            "msg": "Crowd density increasing along central plaza corridor."
        },
        {
            "time": datetime.fromtimestamp(time.time() - 1100).strftime("%H:%M:%S"),
            "risk": "Low",
            "count": 44,
            "msg": "Normal crowd movement flow restored."
        }
    ])


# ================= Background Worker =================
def run_real_video_worker():
    """Background worker loop processing real crowd.mp4 with CSRNet & Farneback flow."""
    global state, last_alert_time
    last_alert_time = 0.0
    frame_idx = 0
    prev_gray = None

    print(f"[Worker] Starting REAL video processing worker on: {VIDEO_PATH}")
    print(f"[Worker] CSRNet will analyze every {PROCESS_EVERY_N_FRAMES} frames.")

    while not stop_worker:
        cap = cv2.VideoCapture(VIDEO_PATH)
        if not cap.isOpened():
            print(f"[Worker ERROR] Unable to open video {VIDEO_PATH}. Falling back to mock loop.")
            run_fallback_worker()
            return

        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        frame_interval = 1.0 / fps

        while cap.isOpened() and not stop_worker:
            t_start = time.time()
            ret, frame = cap.read()
            if not ret:
                # Video reached the end -> loop from beginning
                break

            # 1. Resize each frame to FRAME_SIZE (640, 480)
            resized = cv2.resize(frame, FRAME_SIZE, interpolation=cv2.INTER_AREA)

            # 2. Always encode and update latest['video'] for smooth live playback
            ret_vid, vid_bytes = cv2.imencode(".jpg", resized, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
            if ret_vid:
                with state_lock:
                    latest["video"] = vid_bytes.tobytes()

            # 3. Grayscale representation for optical flow
            gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)

            # 4. Process AI on every Nth frame
            frame_idx += 1
            if frame_idx % PROCESS_EVERY_N_FRAMES == 0:
                # Run CSRNet density estimation
                count, density_map = csrnet.predict_density(resized)

                # Compute optical flow motion & turbulence
                if prev_gray is not None:
                    speed, turb = flow.flow_stats(prev_gray, gray)
                else:
                    speed, turb = 0.0, 0.0

                # Compute risk level using rule-based heuristics
                risk_idx = risk.rule_risk(count, turb)
                risk_label = risk.LABELS[risk_idx]
                now_str = datetime.now().strftime("%H:%M:%S")

                # Generate blended heatmap overlay
                heatmap_overlay = flow.overlay(resized, density_map)
                ret_heat, heat_bytes = cv2.imencode(".jpg", heatmap_overlay, [int(cv2.IMWRITE_JPEG_QUALITY), 75])

                with state_lock:
                    state["count"] = round(count)
                    state["speed"] = round(speed, 2)
                    state["turb"] = round(turb, 2)
                    state["risk"] = risk_label
                    state["ts"] = now_str

                    history.append(dict(state))

                    if ret_heat:
                        latest["heat"] = heat_bytes.tobytes()

                    # Add alert when risk is High (at most once every 10 seconds)
                    now_time = time.time()
                    if risk_label == "High" and (now_time - last_alert_time >= 10.0):
                        last_alert_time = now_time
                        alerts.insert(0, {
                            "time": now_str,
                            "risk": "High",
                            "count": round(count),
                            "msg": f"CRITICAL: High crowd density ({round(count)} persons) & turbulence ({round(turb, 2)})! Stampede hazard."
                        })
                        if len(alerts) > 50:
                            alerts.pop()

            # Always update prev_gray on every frame
            prev_gray = gray.copy()

            # Maintain natural video framerate timing
            elapsed = time.time() - t_start
            delay = max(0.001, frame_interval - elapsed)
            time.sleep(delay)

        cap.release()


def run_fallback_worker():
    """Background fallback worker simulating data when video or weights are missing."""
    global state, last_alert_time
    last_alert_time = 0.0
    init_mock_seed_data()

    print("[Worker] Running FALLBACK simulated mock loop.")
    prev_count = 75

    while not stop_worker:
        # Check if video was added while running
        if os.path.isfile(VIDEO_PATH) and csrnet.WEIGHTS_LOADED:
            print("[Worker] Detected crowd.mp4 and weights! Switching to real video worker.")
            run_real_video_worker()
            return

        now_str = datetime.now().strftime("%H:%M:%S")
        delta = random.choice([-6, -3, 0, 3, 5, 8])
        if random.random() < 0.12:
            delta += random.randint(18, 30)
        elif prev_count > 160:
            delta -= random.randint(15, 25)

        new_count = int(max(25, min(205, prev_count + delta)))
        prev_count = new_count
        new_speed = round(max(0.3, min(4.2, 2.4 - (new_count / 150.0) + random.uniform(-0.2, 0.2))), 2)
        new_turb = round(max(0.2, min(3.8, (new_count / 110.0) + random.uniform(-0.3, 0.5))), 2)

        r_idx = risk.rule_risk(new_count, new_turb)
        r_label = risk.LABELS[r_idx]

        with state_lock:
            state["count"] = new_count
            state["speed"] = new_speed
            state["turb"] = new_turb
            state["risk"] = r_label
            state["ts"] = now_str

            history.append(dict(state))

            # Generate placeholder JPEGs
            latest["video"] = make_fallback_video_frame(state)
            latest["heat"] = make_fallback_heatmap_frame(state)

            now_time = time.time()
            if r_label == "High" and (now_time - last_alert_time >= 10.0):
                last_alert_time = now_time
                alerts.insert(0, {
                    "time": now_str,
                    "risk": "High",
                    "count": new_count,
                    "msg": f"CRITICAL: Crowd density reached {new_count} persons with turbulence {new_turb}! Stampede hazard."
                })
                if len(alerts) > 50:
                    alerts.pop()

        time.sleep(1.5)


def worker_entry():
    """Worker dispatcher checking real vs fallback prerequisites."""
    if os.path.isfile(VIDEO_PATH) and csrnet.WEIGHTS_LOADED:
        run_real_video_worker()
    else:
        if not os.path.isfile(VIDEO_PATH):
            print("\n" + "=" * 78)
            print("[Backend NOTICE] Video file not found at:")
            print(f"  Target File : {VIDEO_PATH}")
            print("To enable real video feed analysis:")
            print("  1. Place a recorded CCTV/crowd video named 'crowd.mp4' into backend/data/")
            print("Operating in fallback mock mode so dashboard stays fully interactive.")
            print("=" * 78 + "\n")
        run_fallback_worker()


# ================= FastAPI Application =================
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: spawn video / AI background worker thread
    thread = threading.Thread(target=worker_entry, daemon=True)
    thread.start()
    yield
    # Shutdown
    global stop_worker
    stop_worker = True


app = FastAPI(
    title="Crowd Density & Stampede Risk Prediction System",
    description="Real-time CCTV crowd monitoring, CSRNet density estimation, optical flow, and risk forecasting.",
    version="2.0.0",
    lifespan=lifespan
)

# Enable CORS for all origins so React Vite can connect seamlessly
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ================= API Endpoints =================
@app.get("/")
def root():
    return {
        "status": "online",
        "system": "Crowd Density & Stampede Risk Prediction System",
        "mode": "real" if (os.path.isfile(VIDEO_PATH) and csrnet.WEIGHTS_LOADED) else "mock",
        "version": "2.0.0"
    }


@app.get("/density")
def get_density():
    """
    Returns latest live crowd density metrics.
    Exact shape: {count, speed, turb, risk, ts}
    """
    with state_lock:
        return dict(state)


@app.get("/history")
def get_history():
    """
    Returns list of the last 120 readings for line chart plotting.
    Exact shape: list of {ts, count, speed, turb, risk}
    """
    with state_lock:
        return list(history)


@app.get("/alerts")
def get_alerts():
    """
    Returns list of recent alerts, newest first.
    Exact shape: list of {time, risk, count, msg}
    """
    with state_lock:
        return list(alerts)


@app.get("/status")
def get_status():
    """
    Returns system status metrics.
    Returns: {"mode": "real" or "mock", "weights_loaded": bool, "video_found": bool}
    """
    vid_found = os.path.isfile(VIDEO_PATH)
    w_loaded = bool(csrnet.WEIGHTS_LOADED)
    active_mode = "real" if (vid_found and w_loaded) else "mock"

    return {
        "mode": active_mode,
        "weights_loaded": w_loaded,
        "video_found": vid_found,
        "process_every_n_frames": PROCESS_EVERY_N_FRAMES,
        "frame_size": FRAME_SIZE
    }


@app.get("/video_feed")
def video_feed():
    """MJPEG stream for live video surveillance feed."""
    def frame_stream():
        while True:
            with state_lock:
                frame_bytes = latest["video"]
            if frame_bytes:
                yield (b"--frame\r\n"
                       b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n")
            time.sleep(0.04)  # ~25 FPS

    return StreamingResponse(
        frame_stream(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@app.get("/heatmap_feed")
def heatmap_feed():
    """MJPEG stream for spatial crowd density heatmap overlay."""
    def frame_stream():
        while True:
            with state_lock:
                frame_bytes = latest["heat"]
            if frame_bytes:
                yield (b"--frame\r\n"
                       b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n")
            time.sleep(0.08)  # ~12 FPS

    return StreamingResponse(
        frame_stream(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=HOST, port=PORT, reload=False)
