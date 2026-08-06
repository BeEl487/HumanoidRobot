"""Reward shaping for the bin-picking task. See config/env.yaml "reward"/"success"/"failure".

Design principle (v2.2, after two earlier revisions found real problems -- history below): every
reward term is either (a) tied to a quantity that can't be held fixed for free (distance shaping,
lift height -- both continuous, but "camping" at a non-improving value earns nothing extra beyond
what that value already costs/pays), or (b) a ONE-TIME milestone bonus paid on first occurrence
per episode. There is no dense per-step reward that pays out repeatedly just for holding a state
still. This is a structural fix, not a per-symptom patch -- see the v2.1 note for why patching one
exploit at a time (adding a gate to a still-continuous bonus) left a residual loophole open.

History:
- v1: distance + sparse grasp/lift bonus only. Ran for a full 500k-timestep PPO pass (see
  ASSUMPTIONS.md "Follow-up: a full training run"). Reward improved steadily but grasp success
  stayed at 0% -- nothing bridged "close to the object" toward "gripper closed on it", so the
  sparse bonus had to be found by pure chance.
- v2: added `gripper_close_bonus_weight` (continuous, paid every step within a proximity
  threshold) and `single_finger_contact_bonus` (continuous, paid every step per finger touching).
  Both were meant to bridge the v1 gap.
- v2.1: a real exploit, found *during* v2 training by inspecting an anomalous checkpoint's actual
  rollout footage, not by code review. `gripper_close_bonus_weight` required only proximity, not
  contact -- the policy discovered it could park the gripper shut near the object and farm
  ~1.87 reward/step indefinitely with ZERO frames of contact (confirmed via env._contact_state()
  logging: touched_f1/touched_f2 False for all 200 steps, object height never changed, yet that
  one episode scored +247.9 vs. -41 to -53 for four otherwise-identical seeds). First fix: gate
  the bonus on actual finger contact.
- v2.2 (this revision): re-auditing that v2.1 fix found it was incomplete. finger2 mechanically
  mirrors finger1 (they can't open/close independently), so if the object sits off-center only
  ONE finger may ever physically reach it -- a policy could still graze that single finger against
  the object and hold position, continuously farming both the (now contact-gated) proximity bonus
  and the per-finger contact bonus, without ever achieving or approaching a real two-finger grasp.
  Any continuous per-step bonus tied to a state the agent can passively hold is farmable in
  principle, regardless of how it's gated -- so both continuous bonuses are replaced here with
  ONE-TIME milestone events (`touch_bonus` on first contact, `grasp_bonus` on first full
  two-finger grasp, both per-episode), which cannot be re-collected by holding still.
- v9 (queued, off by default -- config/env.yaml's reward.stuck.enabled): every run v1-v8
  converges to a near-static hover close to the object and then just holds there, since holding
  still is free once the distance term stops improving. Added `stuck_penalty`: a continuous
  per-step penalty while the closest arm's EE hasn't moved more than `stuck.movement_threshold_m`
  for `stuck.steps_threshold` consecutive steps (state tracked in BinPickingEnv.step, passed in as
  `is_stuck` -- this function stays a pure function, no state of its own). A continuous PENALTY
  doesn't reopen the v2 pattern the way a continuous BONUS did: the worst case if an agent "games"
  it is minimal jitter that avoids the penalty without genuine exploration -- a weak signal, not a
  false reward inflation.
"""

from __future__ import annotations

import numpy as np


def compute_step_reward(
    ee_pos: np.ndarray,
    object_pos: np.ndarray,
    height_above_floor: float,
    is_grasped: bool,
    just_touched: bool,
    just_grasped: bool,
    is_stuck: bool,
    cfg: dict,
) -> float:
    """ee_pos: one entry per active arm. Uses the closest active arm's EE to the object for the
    distance term, so this reward is well-defined for both the single-arm (6.1) and both-arms
    (6.2) configurations without special-casing either.

    just_touched/just_grasped are true only on the step each milestone is FIRST reached in the
    episode (computed once in BinPickingEnv.step against per-episode flags, not recomputed here)
    -- paying them here unconditionally on every call would defeat the point.

    is_stuck: whether the closest arm's EE has been near-motionless for enough consecutive steps
    (tracked in BinPickingEnv.step; always False when config/env.yaml's reward.stuck.enabled is
    False, which is the v8 and earlier default -- see this module's v9 history note)."""
    r = cfg["reward"]
    dist = float(np.min(np.linalg.norm(ee_pos - object_pos[None, :], axis=1)))

    reward = r["distance_weight"] * dist + r["step_penalty"]

    if just_touched:
        reward += r["touch_bonus"]
    if just_grasped:
        reward += r["grasp_bonus"]
    if is_grasped:
        reward += r["lift_bonus_weight"] * max(height_above_floor, 0.0)
    if is_stuck:
        reward += r["stuck"]["penalty"]
    return float(reward)
