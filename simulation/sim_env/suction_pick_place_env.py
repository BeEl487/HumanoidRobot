"""Gymnasium environment for the suction pick-place task: pick a cube up from the source ("left")
box and place it at rest in the destination ("right") box, using a single arm whose gripper acts
as a suction cup rather than a finger grasp.

Independent task module from bin_picking_env.py (different scene, different action/observation
contract, different reward) -- kept separate per the "modular so additional objects and tasks can
easily be added later" requirement, rather than overloading one env class with two task modes.

Suction mechanics: the gripper's two finger joints are held at a fixed pose (not an RL action --
see config/pick_place_env.yaml's gripper_fixed_pos_frac) and act as a mounting platform for the
suction contact point (the gripper_base_link's own collision geom). Attachment is modeled as a
MuJoCo weld equality constraint between {side}_gripper_base_link and object_0, compiled inactive
by scripts/build_model.py:_add_suction_weld and toggled on/off per step via data.eq_active (a
plain mutable MjData array -- no recompilation needed, so this is stable/cheap enough to toggle
every control step during RL training). Physically: suction can only engage when the action
commands it AND the cup is actually touching the cube within a short range -- an action alone
can't attach through open air.
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
from build_model import load_model, pick_place_geometry_from_config  # noqa: E402

from .domain_randomization import randomize_cube_in_box, randomize_cube_physics
from .robot_model import arm_joint_names, ee_body_name, gripper_joint_name
from .pick_place_rewards import compute_step_reward
from .trajectory_shaper import TrajectoryShaper

SIM_ROOT = pathlib.Path(__file__).resolve().parent.parent
ENV_CONFIG_PATH = SIM_ROOT / "config" / "pick_place_env.yaml"
SCENE_CONFIG_PATH = SIM_ROOT / "config" / "pick_place_scene.yaml"

# Furniture geom name prefixes that count as "collision" if an arm link touches them (not the
# gripper/cube contacts, which are the intended interaction) -- see _is_arm_collision.
_FURNITURE_GEOM_PREFIXES = ("pp_table_", "box_source_", "box_dest_")


def _quat_mul(q1: np.ndarray, q2: np.ndarray) -> np.ndarray:
    w1, x1, y1, z1 = q1
    w2, x2, y2, z2 = q2
    return np.array([
        w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
        w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
        w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
        w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2,
    ])


def _quat_conj(q: np.ndarray) -> np.ndarray:
    return np.array([q[0], -q[1], -q[2], -q[3]])


class SuctionPickPlaceEnv(gym.Env):
    metadata = {"render_modes": []}

    def __init__(
        self, config_path: pathlib.Path = ENV_CONFIG_PATH, eval_mode: bool = False,
        enable_camera_occlusion_penalty: bool = False,
        close_approach_range_m_override: float | None = None,
    ):
        super().__init__()
        self.enable_camera_occlusion_penalty = enable_camera_occlusion_penalty
        with open(config_path, encoding="utf-8") as f:
            self.cfg = yaml.safe_load(f)
        with open(SCENE_CONFIG_PATH, encoding="utf-8") as f:
            self.scene_cfg = yaml.safe_load(f)
        if close_approach_range_m_override is not None:
            # rgbd_pp_v9-v13 repeatedly got stuck ~9.7cm from the cube -- outside the shared
            # config's close_approach_range_m (0.05m), so the steeper final-approach gradient
            # (added to fix this exact symptom on the state-based pick_place task) never
            # activated. Per-task override rather than changing the shared config value, since
            # pick_place is at a proven 70% success rate and hasn't shown this symptom -- no
            # reason to risk it for a fix the camera task specifically needs. See
            # camera_pick_place/HANDOFF.md for the diagnosis.
            self.cfg = dict(self.cfg)
            self.cfg["reward"] = dict(self.cfg["reward"])
            self.cfg["reward"]["close_approach_range_m"] = close_approach_range_m_override

        if eval_mode:
            # Forces every episode through the full task from scratch (no curriculum shortcut) --
            # for evaluation/video only, never for training. Without this, evaluate_checkpoint and
            # render_checkpoint_video (training/pick_place/train_ppo_pick_place.py) build a plain
            # SuctionPickPlaceEnv() that still has curriculum.enabled=true, so ~half of every
            # eval run's episodes (and the demo video, depending on its seed) started pre-attached
            # via the curriculum's mid-carry shortcut -- pick_success_rate/place_success_rate were
            # silently a mix of "genuinely solved it" and "started already past the hard part",
            # not a clean read of real end-to-end competence, since the curriculum was added.
            self.cfg = dict(self.cfg)
            self.cfg["curriculum"] = dict(self.cfg.get("curriculum", {}))
            self.cfg["curriculum"]["enabled"] = False
        self.eval_mode = eval_mode

        self.side = self.cfg["active_arm"]
        self.model, self.data = load_model(task="suction_pick_place")

        self.physics_hz = self.cfg["physics_hz"]
        self.control_hz = self.cfg["control_hz"]
        self.n_substeps = self.physics_hz // self.control_hz
        assert abs(self.model.opt.timestep - 1.0 / self.physics_hz) < 1e-9

        self._arm_joint_names = arm_joint_names(self.side)
        self._arm_qposadr = np.array([self.model.joint(n).qposadr[0] for n in self._arm_joint_names])
        self._arm_dofadr = np.array([self.model.joint(n).dofadr[0] for n in self._arm_joint_names])
        self._arm_actuator_id = np.array([
            mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_ACTUATOR, f"{n}_position")
            for n in self._arm_joint_names
        ])
        self._arm_jnt_range = np.array([self.model.joint(n).range for n in self._arm_joint_names])

        gripper_joint = gripper_joint_name(self.side)
        self._gripper_qposadr = self.model.joint(gripper_joint).qposadr[0]
        self._gripper_actuator_id = mujoco.mj_name2id(
            self.model, mujoco.mjtObj.mjOBJ_ACTUATOR, f"{gripper_joint}_position"
        )
        g_lo, g_hi = self.model.joint(gripper_joint).range
        self._gripper_fixed_pos = g_lo + self.cfg["gripper_fixed_pos_frac"] * (g_hi - g_lo)

        self.shaper = TrajectoryShaper(
            self.cfg["max_arm_joint_velocity_rad_s"], 0.0, len(self._arm_joint_names), 0
        )

        n_action = len(self._arm_joint_names) + 1  # 3 arm joints + 1 suction command
        self.action_space = spaces.Box(-1.0, 1.0, shape=(n_action,), dtype=np.float32)
        self.observation_space = spaces.Dict({
            "joint_pos": spaces.Box(-np.inf, np.inf, shape=(len(self._arm_joint_names),), dtype=np.float32),
            "joint_vel": spaces.Box(-np.inf, np.inf, shape=(len(self._arm_joint_names),), dtype=np.float32),
            "ee_pos": spaces.Box(-np.inf, np.inf, shape=(3,), dtype=np.float32),
            "cube_pos": spaces.Box(-np.inf, np.inf, shape=(3,), dtype=np.float32),
            "dest_pos": spaces.Box(-np.inf, np.inf, shape=(2,), dtype=np.float32),
            "is_attached": spaces.Box(0.0, 1.0, shape=(1,), dtype=np.float32),
            "suction_cmd": spaces.Box(0.0, 1.0, shape=(1,), dtype=np.float32),
        })

        self._ee_body_id = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_BODY, ee_body_name(self.side))
        self._suction_geom_id = mujoco.mj_name2id(
            self.model, mujoco.mjtObj.mjOBJ_GEOM, f"{self.side}_gripper_base_collision"
        )
        self._object_body_id = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_BODY, "object_0")
        self._object_geom_id = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_GEOM, "object_0_collision")
        self._object_dofadr = self.model.joint("object_0_freejoint").dofadr[0]
        self._eq_id = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_EQUALITY, f"{self.side}_suction_weld")
        # Camera is rigidly fixed to torso_link (no gimbal -- ASSUMPTIONS.md meta-assumption M1),
        # so its world position never changes once the model is built; resolved once here rather
        # than re-read every step. Only used when enable_camera_occlusion_penalty is set (the
        # RGB-D camera task), since the state-only pick_place task has no camera to occlude.
        if self.enable_camera_occlusion_penalty:
            cam_id = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_CAMERA, "head_camera")
            mujoco.mj_forward(self.model, self.data)
            self._camera_pos = self.data.cam_xpos[cam_id].copy()

        arm_link_geom_names = [f"{self.side}_upper_arm_collision", f"{self.side}_forearm_collision"]
        self._arm_link_geom_ids = {
            mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_GEOM, n) for n in arm_link_geom_names
        }
        self._furniture_geom_ids = {
            i for i in range(self.model.ngeom)
            if (mujoco.mj_id2name(self.model, mujoco.mjtObj.mjOBJ_GEOM, i) or "").startswith(_FURNITURE_GEOM_PREFIXES)
        }

        geom = pick_place_geometry_from_config(self.scene_cfg)
        self._src_x, self._src_y, self._floor_top_z = geom["source"]
        self._dst_x, self._dst_y, _ = geom["destination"]
        self._dest_center_xy = np.array([self._dst_x, self._dst_y])
        iw, idepth, ih = self.scene_cfg["boxes"]["inner_size"]
        self._box_half_w = iw / 2
        self._box_half_d = idepth / 2
        self._box_inner_h = ih
        self._table_top_z = self.scene_cfg["table"]["top_height"] + self.scene_cfg["table"]["top_thickness"]

        self._rng = np.random.default_rng()
        self._step_count = 0
        self._settle_count = 0
        self._is_attached = False
        self._has_attached_this_episode = False
        self._has_touched_this_episode = False
        self._has_lifted_this_episode = False
        self._has_placed_this_episode = False
        self._prev_carry_dist: float | None = None
        self._prev_height: float | None = None
        self._suction_cmd_on = False
        self._stall_counter = 0
        self._idle_counter = 0
        self._steps_since_attach = 0
        self._prev_action = np.zeros(n_action, dtype=np.float64)

    def set_start_attached_prob(self, prob: float) -> None:
        """Called via VecEnv.env_method by PeriodicArtifactCallback to anneal the curriculum's
        start_attached_prob over training (see config/pick_place_env.yaml's curriculum block) --
        a plain runtime dict update, no recompilation/reset needed, takes effect on the next
        reset()."""
        self.cfg.setdefault("curriculum", {})["start_attached_prob"] = prob

    def _camera_occlusion_penalty(self, ee_pos: np.ndarray, cube_pos: np.ndarray) -> float:
        """Penalizes the end effector for sitting in the camera's direct line of sight to the
        cube during approach -- the RGB-D policy otherwise has no incentive to prefer an angled
        approach over driving straight down the camera's centerline, which blinds its own vision
        right when it matters most. Geometrically: project ee_pos onto the camera->cube segment;
        if the projection falls strictly between the two (t in (0.05, 0.85) -- excluding both the
        camera's immediate vicinity and the final few cm of approach, where the hand is *supposed*
        to be near the cube) and the perpendicular distance from that segment is small, the hand is
        judged to be blocking the view. Gated by enable_camera_occlusion_penalty (camera task only,
        see ASSUMPTIONS.md) since the state-only pick_place task's camera is unused/irrelevant."""
        to_cube = cube_pos - self._camera_pos
        dist_to_cube = np.linalg.norm(to_cube)
        if dist_to_cube < 1e-6:
            return 0.0
        to_ee = ee_pos - self._camera_pos
        t = float(np.dot(to_ee, to_cube) / (dist_to_cube * dist_to_cube))
        if not (0.05 < t < 0.85):
            return 0.0
        perp_dist = np.linalg.norm(to_ee - t * to_cube)
        radius = self.cfg["reward"]["camera_occlusion_radius_m"]
        if perp_dist < radius:
            return self.cfg["reward"]["camera_occlusion_penalty"]
        return 0.0

    def _ready_pose(self) -> np.ndarray:
        pose = self.cfg["ready_pose_rad"]
        return np.array([pose["shoulder_yaw"], pose["shoulder_pitch"], pose["shoulder_roll"], pose["elbow"]])

    def _mid_carry_pose(self) -> np.ndarray:
        pose = self.cfg["curriculum"]["mid_carry_pose_rad"]
        return np.array([pose["shoulder_yaw"], pose["shoulder_pitch"], pose["shoulder_roll"], pose["elbow"]])

    def _near_dest_pose(self) -> np.ndarray:
        pose = self.cfg["curriculum"]["near_dest_pose_rad"]
        return np.array([pose["shoulder_yaw"], pose["shoulder_pitch"], pose["shoulder_roll"], pose["elbow"]])

    def _apply_ready_pose(self) -> None:
        self.data.qpos[self._arm_qposadr] = self._ready_pose()
        self.data.qpos[self._gripper_qposadr] = self._gripper_fixed_pos
        self.data.ctrl[self._gripper_actuator_id] = self._gripper_fixed_pos
        self.data.qvel[:] = 0.0

    def _deactivate_suction(self) -> None:
        self.data.eq_active[self._eq_id] = 0
        self._is_attached = False
        self._steps_since_attach = 0

    def reset(self, *, seed: int | None = None, options: dict | None = None):
        super().reset(seed=seed)
        if seed is not None:
            self._rng = np.random.default_rng(seed)
        mujoco.mj_resetData(self.model, self.data)
        self._apply_ready_pose()
        self._deactivate_suction()

        curriculum_cfg = self.cfg.get("curriculum", {})
        # pp_v15 -> pp_v16: three-way curriculum draw, cumulative -- start_carrying_prob (new,
        # highest priority slice) takes episodes closest to the goal first, then start_attached_prob
        # (existing) covers the rest of the assisted episodes, remainder run the full task from
        # scratch. Order matters only for how the probability mass is allocated, not semantics.
        curriculum_enabled = curriculum_cfg.get("enabled", False)
        u = self._rng.uniform() if curriculum_enabled else 1.0
        start_carrying_prob = curriculum_cfg.get("start_carrying_prob", 0.0)
        start_attached_prob = curriculum_cfg.get("start_attached_prob", 0.0)
        start_carrying = u < start_carrying_prob
        start_attached = (not start_carrying) and u < (start_carrying_prob + start_attached_prob)

        randomize_cube_physics(self.model, self._rng)
        self._has_attached_this_episode = False
        self._has_touched_this_episode = False
        self._has_lifted_this_episode = False
        if start_carrying:
            # New curriculum stage (see config/pick_place_env.yaml's curriculum block): skip
            # straight to "already attached, already above the destination, already past the lift
            # threshold" -- directly exposes the release-accuracy reward gradient in isolation,
            # the same way start_attached_prob exposes carry from the mid-carry point. Motivated by
            # place_success_rate being ~0% almost the entire project despite pp_9-15's approach/
            # attach-stage fixes -- carry never had its own curriculum shortcut before this.
            self.data.qpos[self._arm_qposadr] = self._near_dest_pose()
            self.data.ctrl[self._arm_actuator_id] = self._near_dest_pose()
            mujoco.mj_forward(self.model, self.data)
            self._teleport_cube_to(self._ee_pos())
            mujoco.mj_forward(self.model, self.data)
            self._attach_suction()
            self._has_attached_this_episode = True
            self._has_touched_this_episode = True
            self._has_lifted_this_episode = True
            self._steps_since_attach = 0
        elif start_attached:
            # Curriculum episode (see config/pick_place_env.yaml's curriculum block): skip the
            # approach+attach stage entirely by snapping the arm to a verified mid-carry pose
            # (NOT ready_pose_rad -- see mid_carry_pose_rad's comment for why) and welding the
            # cube on there, so every step of this episode exercises the carry+release reward
            # gradient pp_v2 apparently never got enough on-policy samples of.
            self.data.qpos[self._arm_qposadr] = self._mid_carry_pose()
            self.data.ctrl[self._arm_actuator_id] = self._mid_carry_pose()
            mujoco.mj_forward(self.model, self.data)
            self._teleport_cube_to(self._ee_pos())
            mujoco.mj_forward(self.model, self.data)
            self._attach_suction()
            self._has_attached_this_episode = True
            self._has_touched_this_episode = True
            self._steps_since_attach = 0
        else:
            randomize_cube_in_box(
                self.model, self.data, self._rng, (self._src_x, self._src_y), self._floor_top_z
            )
            mujoco.mj_forward(self.model, self.data)

        self.shaper.reset(self.data.ctrl[self._arm_actuator_id])
        self._step_count = 0
        self._settle_count = 0
        self._has_placed_this_episode = False
        self._prev_carry_dist = None
        self._prev_height = None
        self._suction_cmd_on = False
        self._stall_counter = 0
        self._idle_counter = 0
        self._prev_action = np.zeros(self.action_space.shape[0], dtype=np.float64)
        return self._get_obs(), {}

    def _teleport_cube_to(self, pos: np.ndarray) -> None:
        qposadr = self.model.joint("object_0_freejoint").qposadr[0]
        dofadr = self.model.joint("object_0_freejoint").dofadr[0]
        self.data.qpos[qposadr:qposadr + 3] = pos
        self.data.qpos[qposadr + 3:qposadr + 7] = [1, 0, 0, 0]
        self.data.qvel[dofadr:dofadr + 6] = 0.0

    def _normalized_to_arm_target(self, action_arm: np.ndarray) -> np.ndarray:
        lo, hi = self._arm_jnt_range[:, 0], self._arm_jnt_range[:, 1]
        action_arm = np.clip(action_arm, -1.0, 1.0)
        return lo + (action_arm + 1.0) * 0.5 * (hi - lo)

    def _ee_pos(self) -> np.ndarray:
        return self.data.xpos[self._ee_body_id].copy()

    def _is_suction_touching(self) -> bool:
        for i in range(self.data.ncon):
            c = self.data.contact[i]
            geoms = {c.geom1, c.geom2}
            if self._suction_geom_id in geoms and self._object_geom_id in geoms:
                return True
        return False

    def _is_arm_collision(self) -> bool:
        for i in range(self.data.ncon):
            c = self.data.contact[i]
            g1, g2 = c.geom1, c.geom2
            if (g1 in self._arm_link_geom_ids and g2 in self._furniture_geom_ids) or (
                g2 in self._arm_link_geom_ids and g1 in self._furniture_geom_ids
            ):
                return True
        return False

    def _update_stall_counter(self, is_arm_collision: bool) -> bool:
        """Tracks consecutive steps where the arm is in contact with furniture AND barely moving
        -- jammed against a wall, not just brushing past it while still in motion. Same shape as
        the bin-picking task's reward.stuck mechanism (config/env.yaml, BinPickingEnv.step):
        collision alone isn't penalized here beyond collision_penalty; sustained collision+no
        motion is what stall_penalty targets."""
        mean_arm_speed = float(np.mean(np.abs(self.data.qvel[self._arm_dofadr])))
        if is_arm_collision and mean_arm_speed < self.cfg["reward"]["stall_velocity_threshold_rad_s"]:
            self._stall_counter += 1
        else:
            self._stall_counter = 0
        return self._stall_counter >= self.cfg["reward"]["stall_steps_threshold"]

    def _update_idle_counter(self) -> bool:
        """pp_v13 -> pp_v14 (user request): tracks consecutive steps of near-zero arm motion
        REGARDLESS of collision -- unlike `_update_stall_counter` (which only fires when jammed
        against furniture), this catches the freeze/hover/park behaviors seen across pp_v8
        (frozen post-attach), pp_v11 (frozen just outside attach range), and pp_v12 (parked inside
        the box, and separately circling in a tight band without committing to a full approach) --
        none of which involve a collision, so `is_stalled` never fired for any of them. Only
        meaningful pre-attach: once attached, `attached_idle_penalty`/`_after_lift` already penalize
        lack of carry progress, and briefly holding still while genuinely aligning for a lift/release
        is more defensible than pre-attach stillness, which has no legitimate reason to persist."""
        mean_arm_speed = float(np.mean(np.abs(self.data.qvel[self._arm_dofadr])))
        if mean_arm_speed < self.cfg["reward"]["idle_velocity_threshold_rad_s"]:
            self._idle_counter += 1
        else:
            self._idle_counter = 0
        return self._idle_counter >= self.cfg["reward"]["idle_steps_threshold"]

    def _is_cube_in_dest_box(self, cube_pos: np.ndarray) -> bool:
        dx = abs(cube_pos[0] - self._dst_x)
        dy = abs(cube_pos[1] - self._dst_y)
        dz = cube_pos[2] - self._floor_top_z
        return dx <= self._box_half_w and dy <= self._box_half_d and -0.01 <= dz <= self._box_inner_h

    def _attach_suction(self) -> None:
        """Overwrite model.eq_data[self._eq_id] with the CURRENT relative pose between the
        gripper and the cube, then activate the constraint -- so the cube welds on exactly where
        it actually is (see build_model.py:_add_suction_weld's data-layout note), not a pose
        baked in at compile time."""
        xpos1 = self.data.xpos[self._ee_body_id]
        xquat1 = self.data.xquat[self._ee_body_id]
        xmat1 = self.data.xmat[self._ee_body_id].reshape(3, 3)
        xpos2 = self.data.xpos[self._object_body_id]
        xquat2 = self.data.xquat[self._object_body_id]

        rel_pos = xmat1.T @ (xpos2 - xpos1)
        rel_quat = _quat_mul(_quat_conj(xquat1), xquat2)

        self.model.eq_data[self._eq_id, 0:3] = rel_pos      # anchor, in body1 (gripper) frame
        self.model.eq_data[self._eq_id, 3:6] = rel_pos      # relpose position (same point)
        self.model.eq_data[self._eq_id, 6:10] = rel_quat    # relpose orientation
        self.model.eq_data[self._eq_id, 10] = 1.0           # torquescale (full rigid weld)
        self.data.eq_active[self._eq_id] = 1
        self._is_attached = True

    def step(self, action: np.ndarray):
        action = np.asarray(action, dtype=np.float64)
        n_arm = len(self._arm_joint_names)
        arm_target = self._normalized_to_arm_target(action[:n_arm])
        suction_cmd_on = bool(action[n_arm] > self.cfg["suction"]["activation_threshold"])

        dt = self.model.opt.timestep
        for _ in range(self.n_substeps):
            ref = self.shaper.step(arm_target, dt)
            self.data.ctrl[self._arm_actuator_id] = ref
            mujoco.mj_step(self.model, self.data)

        self._step_count += 1

        cube_pos = self.data.xpos[self._object_body_id].copy()
        cube_vel = self.data.qvel[self._object_dofadr:self._object_dofadr + 3].copy()
        ee_pos = self._ee_pos()

        was_attached = self._is_attached
        just_attached = False
        just_released_early = False

        if not was_attached:
            suction_cmd_on = float(action[n_arm]) > self.cfg["suction"]["activation_threshold"]
        else:
            suction_cmd_on = float(action[n_arm]) > self.cfg["suction"]["deactivation_threshold"]
        self._suction_cmd_on = suction_cmd_on

        # pp_v9 -> pp_v10: two-part chatter fix. User observed (and pick_place_rewards.py's reward
        # log confirmed) rapid attach/detach cycling with reward spiking each cycle -- root cause
        # was attach_bonus paying out on EVERY attach, not just the episode's first (unlike
        # lift_bonus, which already had this gate via _has_lifted_this_episode). A chatter cycle
        # (attach +12, release outside dest -3, reattach +12, ...) nets +9/cycle, farmable
        # indefinitely -- same shape of exploit as pp_v3/v4's continuous lift_bonus_weight bug.
        # Fix 1 (reward): only pay attach_bonus on the true first attach of the episode --
        # `first_attach_this_episode` below, checked against the OLD value of
        # `_has_attached_this_episode` before it's updated. Re-attaching later in the same episode
        # still works physically (just_attached still fires for info/curriculum bookkeeping) but no
        # longer pays the milestone bonus again.
        # Fix 2 (physics): a `min_attached_steps_before_detach` debounce (config, default 5 steps =
        # 0.25s @ 20Hz) -- once attached, a detach command is ignored until this many steps have
        # passed, so single-step action noise crossing the hysteresis band can't toggle the weld at
        # all, independent of whether the reward incentive is fixed.
        if not was_attached and suction_cmd_on:
            dist = float(np.linalg.norm(ee_pos - cube_pos))
            if self._is_suction_touching() and dist <= self.cfg["suction"]["max_attach_distance_m"]:
                first_attach_this_episode = not self._has_attached_this_episode
                self._attach_suction()
                just_attached = first_attach_this_episode
                self._has_attached_this_episode = True
                self._steps_since_attach = 0
        elif was_attached and not suction_cmd_on:
            min_hold = self.cfg["suction"].get("min_attached_steps_before_detach", 0)
            if self._steps_since_attach >= min_hold:
                released_over_dest = self._is_cube_in_dest_box(cube_pos)
                self._deactivate_suction()
                if not released_over_dest:
                    just_released_early = True
            else:
                self._steps_since_attach += 1
        elif was_attached:
            self._steps_since_attach += 1

        is_arm_collision = self._is_arm_collision()
        is_stalled = self._update_stall_counter(is_arm_collision)
        # pp_v13 -> pp_v14: pure stillness, independent of collision -- see _update_idle_counter's
        # docstring. Only meaningful pre-attach (post-attach stillness is already covered by
        # attached_idle_penalty/_after_lift, which key off carry PROGRESS rather than raw motion).
        # Counter is reset (not just ignored) while attached so a stale count can't immediately
        # re-trigger the instant suction releases.
        if self._is_attached:
            self._idle_counter = 0
            is_idle = False
        else:
            is_idle = self._update_idle_counter()
        height_above_table = float(cube_pos[2] - self._table_top_z)
        carry_dist = float(np.linalg.norm(cube_pos[:2] - self._dest_center_xy))
        ee_to_cube_dist = float(np.linalg.norm(ee_pos - cube_pos))

        # "Bulldozing": the suction cup is touching the cube but hasn't attached, and the cube is
        # moving fast -- being knocked/pushed around rather than gently approached. Without this,
        # nothing in the reward distinguished a careful approach from ramming the cube (which can
        # still look like "progress" to distance_weight since it may reduce ee_to_cube_dist
        # briefly even as it shoves the cube away, and the policy has no reason to stop chasing a
        # cube it keeps pushing out of reach). Only applies pre-attach -- once attached, cube
        # velocity legitimately follows the arm's own carry motion and shouldn't be penalized.
        cube_speed = float(np.linalg.norm(cube_vel))
        is_touching_not_attached = (not self._is_attached) and self._is_suction_touching()
        disturb_threshold = self.cfg["reward"]["disturbance_velocity_threshold_m_s"]
        cube_disturbance = max(cube_speed - disturb_threshold, 0.0) if is_touching_not_attached else 0.0

        # One-time touch milestone (2026-08-20): before this, contact alone was pure downside --
        # distance/close_approach only ever *shrink* the per-step penalty as the gap closes (never
        # a positive reward for contact itself), and touching-without-attaching risks
        # cube_disturbance_weight the instant the cube's speed ticks up, with zero offsetting
        # reward if suction/distance don't also line up in that same step to trigger attach_bonus.
        # That asymmetry rewards hovering just short of contact over committing to it -- diagnosed
        # from the RGB-D task hovering ~9-10cm from the cube. Gated the same one-time-per-episode
        # way as attach_bonus/lift_bonus (no farmable repeat reward, matches this file's module
        # docstring principle) -- curriculum episodes that start already attached mark this True at
        # reset so it can't re-pay here.
        just_touched = self._is_suction_touching() and not self._has_touched_this_episode
        if just_touched:
            self._has_touched_this_episode = True

        just_lifted = False
        if self._is_attached and not self._has_lifted_this_episode and height_above_table > self.cfg["reward"]["lift_threshold_m"]:
            just_lifted = True
            self._has_lifted_this_episode = True

        just_placed = False
        if not self._is_attached and self._is_cube_in_dest_box(cube_pos) and float(np.linalg.norm(cube_vel)) < self.cfg["success"]["max_speed_m_s"]:
            self._settle_count += 1
        else:
            self._settle_count = 0
        if self._settle_count >= self.cfg["success"]["hold_steps"] and not self._has_placed_this_episode:
            just_placed = True
            self._has_placed_this_episode = True

        reward = compute_step_reward(
            ee_pos, cube_pos, self._dest_center_xy, height_above_table,
            self._is_attached, just_attached, just_lifted, just_placed, just_released_early, is_arm_collision,
            is_stalled, is_idle, cube_disturbance, self._prev_carry_dist, self._prev_height,
            self._has_lifted_this_episode, action, self._prev_action, self.cfg,
        )
        if just_touched:
            reward += self.cfg["reward"]["touch_bonus"]
        self._prev_action = action
        self._prev_carry_dist = carry_dist
        self._prev_height = height_above_table

        if self.enable_camera_occlusion_penalty and not self._is_attached:
            reward += self._camera_occlusion_penalty(ee_pos, cube_pos)

        terminated = False
        truncated = False
        info: dict = {
            "attached": self._has_attached_this_episode,
            "touched": self._has_touched_this_episode,
            "is_attached": self._is_attached,
            "is_arm_collision": is_arm_collision,
            "is_stalled": is_stalled,
            "is_idle": is_idle,
            "ee_to_cube_dist": ee_to_cube_dist,
            "carry_dist": carry_dist,
            "cube_height": height_above_table,
            "cube_disturbance": cube_disturbance,
            # Plain float tuples (not np.ndarray) -- these cross a SubprocVecEnv pickling boundary
            # during training (training/pick_place/self_monitor.py reads them from
            # self.locals["infos"] for the continuous CSV logger), where plain Python types are
            # the safe/simple choice.
            "ee_pos": (float(ee_pos[0]), float(ee_pos[1]), float(ee_pos[2])),
            "cube_pos": (float(cube_pos[0]), float(cube_pos[1]), float(cube_pos[2])),
        }

        if just_placed:
            terminated = True
            info["success"] = True

        if cube_pos[2] < self._table_top_z - self.cfg["failure"]["table_edge_margin_m"]:
            terminated = True
            reward += self.cfg["reward"]["knockout_penalty"]
            info["success"] = False

        stage = 0
        if self._is_attached:
            if height_above_table > self.cfg["reward"]["lift_threshold_m"]:
                stage = 2
            else:
                stage = 1
        if just_placed:
            stage = 3

        info["suction_cmd"] = float(self._suction_cmd_on)
        info["stage"] = stage

        if self._step_count >= self.cfg["episode_max_steps"]:
            truncated = True

        return self._get_obs(), reward, terminated, truncated, info

    def _get_obs(self) -> dict:
        return {
            "joint_pos": self.data.qpos[self._arm_qposadr].astype(np.float32),
            "joint_vel": self.data.qvel[self._arm_dofadr].astype(np.float32),
            "ee_pos": self._ee_pos().astype(np.float32),
            "cube_pos": self.data.xpos[self._object_body_id].astype(np.float32),
            "dest_pos": self._dest_center_xy.astype(np.float32),
            "is_attached": np.array([1.0 if self._is_attached else 0.0], dtype=np.float32),
            "suction_cmd": np.array([1.0 if self._suction_cmd_on else 0.0], dtype=np.float32),
        }
