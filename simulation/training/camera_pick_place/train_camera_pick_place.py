from __future__ import annotations

import pathlib
import sys

import gymnasium as gym
import numpy as np
import yaml
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv, VecMonitor

SIM_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(SIM_ROOT))
sys.path.insert(0, str(SIM_ROOT / "scripts"))

from sim_env.bin_picking_env import BinPickingEnv  # noqa: E402
from sim_env.vision_wrapper import VisionWrapper  # noqa: E402

CONFIG_PATH = SIM_ROOT / "config" / "camera_pick_place_train.yaml"


def _load_config() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def make_env(seed: int = 0, include_privileged_state: bool = False):
    def _make_single_env():
        env = BinPickingEnv()
        env = VisionWrapper(env, include_privileged_state=include_privileged_state)
        return env

    env = DummyVecEnv([_make_single_env])
    env = VecMonitor(env)
    return env


def build_model(env: gym.Env, total_timesteps: int = 1000, seed: int = 0) -> PPO:
    cfg = _load_config()
    policy_kwargs = dict(cfg.get("policy_kwargs", {}))
    model = PPO(
        "MultiInputPolicy",
        env,
        verbose=1,
        seed=seed,
        n_steps=cfg.get("n_steps", 64),
        batch_size=cfg.get("batch_size", 64),
        learning_rate=cfg.get("learning_rate", 3e-4),
        ent_coef=cfg.get("ent_coef", 0.0),
        policy_kwargs=policy_kwargs,
        device=cfg.get("device", "auto"),
    )
    return model


def train_model(total_timesteps: int | None = None, seed: int = 0) -> PPO:
    env = make_env(seed=seed)
    try:
        model = build_model(env, total_timesteps=total_timesteps or 1000, seed=seed)
        model.learn(total_timesteps=total_timesteps or 1000, progress_bar=True)
        return model
    finally:
        env.close()
