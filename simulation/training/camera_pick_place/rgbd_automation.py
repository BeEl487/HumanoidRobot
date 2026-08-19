"""Pick-and-Place-style artifact lifecycle for RGB-D PPO training."""

from __future__ import annotations

import datetime
import json
import pathlib
import sys
import time
from collections import deque

import imageio
import mujoco
import numpy as np
from PIL import Image, ImageDraw
from stable_baselines3.common.callbacks import BaseCallback

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent / "scripts"))

from training.pick_place import self_monitor
from training.camera_pick_place.task_logging import TaskMetricsLogger
from sim_env.rgbd_vision_wrapper import RGBDVisionWrapper
from sim_env.suction_pick_place_env import SuctionPickPlaceEnv
from generate_camera_dashboard import generate_dashboard  # noqa: E402


def eval_env() -> RGBDVisionWrapper:
    return RGBDVisionWrapper(SuctionPickPlaceEnv(
        eval_mode=True, enable_camera_occlusion_penalty=True, close_approach_range_m_override=0.12,
    ))


def evaluate(model, episodes: int, seed: int, trajectory_path: pathlib.Path | None = None) -> dict:
    env = eval_env()
    rewards, successes, attachments, stages, trajectories = [], [], [], [], []
    try:
        for episode in range(episodes):
            obs, _ = env.reset(seed=seed + episode)
            done = False
            reward_sum, path = 0.0, []
            while not done:
                action, _ = model.predict(obs, deterministic=True)
                obs, reward, terminated, truncated, info = env.step(action)
                reward_sum += reward
                path.append([*info["ee_pos"], *info["cube_pos"], int(info["stage"])])
                done = terminated or truncated
            rewards.append(reward_sum)
            successes.append(bool(info.get("success", False)))
            attachments.append(bool(info.get("attached", False)))
            stages.append(int(info.get("stage", 0)))
            trajectories.append(np.asarray(path, dtype=np.float32))
    finally:
        env.close()
    if trajectory_path is not None:
        trajectory_path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(trajectory_path, *trajectories)
    return {"mean_reward": float(np.mean(rewards)), "success_rate": float(np.mean(successes)),
            "pick_success_rate": float(np.mean(attachments)), "mean_max_stage": float(np.mean(stages)),
            "n_episodes": episodes}


# Same external-camera framing as training/pick_place/train_ppo_pick_place.py, so both tasks'
# dashboards read the same way -- a fixed 3rd-person view showing the whole robot/workspace, not
# the policy's own head-camera POV (that POV is still rendered separately, below, since it's
# literally what this task's policy receives and is useful for diagnosing vision failures).
EXT_CAM_LOOKAT = [0.16, 0.0, 0.78]
EXT_CAM_DISTANCE = 0.85
EXT_CAM_AZIMUTH = 140
EXT_CAM_ELEVATION = -25


def _overlay(frame: np.ndarray, step: int, info: dict, reward: float) -> np.ndarray:
    img = Image.fromarray(frame).convert("RGB")
    draw = ImageDraw.Draw(img, "RGBA")
    draw.rectangle((0, 0, 225, 78), fill=(0, 0, 0, 160))
    draw.text((6, 5), f"RGB-D eval step: {step}\nstage: {info['stage']}  attached: {info['attached']}\n"
              f"ee->cube: {info['ee_to_cube_dist']:.3f}m\nreward: {reward:+.2f}", fill="white")
    return np.asarray(img)


def render_video(model, path: pathlib.Path, pov_path: pathlib.Path, seed: int) -> None:
    """Renders two views of the same deterministic rollout: `path` (3rd-person external, whole
    robot+workspace visible -- the primary/default video) and `pov_path` (head-camera POV, exactly
    what the policy's RGB channel receives, sans depth)."""
    env = eval_env()
    renderer = mujoco.Renderer(env.unwrapped.model, height=480, width=640)
    ext_cam = mujoco.MjvCamera()
    mujoco.mjv_defaultFreeCamera(env.unwrapped.model, ext_cam)
    ext_cam.lookat, ext_cam.distance = EXT_CAM_LOOKAT, EXT_CAM_DISTANCE
    ext_cam.azimuth, ext_cam.elevation = EXT_CAM_AZIMUTH, EXT_CAM_ELEVATION
    ext_frames, pov_frames = [], []
    try:
        obs, _ = env.reset(seed=seed)
        done, step = False, 0
        while not done:
            action, _ = model.predict(obs, deterministic=True)
            obs, reward, terminated, truncated, info = env.step(action)
            renderer.update_scene(env.unwrapped.data, camera=ext_cam)
            ext_frames.append(_overlay(renderer.render(), step, info, reward))
            renderer.update_scene(env.unwrapped.data, camera="head_camera")
            pov_frames.append(_overlay(renderer.render(), step, info, reward))
            step += 1; done = terminated or truncated
    finally:
        renderer.close(); env.close()
    path.parent.mkdir(parents=True, exist_ok=True)
    pov_path.parent.mkdir(parents=True, exist_ok=True)
    imageio.mimsave(path, ext_frames, fps=20)
    imageio.mimsave(pov_path, pov_frames, fps=20)


