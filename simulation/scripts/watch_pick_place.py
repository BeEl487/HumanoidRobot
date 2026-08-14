"""Run a trained pick-place PPO checkpoint interactively in the MuJoCo viewer.

Loops episodes forever (or for --episodes N), each with a freshly randomized
cube start position (domain randomization already happens inside env.reset()).
Uses eval_mode=True so curriculum shortcuts are disabled and every episode is
the full pick -> carry -> place task.

Usage:
  python watch_pick_place.py --checkpoint ../training/pick_place/runs/pp_v26/checkpoints/final.zip
  python watch_pick_place.py --checkpoint ... --episodes 10 --slow 2.0
"""

from __future__ import annotations

import argparse
import pathlib
import sys
import time

import mujoco
import mujoco.viewer

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from sim_env.suction_pick_place_env import SuctionPickPlaceEnv  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--episodes", type=int, default=0, help="0 = loop forever")
    parser.add_argument("--slow", type=float, default=1.0, help="playback slowdown factor")
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()

    from stable_baselines3 import PPO
    model = PPO.load(args.checkpoint)

    env = SuctionPickPlaceEnv(eval_mode=True)

    successes = 0
    ep = 0
    with mujoco.viewer.launch_passive(env.model, env.data) as viewer:
        while viewer.is_running() and (args.episodes == 0 or ep < args.episodes):
            seed = None if args.seed is None else args.seed + ep
            obs, info = env.reset(seed=seed)
            terminated = truncated = False
            ep_reward = 0.0
            while viewer.is_running() and not (terminated or truncated):
                action, _ = model.predict(obs, deterministic=True)
                obs, reward, terminated, truncated, info = env.step(action)
                ep_reward += reward
                viewer.sync()
                time.sleep(args.slow / env.control_hz)
            ep += 1
            placed = bool(info.get("success", False))
            successes += placed
            print(
                f"episode {ep}: reward={ep_reward:.2f} place_success={placed} "
                f"({successes}/{ep} = {successes / ep:.0%})"
            )


if __name__ == "__main__":
    main()
