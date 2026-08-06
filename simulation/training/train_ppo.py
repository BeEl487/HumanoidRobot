"""SB3 PPO training entrypoint -- smoke-tests the RL pipeline end to end (state-based and
vision-based profiles, config/train_ppo.yaml). NOT expected to converge/solve the task at these
budgets: this proves the pipeline runs without crashing, not that the policy is good.
"""

from __future__ import annotations

import argparse
import pathlib
import sys

import yaml
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import CheckpointCallback
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.vec_env import DummyVecEnv

SIM_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SIM_ROOT))

from sim_env.bin_picking_env import BinPickingEnv  # noqa: E402
from sim_env.vision_wrapper import VisionWrapper  # noqa: E402

CONFIG_PATH = SIM_ROOT / "config" / "train_ppo.yaml"
CHECKPOINT_DIR = SIM_ROOT / "training" / "checkpoints"
LOG_DIR = SIM_ROOT / "training" / "logs"


def make_env(profile: str):
    def _make():
        env = BinPickingEnv()
        if profile == "vision":
            env = VisionWrapper(env)
        return Monitor(env)
    return _make


def train(
    profile: str,
    total_timesteps: int | None = None,
    checkpoint_name: str | None = None,
    save_freq: int | None = None,
    run_name: str | None = None,
) -> pathlib.Path:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)["profiles"][profile]

    timesteps = total_timesteps if total_timesteps is not None else cfg["total_timesteps"]
    name = checkpoint_name or f"ppo_{profile}_smoke_test"

    env = DummyVecEnv([make_env(profile)])
    model = PPO(
        cfg["policy"], env,
        learning_rate=cfg["learning_rate"], n_steps=cfg["n_steps"], batch_size=cfg["batch_size"],
        ent_coef=cfg.get("ent_coef", 0.0),  # SB3 default is 0.0 (no entropy bonus); see ASSUMPTIONS.md v4 note
        seed=cfg.get("seed", 0), device=cfg.get("device", "auto"),
        tensorboard_log=str(LOG_DIR / profile), verbose=1,
    )

    callbacks = []
    if save_freq:
        progress_dir = CHECKPOINT_DIR / f"{name}_progress"
        progress_dir.mkdir(parents=True, exist_ok=True)
        callbacks.append(CheckpointCallback(save_freq=save_freq, save_path=str(progress_dir), name_prefix=name))

    model.learn(total_timesteps=timesteps, callback=callbacks or None, tb_log_name=run_name or profile)

    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    checkpoint_path = CHECKPOINT_DIR / f"{name}.zip"
    model.save(str(checkpoint_path))
    print(f"Saved checkpoint to {checkpoint_path}")
    return checkpoint_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", choices=["state", "vision"], default="state")
    parser.add_argument("--timesteps", type=int, default=None, help="override config total_timesteps")
    parser.add_argument("--checkpoint-name", default=None)
    parser.add_argument("--save-freq", type=int, default=None, help="save a progress checkpoint every N timesteps")
    parser.add_argument("--run-name", default=None, help="TensorBoard run name (defaults to profile)")
    args = parser.parse_args()
    train(
        args.profile, total_timesteps=args.timesteps, checkpoint_name=args.checkpoint_name,
        save_freq=args.save_freq, run_name=args.run_name,
    )
