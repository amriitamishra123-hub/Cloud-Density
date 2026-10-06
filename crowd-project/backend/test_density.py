"""
Test script for Phase 2: CSRNet Density Estimation & Optical Flow Verification.
1. Loads sample_crowd.jpg (creates one if not already present).
2. Resizes to max width 640 keeping aspect ratio.
3. Calls predict_density() and prints the estimated crowd count.
4. Generates and saves the blended heatmap overlay to output_heatmap.jpg.
5. Runs flow_stats() on two slightly shifted copies of the image to verify optical flow.
"""

import os
import cv2
import numpy as np

import csrnet
from flow import flow_stats, overlay

def ensure_sample_image(img_path: str):
    """Ensures sample_crowd.jpg exists by generating a synthetic test scene if needed."""
    if os.path.isfile(img_path):
        return

    print(f"[Setup] Generating initial sample image at {img_path}...")
    width, height = 800, 600  # Will test resizing to max width 640
    img = np.full((height, width, 3), 40, dtype=np.uint8)

    # Add ground texture
    noise = np.random.normal(0, 8, img.shape).astype(np.int16)
    img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    # Add simulated clusters of people
    np.random.seed(42)
    centers = [(220, 300), (400, 280), (580, 310), (300, 440), (480, 420)]
    for cx, cy in centers:
        for _ in range(16):
            px = int(np.clip(np.random.normal(cx, 40), 30, width - 30))
            py = int(np.clip(np.random.normal(cy, 35), 140, height - 40))
            # Head circle
            cv2.circle(img, (px, py), 7, (150, 190, 230), -1)
            # Body rectangle
            col = (int(np.random.randint(60, 210)), int(np.random.randint(60, 210)), int(np.random.randint(60, 210)))
            cv2.rectangle(img, (px - 9, py + 7), (px + 9, py + 28), col, -1)

    cv2.imwrite(img_path, img)


def main():
    print("=" * 65)
    print("PHASE 2 VERIFICATION: CSRNet & Optical Flow")
    print("=" * 65)

    backend_dir = os.path.dirname(os.path.abspath(__file__))
    sample_img_path = os.path.join(backend_dir, "sample_crowd.jpg")
    output_heatmap_path = os.path.join(backend_dir, "output_heatmap.jpg")

    # 1. Ensure and load sample_crowd.jpg
    ensure_sample_image(sample_img_path)
    img = cv2.imread(sample_img_path)
    if img is None:
        raise FileNotFoundError(f"Failed to load image from {sample_img_path}")

    orig_h, orig_w = img.shape[:2]
    print(f"Loaded image '{os.path.basename(sample_img_path)}' (Original shape: {orig_w}x{orig_h})")

    # 2. Resize to max width 640 keeping aspect ratio
    if orig_w > 640:
        scale = 640.0 / orig_w
        new_w = 640
        new_h = int(orig_h * scale)
        img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
        print(f"Resized image to max width 640: {new_w}x{new_h}")
    else:
        print(f"Image width ({orig_w}px) <= 640px. No downscaling needed.")

    # 3. Print estimated count from predict_density
    print("\nRunning predict_density()...")
    count, density_map = csrnet.predict_density(img)
    print("-" * 45)
    print(f"Estimated Crowd Count: {count:.2f} persons")
    print(f"Density Map Shape    : {density_map.shape}")
    print(f"Weights Loaded Mode  : {csrnet.WEIGHTS_LOADED}")
    print("-" * 45)

    # 4. Save the heatmap to output_heatmap.jpg
    print("\nGenerating JET colormap heatmap overlay (0.5/0.5 blend)...")
    blended = overlay(img, density_map)
    cv2.imwrite(output_heatmap_path, blended)
    print(f"[SUCCESS] Heatmap saved to: {output_heatmap_path}")

    # 5. Run flow_stats on two slightly shifted copies of the image to confirm optical flow
    print("\nTesting optical flow stats on two shifted image copies...")
    gray1 = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # Shift horizontal pixels by 3 to simulate moving crowd
    gray2 = np.roll(gray1, shift=3, axis=1)

    speed, turbulence = flow_stats(gray1, gray2)
    print(f"Optical Flow Speed      : {speed:.4f} (mean magnitude)")
    print(f"Optical Flow Turbulence : {turbulence:.4f} (std magnitude)")

    print("\n" + "=" * 65)
    print("Phase 2 test completed successfully!")
    print("=" * 65)


if __name__ == "__main__":
    main()
