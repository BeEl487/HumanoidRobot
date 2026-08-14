"""Milestone 5 reachability gate: sample points across the bin floor and check what fraction is
reachable by at least one arm, using ikpy against models/urdf/humanoid.urdf directly (not MuJoCo)
-- a deliberate choice that also validates the URDF is actually usable by the real robot's own
future kinematics library (ARCHITECTURE.md's Phase 1 plan), not just by MuJoCo.

Gate: >=80% of sampled bin-floor points reachable by at least one arm. If this fails, the fix is
to adjust config/scene.yaml (table/bin position) or the URDF's arm dimensions and re-run -- not
to loosen the gate.
"""

from __future__ import annotations

import pathlib
import warnings

import numpy as np
import yaml
from ikpy.chain import Chain

warnings.filterwarnings("ignore", category=UserWarning, module="ikpy")

SIM_ROOT = pathlib.Path(__file__).resolve().parent.parent
URDF_PATH = SIM_ROOT / "models" / "urdf" / "humanoid.urdf"
SCENE_CONFIG_PATH = SIM_ROOT / "config" / "scene.yaml"

# Must match scripts/build_model.py's mount body position (models/mjcf/scene.xml's "mount" body)
# -- ikpy operates in the URDF's own base_link frame (origin at 0,0,0), which has no knowledge of
# where build_model.py welds the robot into the MuJoCo scene, so targets must be shifted into
# that frame before solving.
MOUNT_HEIGHT_M = 0.90

REACH_TOLERANCE_M = 0.05  # IK convergence tolerance for counting a point "reachable"
GRID_N = 6  # GRID_N x GRID_N samples across the bin floor
GATE_FRACTION = 0.80


def _build_arm_chain(side: str) -> tuple[Chain, list[bool]]:
    elems = [
        "base_link", "base_to_torso", "torso_link",
        f"{side}_shoulder_yaw_joint", f"{side}_shoulder_yaw_link",
        f"{side}_shoulder_pitch_joint", f"{side}_shoulder_link",
        f"{side}_shoulder_roll_joint", f"{side}_upper_arm_link",
        f"{side}_elbow_joint", f"{side}_forearm_link",
        f"{side}_ee_mount_joint", f"{side}_ee_mount_link",
    ]
    # active_links_mask must be True only for the 4 real revolute arm joints -- the fixed joints
    # in the chain (base_to_torso, ee_mount_joint) and anything ikpy auto-appends past the
    # requested end link (the gripper) must stay inactive, or the IK solver "explores" DOFs that
    # either contribute nothing (fixed joints) or aren't part of what this check is measuring.
    chain = Chain.from_urdf_file(str(URDF_PATH), base_elements=elems)
    mask = [False] * len(chain.links)
    for i, link in enumerate(chain.links):
        if link.name in (f"{side}_shoulder_yaw_joint", f"{side}_shoulder_pitch_joint", f"{side}_shoulder_roll_joint", f"{side}_elbow_joint"):
            mask[i] = True
    chain.active_links_mask = mask
    return chain, mask


def _midrange_initial_guess(chain: Chain, mask: list[bool]) -> list[float]:
    """ikpy's default initial guess is all-zeros, which sits exactly on the lower bound for
    shoulder_roll/elbow (both range from 0, not symmetric around 0) -- the LM solver gets stuck
    right at that boundary and never explores the rest of the joint's range (confirmed
    empirically: this alone was the difference between ~6% and 100% convergence on easy,
    obviously-reachable test targets). Starting at each active joint's mid-range avoids it."""
    init = [0.0] * len(chain.links)
    for i, link in enumerate(chain.links):
        if mask[i]:
            lo, hi = link.bounds
            init[i] = (lo + hi) / 2
    return init


def _is_reachable(chain: Chain, mask: list[bool], target_local: np.ndarray) -> bool:
    init = _midrange_initial_guess(chain, mask)
    solution = chain.inverse_kinematics(target_local.tolist(), initial_position=init)
    achieved = chain.forward_kinematics(solution)[:3, 3]
    return float(np.linalg.norm(achieved - target_local)) < REACH_TOLERANCE_M


def sample_bin_floor_points() -> np.ndarray:
    with open(SCENE_CONFIG_PATH, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    t, b = cfg["table"], cfg["bin"]
    cx, cy = t["center_xy"]
    floor_z = t["top_height"] + t["top_thickness"] + b["wall_thickness"]
    iw, idepth, _ = b["inner_size"]
    margin = cfg["objects"]["spawn_margin_m"]
    xs = np.linspace(cx - iw / 2 + margin, cx + iw / 2 - margin, GRID_N)
    ys = np.linspace(cy - idepth / 2 + margin, cy + idepth / 2 - margin, GRID_N)
    grid = np.array([[x, y, floor_z] for x in xs for y in ys])
    return grid


if __name__ == "__main__":
    left_chain, left_mask = _build_arm_chain("left")
    right_chain, right_mask = _build_arm_chain("right")
    points = sample_bin_floor_points()

    reachable = 0
    for p in points:
        p_local = p.copy()
        p_local[2] -= MOUNT_HEIGHT_M
        if _is_reachable(left_chain, left_mask, p_local) or _is_reachable(right_chain, right_mask, p_local):
            reachable += 1

    fraction = reachable / len(points)
    print(f"reachability_check: {reachable}/{len(points)} bin-floor points reachable "
          f"({fraction*100:.1f}%), gate is {GATE_FRACTION*100:.0f}%")
    assert fraction >= GATE_FRACTION, (
        f"Reachability gate failed: {fraction*100:.1f}% < {GATE_FRACTION*100:.0f}%. "
        "Adjust config/scene.yaml (table/bin position) or the URDF's arm dimensions and re-run."
    )
    print("reachability_check.py: GATE PASSED")