class RGBDArtifactCallback(BaseCallback):
    def __init__(self, run_dir: pathlib.Path, total_steps: int, cfg: dict, seed: int):
        super().__init__()
        self.run_dir, self.total_steps, self.cfg, self.seed = run_dir, total_steps, cfg, seed
        self.log_freq, self.eval_freq, self.analysis_freq = cfg["log_freq"], cfg["eval_freq"], cfg["analysis_freq"]
        self.video_freq = cfg.get("video_freq", self.eval_freq)
        self.metrics = self_monitor.MetricsLogger(run_dir / "metrics_log.csv")
        self.task_metrics = TaskMetricsLogger(run_dir / "task_logs" / "rgbd_pick_place.csv", task_name="rgbd_pick_place", run_name=run_dir.name)
        self.recent_rewards, self.recent_success = deque(maxlen=100), deque(maxlen=100)
        self.last_log = self.last_eval = self.last_analysis = self.last_video = 0
        self.last_time, self.last_step, self.fps = time.time(), 0, None
        (run_dir / "checkpoints").mkdir(parents=True, exist_ok=True)
        (run_dir / "videos").mkdir(exist_ok=True); (run_dir / "trajectories").mkdir(exist_ok=True)

    def _on_step(self) -> bool:
        infos, dones = self.locals.get("infos", []), self.locals.get("dones", [])
        for info, done in zip(infos, dones):
            if done and "episode" in info:
                self.recent_rewards.append(info["episode"]["r"]); self.recent_success.append(bool(info.get("success", False)))
        if self.num_timesteps - self.last_log >= self.log_freq:
            now = time.time(); self.fps = (self.num_timesteps - self.last_step) / max(now - self.last_time, 1e-6)
            self.last_time, self.last_step, self.last_log = now, self.num_timesteps, self.num_timesteps
            info = infos[0] if infos else {}; values = self.model.logger.name_to_value
            row = {"global_step": self.num_timesteps, "success_rate": np.mean(self.recent_success) if self.recent_success else "",
                "avg_reward_100": np.mean(self.recent_rewards) if self.recent_rewards else "", "policy_loss": values.get("train/policy_gradient_loss"),
                "value_loss": values.get("train/value_loss"), "entropy": -values["train/entropy_loss"] if "train/entropy_loss" in values else "",
                "learning_rate": values.get("train/learning_rate"), "fps": self.fps, "eta_seconds": (self.total_steps-self.num_timesteps)/self.fps,
                "ee_x": info.get("ee_pos", [None]*3)[0], "ee_y": info.get("ee_pos", [None]*3)[1], "ee_z": info.get("ee_pos", [None]*3)[2],
                "cube_x": info.get("cube_pos", [None]*3)[0], "cube_y": info.get("cube_pos", [None]*3)[1], "cube_z": info.get("cube_pos", [None]*3)[2],
                "ee_to_cube_dist": info.get("ee_to_cube_dist"), "cube_to_goal_dist": info.get("carry_dist"), "is_grasped": info.get("is_attached"),
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()}
            self.metrics.log_row(row)
            self.task_metrics.log_row(row)
        if self.num_timesteps - self.last_eval >= self.eval_freq or self.num_timesteps - self.last_video >= self.video_freq:
            if self.num_timesteps - self.last_eval >= self.eval_freq:
                self.last_eval = self.num_timesteps
            self.last_video = self.num_timesteps
            self._cycle(final=False)
        if self.num_timesteps - self.last_analysis >= self.analysis_freq:
            self.last_analysis = self.num_timesteps
            window = self_monitor.analyze_window(self.run_dir / "metrics_log.csv", self.num_timesteps, self.cfg["stall_window_steps"])
            stalled = self_monitor.is_stalled(window)
            self_monitor.write_analysis_report(self.run_dir, self.num_timesteps, window, None, stalled, self.fps, self.total_steps)
            if stalled:
                self._cycle(final=True); (self.run_dir / "STALL_DETECTED.flag").write_text(f"stalled at {self.num_timesteps}\n")
                return False
        return True

    def _cycle(self, final: bool) -> None:
        step = self.num_timesteps; checkpoint = self.run_dir / "checkpoints" / f"ckpt_{step}.zip"; self.model.save(checkpoint)
        metrics = evaluate(self.model, self.cfg["n_eval_episodes"], self.seed + step, self.run_dir / "trajectories" / f"ckpt_{step}.npz")
        video = self.run_dir / "videos" / f"ckpt_{step}.mp4"
        video_pov = self.run_dir / "videos" / f"ckpt_{step}_pov.mp4"
        render_video(self.model, video, video_pov, self.seed + step)
        manifest_path = self.run_dir / "manifest.json"; manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {"checkpoints": []}
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        manifest["checkpoints"].append({
            "step": step, "checkpoint": str(checkpoint.relative_to(self.run_dir)),
            "video": str(video.relative_to(self.run_dir)), "video_pov": str(video_pov.relative_to(self.run_dir)),
            "final": final, "timestamp": timestamp, **metrics,
        })
        manifest["total_timesteps_target"] = self.total_steps
        manifest["last_updated"] = timestamp
        manifest_path.write_text(json.dumps(manifest, indent=2))
        generate_dashboard(self.run_dir)

    def _on_training_end(self) -> None:
        final_step = self.num_timesteps
        final_video = self.run_dir / "videos" / f"ckpt_{final_step}.mp4"
        if self.last_eval != final_step or not final_video.exists():
            self._cycle(final=True)
