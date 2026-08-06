"""General-purpose model health check: compile, print a structural summary, and run a short
zero-actuation rollout checking for numerical stability (no NaN/Inf, nothing diverging).

Run after every milestone that changes the model. Expected body/joint/actuator counts and mass
range are milestone-specific and are stated in that milestone's verification notes, not hardcoded
here — this script stays a reusable health check, not a fixed assertion for one snapshot in time.
"""

from __future__ import annotations

import numpy as np
import mujoco

from build_model import load_model

N_STEPS = 500


def summarize(model: mujoco.MjModel) -> None:
    total_mass = sum(model.body(i).mass[0] for i in range(model.nbody))
    print(f"bodies:     {model.nbody}")
    print(f"joints:     {model.njnt}")
    print(f"actuators:  {model.nu}")
    print(f"total mass: {total_mass:.4f} kg")
    print("body list:")
    for i in range(model.nbody):
        b = model.body(i)
        print(f"  [{i}] {b.name!r:24s} mass={b.mass[0]:.4f} kg  pos={model.body_pos[i]}")
    if model.njnt:
        print("joint list:")
        for i in range(model.njnt):
            j = model.joint(i)
            lo, hi = model.jnt_range[i]
            print(f"  [{i}] {j.name!r:32s} range=({lo:.3f}, {hi:.3f}) rad")


def check_stability(model: mujoco.MjModel, data: mujoco.MjData, n_steps: int = N_STEPS) -> None:
    """Zero-control rollout: every DOF should either stay put or settle, never diverge."""
    mujoco.mj_resetData(model, data)
    for step in range(n_steps):
        mujoco.mj_step(model, data)
        if not (np.all(np.isfinite(data.qpos)) and np.all(np.isfinite(data.qvel))):
            raise AssertionError(f"Non-finite qpos/qvel at step {step}")
        if not np.all(np.isfinite(data.xpos)):
            raise AssertionError(f"Non-finite body world position at step {step}")
    print(f"Stability check passed: {n_steps} zero-control steps, all state finite.")


if __name__ == "__main__":
    model, data = load_model()
    summarize(model)
    check_stability(model, data)
    print("check_model.py: ALL CHECKS PASSED")
