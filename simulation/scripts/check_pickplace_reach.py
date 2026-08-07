"""Reachability gate for the suction pick-place task's two boxes (config/pick_place_scene.yaml),
mirroring reachability_check.py's role for the bin-picking task's bin. Checks all 4 corners of
both the source and destination box footprints against the single active arm
(config/pick_place_env.yaml's active_arm) using ikpy against humanoid.urdf directly -- the same
method, and the same lesson: a box position that "looks" reachable by eye can silently exceed the
arm's actual joint-limited workspace (this is exactly what caught the original 0.06/0.06 box
centers being wrong once the boxes tripled in Y -- see docs/ASSUMPTIONS.md's "Suction pick-place"
entry).

Gate: all 4 corners of both boxes must be reachable. If this fails, the fix is to adjust
config/pick_place_scene.yaml's box centers/table size and re-run -- not to loosen the gate.
"""

from __future__ import annotations

import pathlib
import sys
import warnings

import numpy as np
import yaml
from ikpy.chain import Chain

warnings.filterwarnings("ignore", category=UserWarning, module="ikpy")

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from reachability_check import _build_arm_chain, _is_reachable, MOUNT_HEIGHT_M  # noqa: E402

SIM_ROOT = pathlib.Path(__file__).resolve().parent.parent
ENV_CONFIG_PATH = SIM_ROOT / "config" / "pick_place_env.yaml"
SCENE_CONFIG_PATH = SIM_ROOT / "config" / "pick_place_scene.yaml"


def _pick_place_geometry(cfg: dict) -> dict:
    t, b = cfg["table"], cfg["boxes"]
    floor_top_z = t["top_height"] + t["top_thickness"] + b["wall_thickness"]
    src_x, src_y = b["source"]["center_xy"]
    dst_x, dst_y = b["destination"]["center_xy"]
    return {"source": (src_x, src_y, floor_top_z), "destination": (dst_x, dst_y, floor_top_z)}


def check_box_corners(chain: Chain, mask: list[bool], cx: float, cy: float, z: float, half_x: float, half_y: float) -> bool:
    all_ok = True
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = cx + sx * half_x, cy + sy * half_y
            local = np.array([x, y, z - MOUNT_HEIGHT_M])
            ok = _is_reachable(chain, mask, local)
            all_ok = all_ok and ok
            print(f"  corner ({x:.3f}, {y:.3f}, {z:.3f}): reachable={ok}")
    return all_ok


if __name__ == "__main__":
    with open(ENV_CONFIG_PATH, encoding="utf-8") as f:
        active_arm = yaml.safe_load(f)["active_arm"]
    with open(SCENE_CONFIG_PATH, encoding="utf-8") as f:
        scene_cfg = yaml.safe_load(f)

    geom = _pick_place_geometry(scene_cfg)
    iw, idepth, _ = scene_cfg["boxes"]["inner_size"]
    half_x, half_y = iw / 2, idepth / 2

    chain, mask = _build_arm_chain(active_arm)

    all_ok = True
    for name in ("source", "destination"):
        cx, cy, z = geom[name]
        print(f"{name} box (center {cx:.3f}, {cy:.3f}):")
        ok = check_box_corners(chain, mask, cx, cy, z, half_x, half_y)
        print(f"{name}: ALL CORNERS OK = {ok}")
        all_ok = all_ok and ok

    assert all_ok, (
        f"Reachability gate failed for the '{active_arm}' arm on one or more box corners. "
        "Adjust config/pick_place_scene.yaml's box centers/table size and re-run."
    )
    print("check_pickplace_reach.py: GATE PASSED")
