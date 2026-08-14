"""Live, camera-only visualizer for the RGB camera bin-sorting model.

This program never sends arm, gripper, or CAN commands. It presents model
predictions for validation after training and hand-eye/bin calibration.
"""

from __future__ import annotations

import argparse
import json
import time
from collections import deque
from pathlib import Path

import cv2
import numpy as np
import torch

try:
    from .vision_grasp_model import CameraBinSorter, make_sort_plan
except ImportError:  # Supports direct execution from this folder.
    from vision_grasp_model import CameraBinSorter, make_sort_plan


def load_sorter(checkpoint_path: Path, device: torch.device) -> tuple[CameraBinSorter, list[str], bool]:
    checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=True)
    bin_to_index = checkpoint.get("bin_to_index")
    if not isinstance(bin_to_index, dict) or len(bin_to_index) < 2:
        raise ValueError("checkpoint is not a trained camera bin sorter checkpoint")
    labels = [label for label, _ in sorted(bin_to_index.items(), key=lambda item: item[1])]
    model = CameraBinSorter(num_bins=len(labels)).to(device)
    model.load_state_dict(checkpoint["model_state_dict"])
    return model.eval(), labels, bool(checkpoint.get("preview_only", False))


def load_bin_poses(bin_poses_path: Path, labels: list[str], device: torch.device) -> torch.Tensor:
    with bin_poses_path.open(encoding="utf-8") as bin_poses_file:
        raw_poses = json.load(bin_poses_file)
    missing = [label for label in labels if label not in raw_poses]
    if missing:
        raise ValueError(f"bin pose file has no calibrated pose for: {', '.join(missing)}")
    poses = np.asarray([raw_poses[label] for label in labels], dtype=np.float32)
    if poses.shape != (len(labels), 3) or not np.isfinite(poses).all():
        raise ValueError("every bin pose must be a finite [x, y, z] robot-base position")
    return torch.from_numpy(poses).to(device)


def image_to_tensor(frame_bgr: np.ndarray, device: torch.device) -> torch.Tensor:
    rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    rgb = cv2.resize(rgb, (64, 64), interpolation=cv2.INTER_AREA)
    return torch.from_numpy(rgb.copy()).permute(2, 0, 1).unsqueeze(0).float().div_(255.0).to(device)


def draw_dashboard(
    frame: np.ndarray,
    label: str,
    confidence: float,
    pick_xyz: np.ndarray,
    place_xyz: np.ndarray,
    inference_ms: float,
    fps: float,
    preview_only: bool = False,
) -> np.ndarray:
    dashboard = frame.copy()
    lines = [
        "UNTRAINED CAMERA PREVIEW  |  NO ROBOT COMMANDS" if preview_only else "CAMERA BIN SORTER  |  VISUALIZE ONLY",
        f"Destination: {label}  ({confidence:.1%})",
        f"Pick EEF XYZ [m]:  {pick_xyz[0]:+.3f}, {pick_xyz[1]:+.3f}, {pick_xyz[2]:+.3f}",
        f"Place EEF XYZ [m]: {place_xyz[0]:+.3f}, {place_xyz[1]:+.3f}, {place_xyz[2]:+.3f}",
        f"Inference: {inference_ms:.1f} ms   Camera: {fps:.1f} FPS",
        "q: quit   space: pause",
    ]
    overlay = dashboard.copy()
    cv2.rectangle(overlay, (8, 8), (min(frame.shape[1] - 8, 650), 178), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.68, dashboard, 0.32, 0, dashboard)
    for line_number, line in enumerate(lines):
        cv2.putText(
            dashboard,
            line,
            (18, 35 + 25 * line_number),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.58,
            (90, 255, 150) if line_number == 1 else (245, 245, 245),
            1,
            cv2.LINE_AA,
        )
    return dashboard


def run_live_demo(camera_index: int, checkpoint_path: Path, bin_poses_path: Path) -> None:
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model, labels, preview_only = load_sorter(checkpoint_path, device)
    bin_poses = load_bin_poses(bin_poses_path, labels, device)
    capture = cv2.VideoCapture(camera_index)
    if not capture.isOpened():
        raise RuntimeError(f"could not open camera index {camera_index}")

    frame_times: deque[float] = deque(maxlen=30)
    paused_frame: np.ndarray | None = None
    paused = False
    try:
        while True:
            if not paused:
                ok, frame = capture.read()
                if not ok:
                    raise RuntimeError("camera returned no frame")
                paused_frame = frame
            assert paused_frame is not None
            start = time.perf_counter()
            with torch.inference_mode():
                pick_xyz, bin_logits = model(image_to_tensor(paused_frame, device))
                plan = make_sort_plan(pick_xyz, bin_logits, bin_poses)
                confidence = torch.softmax(bin_logits, dim=1).max(dim=1).values.item()
            inference_ms = (time.perf_counter() - start) * 1000.0
            now = time.perf_counter()
            frame_times.append(now)
            fps = (len(frame_times) - 1) / max(frame_times[-1] - frame_times[0], 1e-6)
            bin_index = plan["bin_index"].item()
            dashboard = draw_dashboard(
                paused_frame,
                labels[bin_index],
                confidence,
                plan["pick_end_effector_xyz"].squeeze(0).cpu().numpy(),
                plan["place_end_effector_xyz"].squeeze(0).cpu().numpy(),
                inference_ms,
                fps,
                preview_only,
            )
            cv2.imshow("Camera bin sorter", dashboard)
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            if key == ord(" "):
                paused = not paused
    finally:
        capture.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Live visualizer for a trained camera bin sorter")
    parser.add_argument("checkpoint", type=Path, help="trained camera_bin_sorter.pt checkpoint")
    parser.add_argument("bin_poses", type=Path, help="JSON map of bin label to calibrated [x, y, z]")
    parser.add_argument("--camera-index", type=int, default=0)
    args = parser.parse_args()
    run_live_demo(args.camera_index, args.checkpoint, args.bin_poses)
