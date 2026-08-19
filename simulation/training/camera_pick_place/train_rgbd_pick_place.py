"""PPO trainer for virtual RGB-D source-box to destination-box cube transfer."""

from __future__ import annotations

import os

# Must be set before numpy/mujoco import -- see train_ppo_pick_place.py's identical guard: with
# SubprocVecEnv, each worker process otherwise lets its BLAS library grab every core for itself,
# so workers spend more time fighting each other for CPU than stepping/rendering the sim.
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

import argparse
import json
import pathlib
import sys

import yaml
from stable_baselines3 import PPO
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.vec_env import DummyVecEnv, SubprocVecEnv

SIM_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(SIM_ROOT))

from sim_env.rgbd_vision_wrapper import RGBDVisionWrapper  # noqa: E402
from sim_env.suction_pick_place_env import SuctionPickPlaceEnv  # noqa: E402
from training.camera_pick_place.rgbd_feature_extractor import RGBDProprioExtractor  # noqa: E402
from training.camera_pick_place.rgbd_automation import RGBDArtifactCallback  # noqa: E402

CONFIG_PATH = SIM_ROOT / "config" / "camera_rgbd_pick_place_train.yaml"
RUNS_ROOT = pathlib.Path(__file__).resolve().parent / "runs"


def _make_one(seed: int):
    def _make():
        env = RGBDVisionWrapper(SuctionPickPlaceEnv(enable_camera_occlusion_penalty=True))
        env.reset(seed=seed)
        return Monitor(env)

    return _make


def make_env(seed: int = 0, n_envs: int = 1):
    # RGB-D rendering is CPU-bound per env (software MuJoCo rendering, no shared GPU context), so
    # unlike the state-only pick_place task this is worth parallelizing even at modest n_envs --
    # a single DummyVecEnv measured ~7-8 fps end to end, making a 2M-step run take multiple days.
    fns = [_make_one(seed + i) for i in range(n_envs)]
    if n_envs > 1:
        return SubprocVecEnv(fns)
    return DummyVecEnv(fns)


def build_model(env, seed: int = 0, tensorboard_log: str | None = None) -> PPO:
    with CONFIG_PATH.open(encoding="utf-8") as config_file:
        cfg = yaml.safe_load(config_file)
    return PPO(
        "MultiInputPolicy",
        env,
        seed=seed,
        learning_rate=cfg["learning_rate"],
        n_steps=cfg["n_steps"],
        batch_size=cfg["batch_size"],
        ent_coef=cfg["ent_coef"],
        device=cfg["device"],
        # gSDE (use_sde) + squash_output: rgbd_pp_v9-v12 repeatedly saturated -- the raw
        # (pre-clip) Gaussian mean for shoulder_roll/pitch drifted past the [-1,1] action
        # boundary (confirmed by direct inspection of model.policy.get_distribution), so nearly
        # every stochastic sample clipped to the same value with zero executed-action variance,
        # leaving no gradient signal to fine-tune the last few cm of approach -- exactly the
        # "gets close, then can't close the gap" behavior observed. Recurred even on v12's
        # genuinely fresh init, ruling out inherited-optimizer-momentum as the sole cause -- this
        # task/reward combination has a structural tendency toward it. Vanilla PPO's
        # DiagGaussianDistribution has no way to avoid this (loss computed on the unclipped
        # continuous distribution, env only ever executes the clipped value). squash_output only
        # takes effect with use_sde=True in SB3 (StateDependentNoiseDistribution) -- together they
        # give a tanh-bounded action with a real gradient everywhere, including near the boundary,
        # instead of a dead zone past it. Also switches exploration from step-independent Gaussian
        # noise to gSDE's state-dependent noise (resampled every sde_sample_freq steps) -- smoother,
        # more physically plausible exploration for continuous robot control, the scenario gSDE was
        # designed for. Architecture change -- invalidates old checkpoints, requires a fresh init.
        use_sde=True,
        sde_sample_freq=4,
        policy_kwargs={
            "features_extractor_class": RGBDProprioExtractor,
            "features_extractor_kwargs": {"features_dim": cfg["features_dim"]},
            "net_arch": cfg["policy_kwargs"]["net_arch"],
            "squash_output": True,
        },
        tensorboard_log=tensorboard_log,
        verbose=1,
    )


def train(total_timesteps: int, run_name: str, seed: int = 0, init_checkpoint: str | None = None,
          eval_freq: int | None = None, log_freq: int | None = None) -> pathlib.Path:
    with CONFIG_PATH.open(encoding="utf-8") as config_file:
        cfg = yaml.safe_load(config_file)
    if eval_freq is not None: cfg["eval_freq"] = eval_freq
    if log_freq is not None: cfg["log_freq"] = log_freq
    run_dir = RUNS_ROOT / run_name
    run_dir.mkdir(parents=True, exist_ok=True)
    logs_dir = run_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "config.yaml").write_text(CONFIG_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    (run_dir / "experiment.json").write_text(json.dumps({"experiment_id": run_name, "parent_checkpoint": init_checkpoint,
        "observation_contract": "RGB-D head camera + robot proprioception; no cube/destination ground truth", "status": "running"}, indent=2), encoding="utf-8")
    env = make_env(seed, cfg.get("n_envs", 1))
    try:
        model = PPO.load(init_checkpoint, env=env, tensorboard_log=str(logs_dir), device=cfg["device"]) if init_checkpoint else build_model(env, seed, tensorboard_log=str(logs_dir))
        # Keep this runnable in the minimal project environment; SB3's rich/tqdm progress bar
        # is an optional extra and must not be a hidden training dependency.
        callback = RGBDArtifactCallback(run_dir, total_timesteps, cfg, seed)
        model.learn(total_timesteps=total_timesteps, callback=callback, tb_log_name=run_name, progress_bar=False)
        output_path = run_dir / "rgbd_pick_place_policy"
        model.save(output_path)
        record = json.loads((run_dir / "experiment.json").read_text(encoding="utf-8"))
        record.update({"status": "complete", "final_checkpoint": str(output_path.with_suffix(".zip"))})
        (run_dir / "experiment.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
        return output_path.with_suffix(".zip")
    finally:
        env.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--timesteps", type=int, default=200_000)
    parser.add_argument("--run-name", default="rgbd_pp_v1")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--init-checkpoint", default=None)
    parser.add_argument("--eval-freq", type=int, default=None)
    parser.add_argument("--log-freq", type=int, default=None)
    args = parser.parse_args()
    print(f"saved {train(args.timesteps, args.run_name, args.seed, args.init_checkpoint, args.eval_freq, args.log_freq)}")
