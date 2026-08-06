"""Milestone 6.1 Gymnasium environment verification:
1. gymnasium's built-in env_checker passes (mandatory gate).
2. A 5-episode random-action rollout has no NaN/Inf, obs stay within declared bounds, episodes
   terminate/truncate correctly.
3. A simple scripted P-controller (not RL) drives reward upward as it approaches/grasps the
   object -- must pass before spending any compute on RL training (Milestone 8).
4. Determinism: reset(seed=...) reproduces identical obs; an identical action sequence from an
   identical seed reproduces an identical trajectory.
"""

from __future__ import annotations

import pathlib
import sys

import numpy as np
from gymnasium.utils.env_checker import check_env

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from sim_env.bin_picking_env import BinPickingEnv  # noqa: E402


def run_gymnasium_check_env() -> None:
    env = BinPickingEnv()
    check_env(env.unwrapped, skip_render_check=True)
    print("run_gymnasium_check_env: OK (gymnasium.utils.env_checker passed)")


def run_random_rollout(n_episodes: int = 5) -> None:
    env = BinPickingEnv()
    for ep in range(n_episodes):
        obs, info = env.reset(seed=ep)
        for key, space in env.observation_space.spaces.items():
            assert space.contains(obs[key]), f"ep {ep}: obs[{key}] out of bounds at reset: {obs[key]}"
        terminated = truncated = False
        steps = 0
        while not (terminated or truncated):
            action = env.action_space.sample()
            obs, reward, terminated, truncated, info = env.step(action)
            for key, space in env.observation_space.spaces.items():
                assert np.all(np.isfinite(obs[key])), f"ep {ep} step {steps}: non-finite obs[{key}]"
                assert space.contains(obs[key]), f"ep {ep} step {steps}: obs[{key}] out of bounds: {obs[key]}"
            assert np.isfinite(reward), f"ep {ep} step {steps}: non-finite reward"
            steps += 1
            assert steps <= env.cfg["episode_max_steps"] + 1, f"ep {ep}: episode ran past episode_max_steps"
        assert terminated or truncated, f"ep {ep}: episode never ended"
    print(f"run_random_rollout: OK ({n_episodes} episodes, random actions, no NaN/Inf, "
          "all obs within bounds, all episodes ended)")


def run_scripted_p_controller_reward_check() -> None:
    """Drives the EE toward the object via real Jacobian-transpose control (mujoco.mj_jacBody
    for the EE body's positional Jacobian w.r.t. the arm's own DOFs, commanding a joint-velocity
    step proportional to J^T @ (object - ee)) -- a real, if simple, task-space controller, not an
    arbitrary fixed action, so this is a fair test of whether the reward signal is informative."""
    import mujoco

    env = BinPickingEnv()
    obs, info = env.reset(seed=0)
    model, data = env.model, env.data
    ee_body_id = int(env.joints.ee_body_id[0])
    dofadr = env.joints.arm_dofadr
    lo, hi = env.joints.arm_jnt_range[:, 0], env.joints.arm_jnt_range[:, 1]

    # Controls only the FIRST active arm's 3 joints via the Jacobian (a real task-space
    # controller, generalized to n_arms>=1 rather than hardcoded to exactly one arm) -- any other
    # active arms (6.2's [left, right]) are left at their normalized-0 (mid-range target) action,
    # a harmless no-op-ish default, not chaotic; every gripper is commanded closed throughout.
    n_arm_joints_first = 3
    jacp = np.zeros((3, model.nv))
    rewards_seen = []
    current_qpos = data.qpos[env.joints.arm_qposadr[:n_arm_joints_first]].copy()
    n_gripper = len(env.joints.gripper_joint_names)
    for _ in range(env.cfg["episode_max_steps"]):
        mujoco.mj_jacBody(model, data, jacp, None, ee_body_id)
        J = jacp[:, dofadr[:n_arm_joints_first]]  # (3, 3) for the first arm's joints
        # Jacobian is taken at gripper_base_link (a fine proxy -- same rigid attachment, so it
        # rotates with the arm the same way the fingers do) but the actual position error steers
        # toward the fingertip midpoint, matching what the reward/observation now use (see
        # BinPickingEnv._ee_pos and docs/ASSUMPTIONS.md "v6").
        ee_pos = env._ee_pos()[0]
        object_pos = data.xpos[env._object_body_id]
        error = object_pos - ee_pos
        dq = 3.0 * (J.T @ error)  # Jacobian-transpose step, gain chosen empirically for this scale
        current_qpos = np.clip(current_qpos + dq, lo[:n_arm_joints_first], hi[:n_arm_joints_first])
        normalized_arm = 2.0 * (current_qpos - lo[:n_arm_joints_first]) / (hi[:n_arm_joints_first] - lo[:n_arm_joints_first]) - 1.0

        action = np.zeros(env.action_space.shape, dtype=np.float32)
        action[:n_arm_joints_first] = normalized_arm
        action[-n_gripper:] = -1.0  # close every gripper throughout, to exercise the grasp-bonus term
        obs, reward, terminated, truncated, info = env.step(action)
        rewards_seen.append(reward)
        if terminated or truncated:
            break

    rewards_seen = np.array(rewards_seen)
    half = len(rewards_seen) // 2
    first_half_mean = rewards_seen[:half].mean()
    second_half_mean = rewards_seen[half:].mean()
    print(f"run_scripted_p_controller_reward_check: first-half mean reward={first_half_mean:.4f}, "
          f"second-half mean reward={second_half_mean:.4f}")
    assert second_half_mean > first_half_mean, (
        "reward did not trend upward under a simple scripted approach -- check reward shaping "
        "before spending compute on RL"
    )
    print("run_scripted_p_controller_reward_check: OK")


def run_determinism_check() -> None:
    env1 = BinPickingEnv()
    obs1, _ = env1.reset(seed=42)
    env2 = BinPickingEnv()
    obs2, _ = env2.reset(seed=42)
    for key in obs1:
        assert np.array_equal(obs1[key], obs2[key]), f"reset(seed=42) obs[{key}] differs across instances"

    rng = np.random.default_rng(0)
    actions = [rng.uniform(-1, 1, size=env1.action_space.shape).astype(np.float32) for _ in range(50)]

    def rollout(env):
        env.reset(seed=42)
        traj = []
        for a in actions:
            obs, reward, terminated, truncated, info = env.step(a)
            traj.append((obs["ee_pos"].copy(), reward))
            if terminated or truncated:
                break
        return traj

    t1 = rollout(BinPickingEnv())
    t2 = rollout(BinPickingEnv())
    assert len(t1) == len(t2), "determinism check: trajectories have different lengths"
    for (ee1, r1), (ee2, r2) in zip(t1, t2):
        assert np.array_equal(ee1, ee2), "determinism check: ee_pos diverged"
        assert r1 == r2, "determinism check: reward diverged"
    print("run_determinism_check: OK (reset(seed=...) and action-sequence determinism both hold)")


if __name__ == "__main__":
    run_gymnasium_check_env()
    run_random_rollout()
    run_scripted_p_controller_reward_check()
    run_determinism_check()
    print("check_env.py: ALL CHECKS PASSED")
