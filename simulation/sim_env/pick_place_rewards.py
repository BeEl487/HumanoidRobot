"""Reward shaping for the suction pick-place task (cube: source/"left" box -> destination/"right"
box). See config/pick_place_env.yaml "reward"/"success"/"failure".

Follows the same structural principle the bin-picking task's rewards.py arrived at only after a
real reward-hacking exploit was found in that task's v2 (a continuous bonus farmable by holding a
state, not earning it): every term here is either (a) tied to a quantity that can't be held fixed
for free (EE-to-cube distance, lift height, cube-to-destination distance -- all continuous, but
"camping" at a non-improving value earns nothing extra beyond what that value already costs/pays),
or (b) a ONE-TIME milestone bonus paid on first occurrence per episode (attach, place). There is no
per-step bonus that pays out repeatedly just for holding a state still -- adopting that lesson from
the start here instead of re-discovering it the same way.

Milestone ladder: reduce EE-to-cube distance (continuous) -> suction attach (attach_bonus, once)
-> lift + carry toward destination (continuous, both tied to genuine cube pose, can't be faked
without an actual attach) -> place success (place_bonus, once, requires the cube at rest in the
destination box AFTER release, not just "close").
"""

from __future__ import annotations

import numpy as np


def compute_step_reward(
    ee_pos: np.ndarray,
    cube_pos: np.ndarray,
    dest_center_xy: np.ndarray,
    height_above_table: float,
    is_attached: bool,
    just_attached: bool,
    just_lifted: bool,
    just_placed: bool,
    just_released_early: bool,
    is_arm_collision: bool,
    is_stalled: bool,
    cube_disturbance: float,
    prev_carry_dist: float | None,
    has_lifted: bool,
    action: np.ndarray,
    prev_action: np.ndarray,
    cfg: dict,
) -> float:
    """ee_pos/cube_pos/dest_center_xy: single active arm, so no closest-of-N-arms reduction is
    needed here (unlike bin_picking's rewards.py, which supports both arms active at once).

    just_attached/just_lifted/just_placed/just_released_early are computed once in
    SuctionPickPlaceEnv.step against per-episode state, not recomputed here -- paying them here
    unconditionally on every call would defeat the point (see module docstring)."""
    r = cfg["reward"]
    reward = r["step_penalty"]

    if not is_attached:
        dist = float(np.linalg.norm(ee_pos - cube_pos))
        reward += r["distance_weight"] * dist
    else:
        if just_lifted:
            reward += r["lift_bonus"]
            reward += r["stage_transition_bonus"]
        carry_dist = float(np.linalg.norm(cube_pos[:2] - dest_center_xy))
        if has_lifted:
            reward += r["carry_distance_weight_after_lift"] * carry_dist
            idle_penalty = r["attached_idle_penalty_after_lift"]
        else:
            reward += r["carry_distance_weight"] * carry_dist
            idle_penalty = r["attached_idle_penalty"]
        if prev_carry_dist is not None and carry_dist >= prev_carry_dist - r["carry_progress_tolerance_m"]:
            reward += idle_penalty

    if just_attached:
        reward += r["attach_bonus"]
    if just_placed:
        reward += r["place_bonus"]
    if just_released_early:
        reward += r["premature_release_penalty"]
    if is_arm_collision:
        reward += r["collision_penalty"]
    if is_stalled:
        reward += r["stall_penalty"]
    if cube_disturbance > 0.0:
        reward += r["cube_disturbance_weight"] * cube_disturbance

    wasted_motion = float(np.linalg.norm(np.asarray(action) - np.asarray(prev_action)))
    reward += r["wasted_motion_weight"] * wasted_motion

    return float(reward)
