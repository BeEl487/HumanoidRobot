"""Verifies the head camera actually frames the object's randomized spawn area -- not just a
single default/centered position (which is what the Milestone 4/5 visual checks happened to use).
Samples object positions with the exact same distribution as sim_env/domain_randomization.py's
randomize_objects() and checks each against the camera's real frustum (world pose + fovy/hfov),
not just a static snapshot.

This exists because the deployed camera passed every prior visual check yet still missed the
object in real policy rollouts -- the earlier checks only ever rendered the object at the bin's
center, which happened to be in frame, while the actual randomized spawn area mostly wasn't. Gate:
>=95% of sampled spawn positions in frame.
"""

from __future__ import annotations

import pathlib
import sys

import mujoco
import numpy as np
import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "sim_env"))
from build_model import hfov_to_fovy, load_model  # noqa: E402
from domain_randomization import _load_scene_config, bin_geometry_from_config  # noqa: E402

SIM_ROOT = pathlib.Path(__file__).resolve().parent.parent
CAMERA_CONFIG_PATH = SIM_ROOT / "config" / "camera.yaml"
N_SAMPLES = 500
COVERAGE_GATE = 0.95


def fraction_in_view(seed: int = 0) -> float:
    model, data = load_model()
    mujoco.mj_resetData(model, data)
    mujoco.mj_forward(model, data)

    cam_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_CAMERA, "head_camera")
    cam_pos = data.cam_xpos[cam_id].copy()
    cam_mat = data.cam_xmat[cam_id].reshape(3, 3).copy()
    view_dir, right, up = -cam_mat[:, 2], cam_mat[:, 0], cam_mat[:, 1]

    with open(CAMERA_CONFIG_PATH, encoding="utf-8") as f:
        cam_cfg = yaml.safe_load(f)
    width, height = cam_cfg["resolution_default"]
    fovy = hfov_to_fovy(cam_cfg["horizontal_fov_deg"], width, height)
    half_h = np.radians(cam_cfg["horizontal_fov_deg"]) / 2
    half_v = np.radians(fovy) / 2

    scene_cfg = _load_scene_config()
    obj_cfg = scene_cfg["objects"]
    bin_cx, bin_cy, bin_floor_z = bin_geometry_from_config(scene_cfg)
    inner_w, inner_d, _ = scene_cfg["bin"]["inner_size"]
    margin = obj_cfg["spawn_margin_m"]
    half_w = max(inner_w / 2 - margin, 0.005)
    half_d = max(inner_d / 2 - margin, 0.005)

    rng = np.random.default_rng(seed)
    in_view = 0
    for _ in range(N_SAMPLES):
        x = bin_cx + rng.uniform(-half_w, half_w)
        y = bin_cy + rng.uniform(-half_d, half_d)
        z = bin_floor_z + rng.uniform(*obj_cfg["drop_height_range_m"])
        vec = np.array([x, y, z]) - cam_pos
        depth = vec @ view_dir
        if depth <= 0:
            continue
        h_off = np.arctan2(vec @ right, depth)
        v_off = np.arctan2(vec @ up, depth)
        if abs(h_off) < half_h and abs(v_off) < half_v:
            in_view += 1
    return in_view / N_SAMPLES


if __name__ == "__main__":
    frac = fraction_in_view()
    print(f"check_camera_coverage: {frac*100:.1f}% of {N_SAMPLES} sampled spawn positions in "
          f"the head camera's frame (gate: {COVERAGE_GATE*100:.0f}%)")
    assert frac >= COVERAGE_GATE, (
        f"Camera coverage gate failed: {frac*100:.1f}% < {COVERAGE_GATE*100:.0f}%. "
        "Adjust config/camera.yaml (mount_pos / pitch_down_deg / horizontal_fov_deg) and re-run."
    )
    print("check_camera_coverage.py: GATE PASSED")
