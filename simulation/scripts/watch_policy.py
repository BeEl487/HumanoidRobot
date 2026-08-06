"""Run a trained PPO checkpoint interactively in the MuJoCo viewer, for local viewing.

Usage:
  python watch_policy.py --checkpoint ../training/checkpoints/ppo_state_smoke_test.zip --profile state
  python watch_policy.py --checkpoint ../training/checkpoints/ppo_vision_smoke_test.zip --profile vision

Note: these checkpoints are smoke-test artifacts (Milestone 8) trained for a few minutes just to
prove the pipeline runs end to end -- expect unrefined, largely unsuccessful behavior, not a
solved task. Re-run with a longer training budget (training/train_ppo.py --timesteps N) for
anything more than that.
"""

from __future__ import annotations

import argparse
import pathlib
import sys
import time

import mujoco
import mujoco.viewer

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from sim_env.bin_picking_env import BinPickingEnv  # noqa: E402
from sim_env.vision_wrapper import VisionWrapper  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--profile", choices=["state", "vision"], default="state")
    parser.add_argument("--episodes", type=int, default=0, help="0 = loop forever")
    args = parser.parse_args()

    from stable_baselines3 import PPO
    model = PPO.load(args.checkpoint)

    env = BinPickingEnv()
    if args.profile == "vision":
        env = VisionWrapper(env)

    mj_model, mj_data = env.unwrapped.model, env.unwrapped.data
    with mujoco.viewer.launch_passive(mj_model, mj_data) as viewer:
        ep = 0
        while viewer.is_running() and (args.episodes == 0 or ep < args.episodes):
            obs, info = env.reset()
            terminated = truncated = False
            while viewer.is_running() and not (terminated or truncated):
                action, _ = model.predict(obs, deterministic=True)
                obs, reward, terminated, truncated, info = env.step(action)
                viewer.sync()
                time.sleep(1.0 / env.control_hz)
            ep += 1


if __name__ == "__main__":
    main()
