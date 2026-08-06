"""Thin helpers mapping config/env.yaml's active_arms onto concrete joint/body/geom names and
MuJoCo index arrays, resolved once at env construction so per-step code is plain array indexing
rather than repeated name lookups.
"""

from __future__ import annotations

import mujoco
import numpy as np

ARM_JOINT_SUFFIXES = ("shoulder_pitch_joint", "shoulder_roll_joint", "elbow_joint")


def arm_joint_names(side: str) -> list[str]:
    return [f"{side}_{suffix}" for suffix in ARM_JOINT_SUFFIXES]


def gripper_joint_name(side: str) -> str:
    return f"{side}_gripper_finger1_joint"


def ee_body_name(side: str) -> str:
    return f"{side}_gripper_base_link"


class JointIndex:
    """Resolved joint/actuator/body/geom indices for the active arms only."""

    def __init__(self, model: mujoco.MjModel, active_arms: list[str]):
        self.active_arms = list(active_arms)
        self.arm_joint_names = [n for side in active_arms for n in arm_joint_names(side)]
        self.gripper_joint_names = [gripper_joint_name(side) for side in active_arms]
        all_names = self.arm_joint_names + self.gripper_joint_names

        self.qposadr = np.array([model.joint(n).qposadr[0] for n in all_names])
        self.dofadr = np.array([model.joint(n).dofadr[0] for n in all_names])
        self.actuator_id = np.array([
            mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_ACTUATOR, f"{n}_position") for n in all_names
        ])
        self.jnt_range = np.array([model.joint(n).range for n in all_names])

        n_arm = len(self.arm_joint_names)
        self.arm_qposadr = self.qposadr[:n_arm]
        self.arm_dofadr = self.dofadr[:n_arm]
        self.arm_actuator_id = self.actuator_id[:n_arm]
        self.arm_jnt_range = self.jnt_range[:n_arm]

        self.gripper_qposadr = self.qposadr[n_arm:]
        self.gripper_actuator_id = self.actuator_id[n_arm:]
        self.gripper_jnt_range = self.jnt_range[n_arm:]

        self.ee_body_id = np.array([
            mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, ee_body_name(side)) for side in active_arms
        ])
        self.finger1_geom_id = np.array([
            mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, f"{side}_gripper_finger1_collision")
            for side in active_arms
        ])
        self.finger2_geom_id = np.array([
            mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, f"{side}_gripper_finger2_collision")
            for side in active_arms
        ])
