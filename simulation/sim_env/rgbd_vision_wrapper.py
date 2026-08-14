"""Realistic RGB-D and proprioceptive observations for MuJoCo manipulation tasks."""

from __future__ import annotations

import pathlib

import gymnasium as gym
import mujoco
import numpy as np
import yaml
from gymnasium import spaces


SIM_ROOT = pathlib.Path(__file__).resolve().parent.parent
CAMERA_CONFIG_PATH = SIM_ROOT / "config" / "camera.yaml"
_PRIVILEGED_KEYS = {"cube_pos", "dest_pos", "object_pos", "object_present"}


class RGBDVisionWrapper(gym.ObservationWrapper):
    """Expose a head-camera RGB-D frame and real-robot-equivalent proprioception.

    RGB-D is rendered from the same virtual head camera used at deployment. Ground-truth object
    and destination poses remain available only to the simulator/reward, never to the policy.
    Joint encoders, forward-kinematic end-effector position, and suction state are retained as
    realistic robot signals.
    """

    def __init__(self, env: gym.Env, depth_max_m: float = 2.0):
        super().__init__(env)
        with CAMERA_CONFIG_PATH.open(encoding="utf-8") as camera_file:
            camera_cfg = yaml.safe_load(camera_file)
        self._camera_name = camera_cfg["name"]
        width, height = camera_cfg["resolution_default"]
        self._renderer = mujoco.Renderer(self.env.unwrapped.model, height=height, width=width)
        self._depth_max_m = depth_max_m

        observation_spaces = {
            key: value
            for key, value in self.env.observation_space.spaces.items()
            if key not in _PRIVILEGED_KEYS
        }
        # Channel-first contract avoids implicit SB3 image transposition and makes RGB + depth
        # concatenation in RGBDProprioExtractor explicit.
        observation_spaces["rgb"] = spaces.Box(0, 255, shape=(3, height, width), dtype=np.uint8)
        observation_spaces["depth"] = spaces.Box(
            0.0, depth_max_m, shape=(1, height, width), dtype=np.float32
        )
        self.observation_space = spaces.Dict(observation_spaces)

    def observation(self, observation: dict) -> dict:
        self._renderer.update_scene(self.env.unwrapped.data, camera=self._camera_name)
        rgb = self._renderer.render()
        self._renderer.enable_depth_rendering()
        try:
            depth = self._renderer.render()
        finally:
            self._renderer.disable_depth_rendering()

        result = {key: value for key, value in observation.items() if key not in _PRIVILEGED_KEYS}
        result["rgb"] = np.moveaxis(rgb, -1, 0)
        result["depth"] = np.clip(depth, 0.0, self._depth_max_m).astype(np.float32)[None, :, :]
        return result

    def close(self) -> None:
        self._renderer.close()
        super().close()
