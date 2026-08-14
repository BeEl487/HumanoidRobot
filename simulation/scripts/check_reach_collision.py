"""Collision-aware reachability gate: for each reachability_check.py grid point (and the current
curriculum targets), find an IK solution and then verify it against real MuJoCo self-collision,
not just kinematics.

Why this exists: reachability_check.py uses ikpy alone, which has no notion of the torso's
collision geometry -- it will happily report a target "reachable" via a joint configuration that
requires the arm to pass through the torso. That gap went unnoticed through v8, v9, and v10 (each
individually "IK-verified" per commit history) -- the v10 curriculum target that was reported as
solved with 0.00cm residual actually required the upper arm to penetrate 3.6cm into the torso box,
confirmed here for the first time by checking real contacts rather than just forward kinematics.
Keep this script passing on every future geometry change (torso size, arm length, shoulder offset,
joint ranges) -- ikpy alone is not sufficient evidence that a target is actually reachable.

Gate: >=80% of sampled bin-floor points both IK-solvable (reachability_check.py's own tolerance)
AND collision-free (no contact between the solving arm and any other body) by at least one arm.
The curriculum targets are checked separately and unconditionally -- those failing is always a
hard failure regardless of the general grid's pass rate, since that's what's actually being
trained against right now.
"""

from __future__ import annotations

import pathlib
import sys
import warnings

import mujoco
import numpy as np
import yaml

warnings.filterwarnings("ignore", category=UserWarning, module="ikpy")

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import build_model  # noqa: E402
from reachability_check import (  # noqa: E402
    GATE_FRACTION,
    MOUNT_HEIGHT_M,
    REACH_TOLERANCE_M,
    _build_arm_chain,
    _midrange_initial_guess,
    sample_bin_floor_points,
)

SIM_ROOT = pathlib.Path(__file__).resolve().parent.parent
ENV_CONFIG_PATH = SIM_ROOT / "config" / "env.yaml"
COLLISION_MARGIN_M = 0.005  # a contact within this distance still counts as "colliding" (not just exact penetration)


def _solve(chain, mask, target_local: np.ndarray) -> tuple[float, list[float]]:
    init = _midrange_initial_guess(chain, mask)
    solution = chain.inverse_kinematics(target_local.tolist(), initial_position=init)
    achieved = chain.forward_kinematics(solution)[:3, 3]
    resid = float(np.linalg.norm(achieved - target_local))
    angles = [a for a, active in zip(solution, mask) if active]
    return resid, angles


def _set_arm(model: mujoco.MjModel, data: mujoco.MjData, side: str, angles: list[float]) -> None:
    names = [f"{side}_shoulder_yaw_joint", f"{side}_shoulder_pitch_joint", f"{side}_shoulder_roll_joint", f"{side}_elbow_joint"]
    data.qpos[:] = 0
    for n, a in zip(names, angles):
        data.qpos[model.joint(n).qposadr[0]] = a


def _robot_body_ids(model: mujoco.MjModel) -> set[int]:
    """Bodies that are part of the robot itself (torso + both arms), excluding world/table/bin/
    objects entirely -- spawn objects overlap each other and the ground before physics settles
    them (a separate, already-handled concern, see check_scene_settle.py), which would otherwise
    swamp this check with contacts that have nothing to do with arm/torso self-collision."""
    ids = set()
    for i in range(model.nbody):
        name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, i) or ""
        if name == "torso_link" or name.startswith(("left_", "right_")):
            ids.add(i)
    return ids


def _worst_self_collision(model: mujoco.MjModel, data: mujoco.MjData, robot_bodies: set[int]) -> float:
    """Most negative contact distance between two robot-own geoms (0 or positive = clear)."""
    mujoco.mj_forward(model, data)
    worst = 0.0
    for i in range(data.ncon):
        c = data.contact[i]
        b1 = model.geom_bodyid[c.geom1]
        b2 = model.geom_bodyid[c.geom2]
        if b1 not in robot_bodies or b2 not in robot_bodies:
            continue
        worst = min(worst, c.dist)
    return worst


def _is_clear(model, data, robot_bodies, side: str, resid: float, angles: list[float]) -> bool:
    if resid >= REACH_TOLERANCE_M:
        return False
    _set_arm(model, data, side, angles)
    return _worst_self_collision(model, data, robot_bodies) > -COLLISION_MARGIN_M


def _check_point(model, data, robot_bodies, chains, target_world: np.ndarray) -> bool:
    target_local = target_world.copy()
    target_local[2] -= MOUNT_HEIGHT_M
    for side, (chain, mask) in chains.items():
        resid, angles = _solve(chain, mask, target_local)
        if _is_clear(model, data, robot_bodies, side, resid, angles):
            return True
    return False


if __name__ == "__main__":
    model, data = build_model.load_model()
    robot_bodies = _robot_body_ids(model)
    chains = {"left": _build_arm_chain("left"), "right": _build_arm_chain("right")}

    points = sample_bin_floor_points()
    clear = sum(_check_point(model, data, robot_bodies, chains, p) for p in points)
    fraction = clear / len(points)
    print(f"check_reach_collision (grid): {clear}/{len(points)} points reachable AND "
          f"collision-free ({fraction*100:.1f}%), gate is {GATE_FRACTION*100:.0f}%")

    with open(ENV_CONFIG_PATH, encoding="utf-8") as f:
        curriculum = yaml.safe_load(f).get("curriculum", {})

    curriculum_ok = True
    for side, target in curriculum.get("targets", {}).items():
        target_world = np.array(target, dtype=float)
        chain, mask = chains[side]
        target_local = target_world.copy()
        target_local[2] -= MOUNT_HEIGHT_M
        resid, angles = _solve(chain, mask, target_local)
        clear_here = _is_clear(model, data, robot_bodies, side, resid, angles)
        status = "OK" if clear_here else "FAIL"
        print(f"  curriculum target[{side}] = {target}: IK residual {resid*100:.2f}cm, "
              f"collision-free={clear_here} -- {status}")
        curriculum_ok = curriculum_ok and clear_here

    assert fraction >= GATE_FRACTION, (
        f"Collision-aware reachability gate failed: {fraction*100:.1f}% < {GATE_FRACTION*100:.0f}%. "
        "Widening joint ranges alone will not fix a self-collision failure -- check torso/arm "
        "geometry, not just joint limits."
    )
    assert curriculum_ok, (
        "The active curriculum target(s) in config/env.yaml are not both IK-solvable and "
        "collision-free. Do not launch training against a target this script fails on -- it was "
        "exactly this gap (ikpy-only verification) that let v8/v9/v10 train against an "
        "unreachable-in-practice target."
    )
    print("check_reach_collision.py: GATE PASSED")
