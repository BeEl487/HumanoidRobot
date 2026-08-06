"""Gymnasium environment for single-object bin-picking: reach, grasp, and lift `object_0` above
the bin floor. State-based observations only (ground-truth pose from the simulator) -- vision is
layered on top in Milestone 7 by sim_env/vision_wrapper.py, which wraps this env rather than
duplicating it, so the fast state-only baseline stays usable on its own.

Scope: exactly one designated object (object_0) is always the grasp target, regardless of how
many objects are in the bin -- true multi-object target selection (choosing *which* object to
grasp among several) is a materially harder RL problem (variable-cardinality observations, target
ambiguity) genuinely out of scope for this milestone. config/env.yaml's active_arms controls 6.1
(single arm) vs. 6.2 (both arms) generalization.
"""

from __future__ import annotations

import pathlib
import sys

import mujoco
import numpy as np
import yaml
import gymnasium as gym
from gymnasium import spaces

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))
from build_model import load_model  # noqa: E402

from .domain_randomization import bin_geometry_from_config, randomize_object_friction, randomize_objects
from .robot_model import JointIndex
from .rewards import compute_step_reward
from .trajectory_shaper import TrajectoryShaper

SIM_ROOT = pathlib.Path(__file__).resolve().parent.parent
ENV_CONFIG_PATH = SIM_ROOT / "config" / "env.yaml"
SCENE_CONFIG_PATH = SIM_ROOT / "config" / "scene.yaml"


