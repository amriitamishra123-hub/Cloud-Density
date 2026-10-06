"""
CSRNet: Dilated Convolutional Neural Network for Crowd Density Estimation.
Architecture:
  - Frontend: VGG-16 convolutional backbone (3x3 convs, padding=1, ReLU)
              [64, 64, 'M', 128, 128, 'M', 256, 256, 256, 'M', 512, 512, 512]
  - Backend:  Dilated convolutions (dilation=2, padding=2, ReLU)
              [512, 512, 512, 256, 128, 64]
  - Output:   1x1 conv mapping 64 feature channels -> 1 density map channel.

Layer attribute names ('frontend', 'backend', 'output_layer') match original
pretrained CSRNet ShanghaiTech Part B checkpoints.
"""

import os
import cv2
import numpy as np
import torch
import torch.nn as nn
from typing import Tuple

# Resolve relative path to backend/weights/csrnet_partB.pth
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
WEIGHTS_DIR = os.path.join(BACKEND_DIR, "weights")
WEIGHTS_PATH = os.path.join(WEIGHTS_DIR, "csrnet_partB.pth")

# Device configuration: CUDA GPU if available, otherwise CPU
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

def make_layers(cfg, in_channels: int = 3, dilation: bool = False) -> nn.Sequential:
    """
    Builds sequential convolutional layers with ReLU activations.
    For frontend: dilation=False -> dilation=1, padding=1
    For backend:  dilation=True  -> dilation=2, padding=2
    """
    d_rate = 2 if dilation else 1
    layers = []
    for v in cfg:
        if v == 'M':
            layers += [nn.MaxPool2d(kernel_size=2, stride=2)]
        else:
            conv2d = nn.Conv2d(
                in_channels, 
                v, 
                kernel_size=3, 
                padding=d_rate, 
                dilation=d_rate
            )
            layers += [conv2d, nn.ReLU(inplace=True)]
            in_channels = v
    return nn.Sequential(*layers)


class CSRNet(nn.Module):
    """
    Standard CSRNet architecture.
    Attributes must be exactly 'frontend', 'backend', 'output_layer'
    so official pretrained checkpoints load without key mismatches.
    """
    def __init__(self):
        super(CSRNet, self).__init__()
        # VGG-16 frontend configuration: 10 conv layers + 3 maxpools
        self.frontend_feat = [64, 64, 'M', 128, 128, 'M', 256, 256, 256, 'M', 512, 512, 512]
        # Dilated backend configuration (dilation=2): enlarges receptive field without pooling
        self.backend_feat = [512, 512, 512, 256, 128, 64]

        self.frontend = make_layers(self.frontend_feat, in_channels=3, dilation=False)
        self.backend = make_layers(self.backend_feat, in_channels=512, dilation=True)
        self.output_layer = nn.Conv2d(64, 1, kernel_size=1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.frontend(x)
        x = self.backend(x)
        x = self.output_layer(x)
        return x


# Global model and weight status flag
WEIGHTS_LOADED: bool = False
model = CSRNet().to(DEVICE)
model.eval()

# Check and load weights from backend/weights/csrnet_partB.pth
if os.path.isfile(WEIGHTS_PATH):
    try:
        print(f"[CSRNet] Loading pretrained weights from {WEIGHTS_PATH} onto {DEVICE}...")
        checkpoint = torch.load(WEIGHTS_PATH, map_location=DEVICE)

        # Handle checkpoints with "state_dict" wrapper or direct dictionaries
        if isinstance(checkpoint, dict) and "state_dict" in checkpoint:
            state_dict = checkpoint["state_dict"]
        elif isinstance(checkpoint, dict):
            state_dict = checkpoint
        else:
            state_dict = checkpoint

        # Clean any "module." prefix from PyTorch DataParallel checkpoints
        cleaned_dict = {}
        for key, value in state_dict.items():
            clean_key = key.replace("module.", "")
            cleaned_dict[clean_key] = value

        model.load_state_dict(cleaned_dict)
        model.eval()
        WEIGHTS_LOADED = True
        print(f"[CSRNet] Successfully loaded weights onto {DEVICE}. Real AI inference active.")
    except Exception as err:
        print(f"[CSRNet ERROR] Failed to load checkpoint {WEIGHTS_PATH}: {err}")
        WEIGHTS_LOADED = False
else:
    WEIGHTS_LOADED = False
    print(
        "\n" + "=" * 78 + "\n"
        "[CSRNet NOTICE] Pretrained weights file not found!\n"
        f"  Target File : {WEIGHTS_PATH}\n\n"
        "To enable real CSRNet deep learning density estimation:\n"
        "  1. Download pretrained 'csrnet_partB.pth' (ShanghaiTech Part B weights)\n"
        f"  2. Place it into: {WEIGHTS_DIR}\\\n\n"
        "WEIGHTS_LOADED = False\n"
        "Falling back to mock/simulated density estimation so the application runs.\n"
        + "=" * 78 + "\n"
    )


def predict_density(frame_bgr: np.ndarray) -> Tuple[float, np.ndarray]:
    """
    Estimates crowd density map and total headcount from a BGR video frame.

    Pipeline:
      1. Converts BGR -> RGB
      2. Normalizes using ImageNet mean [0.485, 0.456, 0.406] and std [0.229, 0.224, 0.225]
      3. Passes through CSRNet under torch.no_grad()
      4. Returns (density.sum(), 2D density map)

    If WEIGHTS_LOADED is False, returns fallback simulated values.
    """
    if frame_bgr is None:
        raise ValueError("Input frame_bgr cannot be None")

    h, w = frame_bgr.shape[:2]

    if WEIGHTS_LOADED:
        # Convert BGR (OpenCV format) to RGB (PyTorch standard)
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)

        # ImageNet normalization parameters
        mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        std = np.array([0.229, 0.224, 0.225], dtype=np.float32)

        # Scale pixel values [0, 1] then normalize
        norm_img = (frame_rgb.astype(np.float32) / 255.0 - mean) / std

        # Convert to tensor: (H, W, C) -> (1, C, H, W) on active DEVICE
        tensor = torch.from_numpy(norm_img).permute(2, 0, 1).unsqueeze(0).to(DEVICE)

        with torch.no_grad():
            output = model(tensor)

        # Squeeze batch & channel dimensions to get 2D density map
        density_map = output.squeeze().cpu().numpy()
        density_map = np.maximum(density_map, 0.0)  # Density must be non-negative
        count = float(density_map.sum())

        return count, density_map
    else:
        # Fallback simulation: compute edge-based density proxy matching (H/8, W/8) shape
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 50, 150)

        out_h, out_w = max(1, h // 8), max(1, w // 8)
        resized_edges = cv2.resize(edges, (out_w, out_h), interpolation=cv2.INTER_AREA).astype(np.float32)
        density_map = cv2.GaussianBlur(resized_edges, (9, 9), 2.0) * 0.0035

        count = float(density_map.sum())
        count = max(15.0, count)

        return float(round(count, 1)), density_map
