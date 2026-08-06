"""Render a trained PPO checkpoint's rollout to two GIFs: an external viewing angle (watching the
robot) and the robot's own head camera POV (config/camera.yaml's head_camera -- seeing what it
sees). Both are captured from the same deterministic rollout, so they're perfectly in sync frame
for frame. Useful for demos/debugging without needing a local interactive display (see
watch_policy.py for that).
"""

from __future__ import annotations

import argparse
import pathlib
import sys

import imageio
import mujoco
import numpy as np
import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from sim_env.bin_picking_env import BinPickingEnv  # noqa: E402
from sim_env.vision_wrapper import VisionWrapper  # noqa: E402

CAMERA_CONFIG_PATH = pathlib.Path(__file__).resolve().parent.parent / "config" / "camera.yaml"


def render_rollout(
    checkpoint_path: str,
    profile: str,
    out_path: pathlib.Path,
    seed: int = 0,
    fps: int = 20,
    pov_out_path: pathlib.Path | None = None,
) -> int:
    from stable_baselines3 import PPO
    model = PPO.load(checkpoint_path)

    env = BinPickingEnv()
    if profile == "vision":
        env = VisionWrapper(env)
    mj_model, mj_data = env.unwrapped.model, env.unwrapped.data

    with open(CAMERA_CONFIG_PATH, encoding="utf-8") as f:
        head_cam_name = yaml.safe_load(f)["name"]

    renderer = mujoco.Renderer(mj_model, height=480, width=640)
    ext_cam = mujoco.MjvCamera()
    mujoco.mjv_defaultFreeCamera(mj_model, ext_cam)
    ext_cam.lookat = [0.15, 0.0, 0.75]
    ext_cam.distance = 1.1
    ext_cam.azimuth = 130
    ext_cam.elevation = -20

    obs, info = env.reset(seed=seed)
    ext_frames, pov_frames = [], []
    terminated = truncated = False
    steps = 0
    while not (terminated or truncated):
        action, _ = model.predict(obs, deterministic=True)
        obs, reward, terminated, truncated, info = env.step(action)

        renderer.update_scene(mj_data, camera=ext_cam)
        ext_frames.append(renderer.render())

        if pov_out_path is not None:
            renderer.update_scene(mj_data, camera=head_cam_name)
            pov_frames.append(renderer.render())

        steps += 1

    out_path.parent.mkdir(parents=True, exist_ok=True)
    imageio.mimsave(str(out_path), ext_frames, fps=fps)
    msg = (f"Saved {steps}-step rollout ({len(ext_frames)} frames) to {out_path}. "
           f"Episode ended: {'success' if info.get('success') else 'no success'} "
           f"({'terminated' if terminated else 'truncated'}).")
    if pov_out_path is not None:
        pov_out_path.parent.mkdir(parents=True, exist_ok=True)
        imageio.mimsave(str(pov_out_path), pov_frames, fps=fps)
        msg += f" Head-camera POV saved to {pov_out_path}."
    print(msg)
    return steps


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--profile", choices=["state", "vision"], default="state")
    parser.add_argument("--out", default="../docs/policy_rollout.gif")
    parser.add_argument("--pov-out", default=None, help="also render the robot's head-camera POV to this path")
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    pov = pathlib.Path(args.pov_out) if args.pov_out else None
    render_rollout(args.checkpoint, args.profile, pathlib.Path(args.out), seed=args.seed, pov_out_path=pov)
