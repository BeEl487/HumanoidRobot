"""Velocity-limited reference-ramping for the arm/gripper position actuators, approximating the
real ODrive's trapezoidal-trajectory position control (ARCHITECTURE.md §3) -- an RL action sets a
*target*, not an instantaneous command. This ramps the actuator's ctrl input toward that target
at a bounded rate across the physics substeps within one control step, instead of snapping it,
which is what naive direct ctrl-assignment would do and is not how the real hardware behaves.

Acceleration limiting is not modeled (velocity-only ramp) -- a reasonable first-pass
approximation; revisit if later sim-to-real work shows the gap matters.
"""

from __future__ import annotations

import numpy as np


class TrajectoryShaper:
    def __init__(self, arm_max_vel: float, gripper_max_vel: float, n_arm_joints: int, n_gripper_joints: int):
        self.max_vel = np.concatenate([
            np.full(n_arm_joints, arm_max_vel),
            np.full(n_gripper_joints, gripper_max_vel),
        ])
        self.current_ref: np.ndarray | None = None

    def reset(self, current_pos: np.ndarray) -> None:
        self.current_ref = np.asarray(current_pos, dtype=np.float64).copy()

    def step(self, target: np.ndarray, dt: float) -> np.ndarray:
        """Advance the reference by one physics substep toward `target`; returns the new
        reference to write into data.ctrl. Call once per physics step, not once per control
        step -- the ramp needs to be resolved at physics rate to actually bound velocity."""
        if self.current_ref is None:
            raise RuntimeError("TrajectoryShaper.reset() must be called before step()")
        max_step = self.max_vel * dt
        delta = np.clip(target - self.current_ref, -max_step, max_step)
        self.current_ref = self.current_ref + delta
        return self.current_ref
