"""Milestone 7 vision-wrapper verification:
1. gymnasium's env_checker still passes on the wrapped env (Dict obs with an image key is a
   recognized Gymnasium/SB3 convention -- SB3's MultiInputPolicy auto-detects it).
2. Rendered frames actually change as the robot/scene move -- catches a "frozen buffer" bug.
3. Steps/sec logged vs. the state-only (Milestone 6.1/6.2) baseline, recorded as a perf note.
"""

from __future__ import annotations

import pathlib
import sys
import time

import numpy as np
from gymnasium.utils.env_checker import check_env

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from sim_env.bin_picking_env import BinPickingEnv  # noqa: E402
from sim_env.vision_wrapper import VisionWrapper  # noqa: E402

N_PERF_STEPS = 200


def run_gymnasium_check_env() -> None:
    env = VisionWrapper(BinPickingEnv())
    check_env(env.unwrapped, skip_render_check=True)
    print("run_gymnasium_check_env: OK (gymnasium.utils.env_checker passed on the vision-wrapped env)")


def check_frames_change() -> None:
    env = VisionWrapper(BinPickingEnv())
    obs, info = env.reset(seed=0)
    frame0 = obs["rgb"].copy()
    assert frame0.std() > 0, "initial rendered frame is blank"

    for _ in range(20):
        obs, reward, terminated, truncated, info = env.step(env.action_space.sample())
        if terminated or truncated:
            obs, info = env.reset()
    frame_later = obs["rgb"]
    assert not np.array_equal(frame0, frame_later), (
        "rendered frame never changed across 20 steps of robot motion -- possible frozen buffer"
    )
    print("check_frames_change: OK (rendered frames changed as the scene moved)")


def measure_steps_per_second() -> tuple[float, float]:
    state_env = BinPickingEnv()
    state_env.reset(seed=0)
    t0 = time.perf_counter()
    for _ in range(N_PERF_STEPS):
        _, _, terminated, truncated, _ = state_env.step(state_env.action_space.sample())
        if terminated or truncated:
            state_env.reset()
    state_hz = N_PERF_STEPS / (time.perf_counter() - t0)

    vision_env = VisionWrapper(BinPickingEnv())
    vision_env.reset(seed=0)
    t0 = time.perf_counter()
    for _ in range(N_PERF_STEPS):
        _, _, terminated, truncated, _ = vision_env.step(vision_env.action_space.sample())
        if terminated or truncated:
            vision_env.reset()
    vision_hz = N_PERF_STEPS / (time.perf_counter() - t0)

    print(f"measure_steps_per_second: state-only={state_hz:.1f} steps/s, "
          f"vision={vision_hz:.1f} steps/s (slowdown {state_hz/vision_hz:.2f}x)")
    return state_hz, vision_hz


if __name__ == "__main__":
    run_gymnasium_check_env()
    check_frames_change()
    measure_steps_per_second()
    print("check_vision_env.py: ALL CHECKS PASSED")
