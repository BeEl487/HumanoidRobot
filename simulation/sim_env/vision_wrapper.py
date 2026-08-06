"""Adds an RGB camera observation on top of BinPickingEnv's state-only observations, layered as
a gymnasium.ObservationWrapper so the fast state-only env (Milestone 6) stays usable standalone
(e.g. as Milestone 8's state-based training baseline) rather than being replaced outright.
"""

from __future__ import annotations

import pathlib

import gymnasium as gym
import mujoco
import numpy as np
import yaml
from gymnasium import spaces

SIM_ROOT = pathlib.Path(__file__).resolve().parent.parent
CAMERA_CONFIG_PATH = SIM_ROOT / "config" / "camera.yaml"


class VisionWrapper(gym.ObservationWrapper):
    """include_privileged_state=True (default) keeps the ground-truth object_pos/object_present
    keys alongside the rendered image -- useful for future asymmetric actor-critic experiments
    (critic sees privileged state, policy sees only vision) -- not required for a first vision
    baseline, so set False for a pure image-only observation space."""

    def __init__(self, env: gym.Env, include_privileged_state: bool = True):
        super().__init__(env)
        with open(CAMERA_CONFIG_PATH, encoding="utf-8") as f:
            cam_cfg = yaml.safe_load(f)
        self._camera_name = cam_cfg["name"]
        width, height = cam_cfg["resolution_default"]
        self._renderer = mujoco.Renderer(self.env.unwrapped.model, height=height, width=width)
        self.include_privileged_state = include_privileged_state

        obs_spaces = dict(self.env.observation_space.spaces)
        obs_spaces["rgb"] = spaces.Box(0, 255, shape=(height, width, 3), dtype=np.uint8)
        if not include_privileged_state:
            obs_spaces.pop("object_pos", None)
            obs_spaces.pop("object_present", None)
        self.observation_space = spaces.Dict(obs_spaces)

    def observation(self, obs: dict) -> dict:
        self._renderer.update_scene(self.env.unwrapped.data, camera=self._camera_name)
        rgb = self._renderer.render()

        obs = dict(obs)
        obs["rgb"] = rgb
        if not self.include_privileged_state:
            obs.pop("object_pos", None)
            obs.pop("object_present", None)
        return obs
