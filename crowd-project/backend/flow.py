"""
Optical Flow and Heatmap Overlay Module for Crowd Motion Analysis.
Calculates motion statistics (average speed and turbulence) using Farneback optical flow,
and generates JET colormap heatmap overlays blended 50/50 with video frames.
"""

import cv2
import numpy as np
from typing import Tuple

def flow_stats(prev_gray: np.ndarray, gray: np.ndarray) -> Tuple[float, float]:
    """
    Computes optical flow statistics using OpenCV Farneback algorithm.
    cv2.calcOpticalFlowFarneback(prev_gray, gray, None, 0.5, 3, 15, 3, 5, 1.2, 0)
    
    Args:
        prev_gray: Grayscale image from previous frame (uint8, 2D array).
        gray: Grayscale image from current frame (uint8, 2D array).

    Returns:
        (speed, turbulence) as Python floats:
            speed: Mean magnitude of optical flow displacement vectors.
            turbulence: Standard deviation of flow magnitude (indicator of motion chaos).
    """
    if prev_gray is None or gray is None:
        return 0.0, 0.0

    # Ensure inputs are 2D grayscale single channel
    if len(prev_gray.shape) == 3:
        prev_gray = cv2.cvtColor(prev_gray, cv2.COLOR_BGR2GRAY)
    if len(gray.shape) == 3:
        gray = cv2.cvtColor(gray, cv2.COLOR_BGR2GRAY)

    # Dense Farneback optical flow as specified
    flow = cv2.calcOpticalFlowFarneback(
        prev_gray, gray, None, 0.5, 3, 15, 3, 5, 1.2, 0
    )

    # Convert Cartesian flow (dx, dy) to polar coordinates (magnitude, angle)
    magnitude, _ = cv2.cartToPolar(flow[..., 0], flow[..., 1])

    # Return mean magnitude and std deviation as pure Python floats
    speed = float(np.mean(magnitude))
    turb = float(np.std(magnitude))
    return speed, turb


def overlay(frame: np.ndarray, density_map: np.ndarray) -> np.ndarray:
    """
    Blends a crowd density map onto the video frame using JET colormap.
    1. Resizes density map to frame dimensions.
    2. Normalizes density values to 0-1.
    3. Applies cv2.COLORMAP_JET.
    4. Blends 0.5 / 0.5 with the original frame.

    Args:
        frame: Original BGR video frame (H, W, 3).
        density_map: 2D numpy array of estimated crowd density.

    Returns:
        blended: BGR image blended with JET heatmap.
    """
    if frame is None:
        raise ValueError("frame cannot be None")

    if density_map is None:
        return frame.copy()

    h, w = frame.shape[:2]

    # 1. Resize density map to match the frame size
    density_resized = cv2.resize(
        density_map.astype(np.float32), 
        (w, h), 
        interpolation=cv2.INTER_CUBIC
    )

    # 2. Normalise to 0-1 range
    d_min = float(np.min(density_resized))
    d_max = float(np.max(density_resized))
    if d_max > d_min:
        norm_density = (density_resized - d_min) / (d_max - d_min)
    else:
        norm_density = np.zeros((h, w), dtype=np.float32)

    # Convert to 8-bit unsigned integer [0, 255] for OpenCV colormap
    heatmap_uint8 = (norm_density * 255.0).astype(np.uint8)

    # 3. Apply cv2.COLORMAP_JET (Blue=low, Green/Yellow=mid, Red=high)
    heatmap_color = cv2.applyColorMap(heatmap_uint8, cv2.COLORMAP_JET)

    # 4. Blend 0.5/0.5 with the frame
    blended = cv2.addWeighted(frame, 0.5, heatmap_color, 0.5, 0)
    return blended
