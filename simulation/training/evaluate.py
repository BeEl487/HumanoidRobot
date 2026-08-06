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
    model = PPO.load(checkpoint_path)
    env = BinPickingEnv()
    if profile == "vision":
        env = VisionWrapper(env)

    rewards, successes = [], []
    for ep in range(n_episodes):
        obs, info = env.reset(seed=1000 + ep)
        done = False
        ep_reward = 0.0
        while not done:
            action, _ = model.predict(obs, deterministic=True)
            obs, reward, terminated, truncated, info = env.step(action)
            ep_reward += reward
            done = terminated or truncated
        rewards.append(ep_reward)
        successes.append(bool(info.get("success", False)))

    result = {"mean_reward": float(np.mean(rewards)), "success_rate": float(np.mean(successes))}
    print(f"evaluate: mean_reward={result['mean_reward']:.3f}, success_rate={result['success_rate']:.2f} "
          f"over {n_episodes} episodes")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("checkpoint")
    parser.add_argument("--profile", choices=["state", "vision"], default="state")
    parser.add_argument("--episodes", type=int, default=5)
    args = parser.parse_args()
    evaluate(args.checkpoint, args.profile, args.episodes)
