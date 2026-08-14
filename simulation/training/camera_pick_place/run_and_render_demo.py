from __future__ import annotations

import pathlib
import sys

import imageio
import mujoco
import numpy as np
import yaml

SIM_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(SIM_ROOT))

from training.camera_pick_place.train_camera_pick_place import build_model, make_env  # noqa: E402

CAMERA_CONFIG_PATH = SIM_ROOT / "config" / "camera.yaml"
OUT_DIR = pathlib.Path(__file__).resolve().parent / "runs" / "demo_camera_rollout"


def render_demo(checkpoint_path: pathlib.Path, total_timesteps: int = 2000, seed: int = 0) -> None:
    env = make_env(seed=seed)
    try:
        model = build_model(env, total_timesteps=total_timesteps, seed=seed)
        model.learn(total_timesteps=total_timesteps, progress_bar=False)
        model.save(checkpoint_path)

        single_env = env.envs[0]
        mj_model = single_env.env.unwrapped.model
        mj_data = single_env.env.unwrapped.data

        with open(CAMERA_CONFIG_PATH, encoding="utf-8") as f:
            head_cam_name = yaml.safe_load(f)["name"]

        ext_cam = mujoco.MjvCamera()
        mujoco.mjv_defaultFreeCamera(mj_model, ext_cam)
        ext_cam.lookat = [0.15, 0.0, 0.75]
        ext_cam.distance = 1.1
        ext_cam.azimuth = 130
        ext_cam.elevation = -20

        renderer = mujoco.Renderer(mj_model, height=480, width=640)
        obs, info = env.reset(seed=seed)
        ext_frames, pov_frames = [], []
        terminated = truncated = False

        while not (terminated or truncated):
            action, _ = model.predict(obs, deterministic=True)
            obs, reward, terminated, truncated, info = env.step(action)

            renderer.update_scene(mj_data, camera=ext_cam)
            ext_frames.append(renderer.render())
            renderer.update_scene(mj_data, camera=head_cam_name)
            pov_frames.append(renderer.render())

        OUT_DIR.mkdir(parents=True, exist_ok=True)
        imageio.mimsave(str(OUT_DIR / "demo_rollout.gif"), ext_frames, fps=12)
        imageio.mimsave(str(OUT_DIR / "demo_rollout_pov.gif"), pov_frames, fps=12)
        print(f"Saved rollout to {OUT_DIR}")
    finally:
        env.close()


if __name__ == "__main__":
    checkpoint_path = pathlib.Path(__file__).resolve().parent / "runs" / "demo_camera_model.zip"
    render_demo(checkpoint_path)
