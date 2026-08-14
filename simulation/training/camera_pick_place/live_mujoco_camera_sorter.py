"""Interactive MuJoCo head-camera dashboard for the camera bin sorter.

This is the correct live preview for the current project stage: frames come
from VisionWrapper's virtual ``head_camera``, not a physical webcam. It never
commands real hardware.
"""

from __future__ import annotations

import argparse
import pathlib
import sys
import time
from collections import deque

import cv2
import numpy as np
import torch

SIM_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(SIM_ROOT))

from training.camera_pick_place.live_camera_bin_sorter import (  # noqa: E402
    draw_dashboard,
    image_to_tensor,
    load_bin_poses,
    load_sorter,
)
from training.camera_pick_place.train_camera_pick_place import make_env  # noqa: E402
from training.camera_pick_place.vision_grasp_model import make_sort_plan  # noqa: E402


def run_mujoco_dashboard(checkpoint_path: pathlib.Path, bin_poses_path: pathlib.Path, seed: int) -> None:
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model, labels, preview_only = load_sorter(checkpoint_path, device)
    bin_poses = load_bin_poses(bin_poses_path, labels, device)
    env = make_env(seed=seed, include_privileged_state=False)
    frame_times: deque[float] = deque(maxlen=30)
    paused = False
    obs = env.reset()
    action = np.zeros(env.action_space.shape, dtype=np.float32)

    try:
        while True:
            rgb = obs["rgb"][0]
            frame_bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
            start = time.perf_counter()
            with torch.inference_mode():
                pick_xyz, bin_logits = model(image_to_tensor(frame_bgr, device))
                plan = make_sort_plan(pick_xyz, bin_logits, bin_poses)
                confidence = torch.softmax(bin_logits, dim=1).max(dim=1).values.item()
            inference_ms = (time.perf_counter() - start) * 1000.0
            frame_times.append(time.perf_counter())
            fps = (len(frame_times) - 1) / max(frame_times[-1] - frame_times[0], 1e-6)
            bin_index = plan["bin_index"].item()
            dashboard = draw_dashboard(
                frame_bgr,
                labels[bin_index],
                confidence,
                plan["pick_end_effector_xyz"].squeeze(0).cpu().numpy(),
                plan["place_end_effector_xyz"].squeeze(0).cpu().numpy(),
                inference_ms,
                fps,
                preview_only,
            )
            cv2.putText(
                dashboard,
                "SOURCE: MUJOCO VIRTUAL HEAD CAMERA",
                (18, dashboard.shape[0] - 18),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 215, 255),
                1,
                cv2.LINE_AA,
            )
            cv2.imshow("MuJoCo camera bin sorter", dashboard)
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            if key == ord(" "):
                paused = not paused
            if not paused:
                obs, _, _, _ = env.step(action)
    finally:
        env.close()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Live MuJoCo head-camera sorter dashboard")
    parser.add_argument("checkpoint", type=pathlib.Path)
    parser.add_argument("bin_poses", type=pathlib.Path)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    run_mujoco_dashboard(args.checkpoint, args.bin_poses, args.seed)