class BinPickingEnv(gym.Env):
    metadata = {"render_modes": []}

    def __init__(self, config_path: pathlib.Path = ENV_CONFIG_PATH):
        super().__init__()
        with open(config_path, encoding="utf-8") as f:
            self.cfg = yaml.safe_load(f)
        with open(SCENE_CONFIG_PATH, encoding="utf-8") as f:
            self.scene_cfg = yaml.safe_load(f)

        self.model, self.data = load_model()
        self.joints = JointIndex(self.model, self.cfg["active_arms"])
        self.n_arms = len(self.cfg["active_arms"])

        self.physics_hz = self.cfg["physics_hz"]
        self.control_hz = self.cfg["control_hz"]
        self.n_substeps = self.physics_hz // self.control_hz
        assert abs(self.model.opt.timestep - 1.0 / self.physics_hz) < 1e-9, (
            "config/env.yaml's physics_hz must match models/mjcf/scene.xml's <option timestep>"
        )

        self.shaper = TrajectoryShaper(
            self.cfg["max_arm_joint_velocity_rad_s"],
            self.cfg["max_gripper_velocity_m_s"],
            len(self.joints.arm_joint_names),
            len(self.joints.gripper_joint_names),
        )

        n_action = len(self.joints.arm_joint_names) + len(self.joints.gripper_joint_names)
        self.action_space = spaces.Box(-1.0, 1.0, shape=(n_action,), dtype=np.float32)
        self.observation_space = spaces.Dict({
            "joint_pos": spaces.Box(-np.inf, np.inf, shape=(len(self.joints.arm_joint_names),), dtype=np.float32),
            "joint_vel": spaces.Box(-np.inf, np.inf, shape=(len(self.joints.arm_joint_names),), dtype=np.float32),
            "gripper_pos": spaces.Box(-np.inf, np.inf, shape=(self.n_arms,), dtype=np.float32),
            "ee_pos": spaces.Box(-np.inf, np.inf, shape=(3 * self.n_arms,), dtype=np.float32),
            "object_pos": spaces.Box(-np.inf, np.inf, shape=(3,), dtype=np.float32),
            "object_present": spaces.Box(0.0, 1.0, shape=(1,), dtype=np.float32),
        })

        self._object_body_id = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_BODY, "object_0")
        self._object_geom_id = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_GEOM, "object_0_collision")
        self._bin_cx, self._bin_cy, self._bin_floor_z = bin_geometry_from_config(self.scene_cfg)
        iw, idepth, _ = self.scene_cfg["bin"]["inner_size"]
        self._bin_half_w = iw / 2
        self._bin_half_d = idepth / 2

        self._rng = np.random.default_rng()
        self._step_count = 0
        self._grasp_hold_count = 0
        self._has_touched_this_episode = False
        self._has_grasped_this_episode = False
        self._prev_ee_pos = None
        self._stuck_counter = 0

    def _ready_pose(self) -> np.ndarray:
        pose = self.cfg["ready_pose_rad"]
        one_arm = np.array([pose["shoulder_pitch"], pose["shoulder_roll"], pose["elbow"]])
        return np.tile(one_arm, self.n_arms)

    def _apply_ready_pose(self) -> None:
        self.data.qpos[self.joints.arm_qposadr] = self._ready_pose()
        self.data.qpos[self.joints.gripper_qposadr] = self.joints.gripper_jnt_range[:, 1]  # start open
        self.data.qvel[:] = 0.0

    def reset(self, *, seed: int | None = None, options: dict | None = None):
        super().reset(seed=seed)
        if seed is not None:
            self._rng = np.random.default_rng(seed)
        mujoco.mj_resetData(self.model, self.data)
        self._apply_ready_pose()
        # active_slots=[0]: object_0 is this env's fixed grasp target (see class docstring) --
        # without pinning it, randomize_objects' random slot permutation would park it out of
        # the workspace whenever it wasn't the slot chosen active.
        curriculum = self.cfg.get("curriculum", {})
        if curriculum.get("enabled", False):
            self._curriculum_spawn(curriculum)
        else:
            randomize_objects(self.model, self.data, self._rng, count=1, active_slots=[0])
        randomize_object_friction(self.model, self._rng)
        mujoco.mj_forward(self.model, self.data)

        self.shaper.reset(self.data.ctrl[self.joints.actuator_id])
        self._step_count = 0
        self._grasp_hold_count = 0
        self._has_touched_this_episode = False
        self._has_grasped_this_episode = False
        self._prev_ee_pos = self._ee_pos()
        self._stuck_counter = 0
        return self._get_obs(), {}

    def _curriculum_spawn(self, curriculum_cfg: dict) -> None:
        """Places object_0 in a small region close to one arm's ready-pose reach, instead of the
        full bin footprint -- makes initial contact discoverable early in training rather than
        also requiring the policy to solve full-bin reach before ever finding contact (v5 change,
        see docs/ASSUMPTIONS.md "v5" note -- v1-v4 all learned to reduce distance efficiently but
        never discovered contact, suggesting the exploration problem, not network capacity, was
        the bottleneck). Still routes through randomize_objects first (count=1) so the other 3
        object slots get parked out of the workspace exactly as in the non-curriculum path; only
        object_0's spawn position is overridden afterward."""
        randomize_objects(self.model, self.data, self._rng, count=1, active_slots=[0])
        side = "left" if self._rng.uniform() < 0.5 else "right"
        target = curriculum_cfg["targets"][side]
        radius = curriculum_cfg["spawn_radius_m"]
        offset = self._rng.uniform(-radius, radius, size=2)
        qposadr = self.model.joint("object_0_freejoint").qposadr[0]
        self.data.qpos[qposadr] = target[0] + offset[0]
        self.data.qpos[qposadr + 1] = target[1] + offset[1]
        self.data.qpos[qposadr + 2] = target[2]

    def _normalized_to_target(self, action: np.ndarray) -> np.ndarray:
        lo, hi = self.joints.jnt_range[:, 0], self.joints.jnt_range[:, 1]
        action = np.clip(action, -1.0, 1.0)
        return lo + (action + 1.0) * 0.5 * (hi - lo)

    def _ee_pos(self) -> np.ndarray:
        """Per-arm (n_arms, 3) end-effector reference point for both the distance-shaping reward
        and the "ee_pos" observation: the midpoint between the two fingertip collision geoms.

        v6 finding (see docs/ASSUMPTIONS.md "v6"): this used to be gripper_base_link's own xpos --
        the wrist/mount frame the gripper attaches to, per robot_model.ee_body_name. Per
        humanoid.urdf's finger geometry, each finger's collision box is centered ~2.5cm from that
        mount along the gripper (and extends to ~5cm at its very tip), so gripper_base_link was
        silently invisible to how close the gripper *actually* was to the object -- both what the
        policy got rewarded for and what it could see in its own observations understated true
        proximity by 1-2cm on average, every step, every episode, in every run through v6."""
        f1 = self.data.geom_xpos[self.joints.finger1_geom_id]
        f2 = self.data.geom_xpos[self.joints.finger2_geom_id]
        return (f1 + f2) / 2.0

    def _contact_state(self) -> tuple[np.ndarray, np.ndarray]:
        """Per-arm (touched_f1[i], touched_f2[i]) -- must be the SAME arm's own two fingers to
        count as that arm's grasp. (Bug fix: the original version OR'd contact across all active
        arms' fingers independently, so with both arms active it could report "grasped" from the
        left arm's finger1 touching plus the right arm's finger2 touching -- two different arms,
        not an actual enclosing grasp by either one.)"""
        n = self.n_arms
        touched_f1 = np.zeros(n, dtype=bool)
        touched_f2 = np.zeros(n, dtype=bool)
        for i in range(self.data.ncon):
            c = self.data.contact[i]
            geoms = {c.geom1, c.geom2}
            if self._object_geom_id not in geoms:
                continue
            for arm_idx in range(n):
                if int(self.joints.finger1_geom_id[arm_idx]) in geoms:
                    touched_f1[arm_idx] = True
                if int(self.joints.finger2_geom_id[arm_idx]) in geoms:
                    touched_f2[arm_idx] = True
        return touched_f1, touched_f2

    def step(self, action: np.ndarray):
        target = self._normalized_to_target(np.asarray(action, dtype=np.float64))
        dt = self.model.opt.timestep
        for _ in range(self.n_substeps):
            ref = self.shaper.step(target, dt)
            self.data.ctrl[self.joints.actuator_id] = ref
            mujoco.mj_step(self.model, self.data)

        self._step_count += 1

        object_pos = self.data.xpos[self._object_body_id].copy()
        height_above_floor = float(object_pos[2] - self._bin_floor_z)
        touched_f1, touched_f2 = self._contact_state()
        is_grasped = bool(np.any(touched_f1 & touched_f2))

        # Both milestone flags fire at most once per episode (per-episode flags, not just
        # "changed since last step") -- this is what makes them non-farmable: tapping contact
        # on and off repeatedly, or grasping/dropping/re-grasping, cannot re-collect either bonus.
        # See sim_env/rewards.py's module docstring for why this replaced the earlier continuous
        # per-step bonuses (a real reward-hacking exploit was found in the v2 continuous design).
        is_touching = bool(np.any(touched_f1) or np.any(touched_f2))
        just_touched = is_touching and not self._has_touched_this_episode
        if just_touched:
            self._has_touched_this_episode = True
        just_grasped = is_grasped and not self._has_grasped_this_episode
        if just_grasped:
            self._has_grasped_this_episode = True

        ee_pos = self._ee_pos()
        stuck_cfg = self.cfg["reward"]["stuck"]
        if stuck_cfg["enabled"]:
            dists_to_object = np.linalg.norm(ee_pos - object_pos[None, :], axis=1)
            closest_idx = int(np.argmin(dists_to_object))
            movement = float(np.linalg.norm(ee_pos[closest_idx] - self._prev_ee_pos[closest_idx]))
            if movement < stuck_cfg["movement_threshold_m"]:
                self._stuck_counter += 1
            else:
                self._stuck_counter = 0
            is_stuck = self._stuck_counter >= stuck_cfg["steps_threshold"]
        else:
            is_stuck = False
        self._prev_ee_pos = ee_pos

        reward = compute_step_reward(
            ee_pos, object_pos, height_above_floor, is_grasped, just_touched, just_grasped, is_stuck, self.cfg,
        )

        terminated = False
        truncated = False
        info: dict = {}

        if is_grasped and height_above_floor > self.cfg["success"]["lift_height_m"]:
            self._grasp_hold_count += 1
        else:
            self._grasp_hold_count = 0
        if self._grasp_hold_count >= self.cfg["success"]["hold_steps"]:
            terminated = True
            info["success"] = True

        dx = abs(object_pos[0] - self._bin_cx) - self._bin_half_w
        dy = abs(object_pos[1] - self._bin_cy) - self._bin_half_d
        margin = self.cfg["failure"]["out_of_bin_margin_m"]
        if dx > margin or dy > margin:
            terminated = True
            reward += self.cfg["reward"]["knockout_penalty"]
            info["success"] = False

        if self._step_count >= self.cfg["episode_max_steps"]:
            truncated = True

        return self._get_obs(), reward, terminated, truncated, info

    def _get_obs(self) -> dict:
        return {
            "joint_pos": self.data.qpos[self.joints.arm_qposadr].astype(np.float32),
            "joint_vel": self.data.qvel[self.joints.arm_dofadr].astype(np.float32),
            "gripper_pos": self.data.qpos[self.joints.gripper_qposadr].astype(np.float32),
            "ee_pos": self._ee_pos().flatten().astype(np.float32),
            "object_pos": self.data.xpos[self._object_body_id].astype(np.float32),
            "object_present": np.array([1.0], dtype=np.float32),
        }
