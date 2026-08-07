"""SB3 PPO training entrypoint -- smoke-tests the RL pipeline end to end (state-based and
vision-based profiles, config/train_ppo.yaml). NOT expected to converge/solve the task at these
budgets: this proves the pipeline runs without crashing, not that the policy is good.
"""

from __future__ import annotations

import os

# See training/pick_place/train_ppo_pick_place.py's identical block for why: caps each
# SubprocVecEnv worker to 1 BLAS thread so they don't contend with each other for cores.
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

import argparse
import pathlib
import sys

import yaml
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import CheckpointCallback
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.vec_env import DummyVecEnv, SubprocVecEnv

SIM_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SIM_ROOT))

from sim_env.bin_picking_env import BinPickingEnv  # noqa: E402
from sim_env.vision_wrapper import VisionWrapper  # noqa: E402
from progress_artifacts import ProgressArtifactCallback  # noqa: E402

CONFIG_PATH = SIM_ROOT / "config" / "train_ppo.yaml"
CHECKPOINT_DIR = SIM_ROOT / "training" / "checkpoints"
LOG_DIR = SIM_ROOT / "training" / "logs"
RUNS_DIR = SIM_ROOT / "training" / "runs"


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
    artifact_interval: int | None = 200_000,
    artifact_episodes: int = 10,
) -> pathlib.Path:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)["profiles"][profile]

    timesteps = total_timesteps if total_timesteps is not None else cfg["total_timesteps"]
    name = checkpoint_name or f"ppo_{profile}_smoke_test"
    run = run_name or profile

    n_envs = cfg.get("n_envs", 1)
    if n_envs > 1:
        env = SubprocVecEnv([make_env(profile) for _ in range(n_envs)])
    else:
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

    if artifact_interval:
        run_dir = RUNS_DIR / run
        callbacks.append(ProgressArtifactCallback(
            run_dir=run_dir, profile=profile, total_timesteps=timesteps,
            interval_steps=artifact_interval, eval_episodes=artifact_episodes, run_name=run,
        ))
        print(f"Progress dashboard: {run_dir / 'dashboard.html'} "
              f"(serve with: python serve_dashboard.py {run_dir})")

    model.learn(total_timesteps=timesteps, callback=callbacks or None, tb_log_name=run)

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
    parser.add_argument("--run-name", default=None, help="TensorBoard run name and dashboard run dir (defaults to profile)")
    parser.add_argument("--artifact-interval", type=int, default=200_000,
                         help="checkpoint + eval + video + dashboard update every N timesteps (0 to disable)")
    parser.add_argument("--artifact-episodes", type=int, default=10,
                         help="deterministic eval episodes per progress-dashboard update")
    args = parser.parse_args()
    train(
        args.profile, total_timesteps=args.timesteps, checkpoint_name=args.checkpoint_name,
        save_freq=args.save_freq, run_name=args.run_name,
        artifact_interval=args.artifact_interval or None, artifact_episodes=args.artifact_episodes,
    )
