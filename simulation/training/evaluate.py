"""Load a saved PPO checkpoint and run deterministic evaluation episodes. Low-but-nonzero success
at smoke-test training budgets is an acceptable outcome, not a failure -- this validates the
pipeline runs end to end, not that the policy has converged (see config/train_ppo.yaml).
"""

from __future__ import annotations

import argparse
import pathlib
import sys

import numpy as np
from stable_baselines3 import PPO

SIM_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SIM_ROOT))

from sim_env.bin_picking_env import BinPickingEnv  # noqa: E402
from sim_env.vision_wrapper import VisionWrapper  # noqa: E402


def evaluate(checkpoint_path: str, profile: str, n_episodes: int = 5) -> dict:
    """Deterministic eval over seeds 1000..1000+n_episodes-1. `touched`/`grasped` come from
    BinPickingEnv's own per-step info dict (episode-cumulative "ever true" flags) rather than
    reaching into env internals, so this stays correct for any env that exposes the same info
    contract (state or vision profile alike)."""
    model = PPO.load(checkpoint_path)
    env = BinPickingEnv()
    if profile == "vision":
        env = VisionWrapper(env)

    rewards, lengths, successes, touches, grasps = [], [], [], [], []
    for ep in range(n_episodes):
        obs, info = env.reset(seed=1000 + ep)
        done = False
        ep_reward = 0.0
        ep_length = 0
        while not done:
            action, _ = model.predict(obs, deterministic=True)
            obs, reward, terminated, truncated, info = env.step(action)
            ep_reward += reward
            ep_length += 1
            done = terminated or truncated
        rewards.append(ep_reward)
        lengths.append(ep_length)
        successes.append(bool(info.get("success", False)))
        touches.append(bool(info.get("touched", False)))
        grasps.append(bool(info.get("grasped", False)))

    result = {
        "mean_reward": float(np.mean(rewards)),
        "mean_episode_length": float(np.mean(lengths)),
        "success_rate": float(np.mean(successes)),
        "contact_rate": float(np.mean(touches)),
        "grasp_rate": float(np.mean(grasps)),
        "n_episodes": n_episodes,
    }
    print(f"evaluate: mean_reward={result['mean_reward']:.3f}, mean_episode_length={result['mean_episode_length']:.1f}, "
          f"success_rate={result['success_rate']:.2f}, contact_rate={result['contact_rate']:.2f}, "
          f"grasp_rate={result['grasp_rate']:.2f} over {n_episodes} episodes")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("checkpoint")
    parser.add_argument("--profile", choices=["state", "vision"], default="state")
    parser.add_argument("--episodes", type=int, default=5)
    args = parser.parse_args()
    evaluate(args.checkpoint, args.profile, args.episodes)
