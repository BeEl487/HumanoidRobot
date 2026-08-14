"""Compose the full MuJoCo model from the robot URDF + the MJCF scene shell.

This is the single model-composition entrypoint every other script, the Gymnasium env, and the
RL trainer call — no other file should build a model a second, divergent way.

Layering: models/urdf/humanoid.urdf is the single source of truth for robot geometry, joint
layout, and joint limits (kept reusable by the real robot's future ikpy-based kinematics code).
Everything MuJoCo-only that URDF can't express — geom density (so mass/inertia stay derived from
geometry rather than hand-computed), actuators, contact params, cameras, the gripper's finger-
mimic constraint, and attaching the robot into a scene — is added here or in the MJCF scene file.
See simulation/docs/ASSUMPTIONS.md for the rationale behind every numeric value referenced below.
"""

from __future__ import annotations

import math
import pathlib

import mujoco
import numpy as np
import yaml

SIM_ROOT = pathlib.Path(__file__).resolve().parent.parent
URDF_PATH = SIM_ROOT / "models" / "urdf" / "humanoid.urdf"
SCENE_PATH = SIM_ROOT / "models" / "mjcf" / "scene.xml"
GENERATED_DIR = SIM_ROOT / "models" / "mjcf" / "_generated"
GENERATED_SCENE_PATH = GENERATED_DIR / "full_scene_compiled.xml"
GENERATED_PICK_PLACE_SCENE_PATH = GENERATED_DIR / "pick_place_scene_compiled.xml"
JOINT_NAMES_PATH = SIM_ROOT / "config" / "joint_names.yaml"
CAMERA_CONFIG_PATH = SIM_ROOT / "config" / "camera.yaml"
SCENE_CONFIG_PATH = SIM_ROOT / "config" / "scene.yaml"
PICK_PLACE_SCENE_CONFIG_PATH = SIM_ROOT / "config" / "pick_place_scene.yaml"

_SHAPE_TO_GEOMTYPE = {
    "cube": mujoco.mjtGeom.mjGEOM_BOX,
    "cylinder": mujoco.mjtGeom.mjGEOM_CYLINDER,
    "sphere": mujoco.mjtGeom.mjGEOM_SPHERE,
}

# Density (kg/m^3) per named <collision> geom in humanoid.urdf. MuJoCo derives mass/inertia from
# geometry x density at compile time, so no inertia tensor is ever hand-computed. Rationale for
# each value: simulation/docs/ASSUMPTIONS.md.
_ARM_LINK_DENSITY = 1200.0  # PETG-printed tube, per ASSUMPTIONS.md "Arms" table
_ACTUATOR_LUMP_DENSITY = 9600.0  # 0.025^3 m box -> ~0.15 kg, standing in for ODrive Mini + motor
_GRIPPER_BASE_DENSITY = 5000.0  # 0.03x0.04x0.02 m box -> ~0.12 kg, standing in for an unchosen small actuator
_GRIPPER_FINGER_DENSITY = 1200.0  # PETG, same material assumption as the arm tubes

GEOM_DENSITIES: dict[str, float] = {
    "torso_collision": 550.0,  # lumped frame+battery+electronics density, backed out from a target mass guess
}
for _side in ("left", "right"):
    GEOM_DENSITIES[f"{_side}_shoulder_yaw_actuator_collision"] = _ACTUATOR_LUMP_DENSITY
    GEOM_DENSITIES[f"{_side}_shoulder_actuator_collision"] = _ACTUATOR_LUMP_DENSITY
    GEOM_DENSITIES[f"{_side}_shoulder_roll_actuator_collision"] = _ACTUATOR_LUMP_DENSITY
    GEOM_DENSITIES[f"{_side}_upper_arm_collision"] = _ARM_LINK_DENSITY
    GEOM_DENSITIES[f"{_side}_elbow_actuator_collision"] = _ACTUATOR_LUMP_DENSITY
    GEOM_DENSITIES[f"{_side}_forearm_collision"] = _ARM_LINK_DENSITY
    GEOM_DENSITIES[f"{_side}_gripper_base_collision"] = _GRIPPER_BASE_DENSITY
    GEOM_DENSITIES[f"{_side}_gripper_finger1_collision"] = _GRIPPER_FINGER_DENSITY
    GEOM_DENSITIES[f"{_side}_gripper_finger2_collision"] = _GRIPPER_FINGER_DENSITY

# Fingertip friction (sliding, torsional, rolling) — higher sliding friction than MuJoCo's default
# (1.0) assuming a rubberized pad, per ASSUMPTIONS.md "Gripper" table (sim-only proposed spec, no
# real gripper exists yet).
GRIPPER_FRICTION = [1.2, 0.005, 0.0001]

# Object friction. MuJoCo's own default rolling friction (0.0001) is realistic for a mathematically
# perfect sphere but means a sphere that picks up any spin from a bin-floor landing rolls for a
# very long time before stopping — physically defensible but impractical for a settle-check with a
# bounded step budget, and not representative of the small, slightly-deformable real objects this
# is meant to approximate. See ASSUMPTIONS.md "Scene" table.
OBJECT_FRICTION = [0.8, 0.005, 0.005]

# Position-actuator gains (MuJoCo-only control parameters, not part of URDF). Empirically tuned
# via a step-response sweep in rollout_smoke_test.py (settles within ~0.2 deg of a 10 deg step,
# well inside the 2 deg tolerance) — see ASSUMPTIONS.md "Arms" table.
ARM_ACTUATOR_KP = 60.0
ARM_ACTUATOR_KV = 6.0

# Gripper finger actuator gains — same kind of step-response tuning as the arms, but on a much
# lighter, shorter-travel prismatic joint (see ASSUMPTIONS.md "Gripper" table).
GRIPPER_ACTUATOR_KP = 200.0
GRIPPER_ACTUATOR_KV = 10.0


def _load_robot_spec() -> mujoco.MjSpec:
    """Load humanoid.urdf as an editable spec and apply MuJoCo-only physics properties."""
    spec = mujoco.MjSpec.from_file(str(URDF_PATH))

    # Without this, MuJoCo silently fuses any body connected by a fixed joint into its parent,
    # which would make torso_link (and later arm links) unaddressable by name — needed so later
    # milestones can attach arms/gripper/camera to specific named bodies.
    spec.compiler.fusestatic = False

    applied = set()
    for body in spec.bodies:
        for geom in body.geoms:
            if geom.name in GEOM_DENSITIES:
                geom.density = GEOM_DENSITIES[geom.name]
                applied.add(geom.name)
            if geom.name.endswith("_gripper_finger1_collision") or geom.name.endswith(
                "_gripper_finger2_collision"
            ):
                geom.friction = GRIPPER_FRICTION
    missing = set(GEOM_DENSITIES) - applied
    if missing:
        raise ValueError(
            f"GEOM_DENSITIES references geoms not found in {URDF_PATH.name}: {sorted(missing)}"
        )
    return spec


def _load_joint_yaml() -> dict:
    with open(JOINT_NAMES_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _load_joint_order() -> list[str]:
    return _load_joint_yaml()["joint_order"]


def _load_gripper_joint_order() -> list[str]:
    return _load_joint_yaml()["gripper_joint_order"]


def _add_position_actuator(
    scene: mujoco.MjSpec, joint_name: str, kp: float, kv: float, effort: float, jnt_range
) -> None:
    """Replicates MuJoCo's <position> shortcut via the low-level MjSpec API (gaintype=FIXED,
    biastype=AFFINE with [0, -kp, -kv]) — verified equivalent against a hand-written <position>
    element before use. ctrlrange is pinned to the joint's own URDF-declared range so a position
    command can never ask for an out-of-limits target; forcerange comes from the URDF <limit
    effort=".."/> (ARCHITECTURE.md's ODrive position+trapezoidal-trajectory control mode, not raw
    torque control — this is the steady-state gain approximation of that; trajectory shaping to
    match the trapezoidal profile itself is added in Milestone 6)."""
    scene.add_actuator(
        name=f"{joint_name}_position",
        target=joint_name,
        trntype=mujoco.mjtTrn.mjTRN_JOINT,
        gaintype=mujoco.mjtGain.mjGAIN_FIXED,
        gainprm=[kp, 0, 0] + [0] * 7,
        biastype=mujoco.mjtBias.mjBIAS_AFFINE,
        biasprm=[0, -kp, -kv] + [0] * 7,
        ctrllimited=True,
        ctrlrange=[jnt_range[0], jnt_range[1]],
        forcelimited=True,
        forcerange=[-effort, effort],
    )


def _add_gripper_mimic_constraint(scene: mujoco.MjSpec, side: str) -> None:
    """finger2 mechanically mirrors finger1 (finger2_qpos = finger1_qpos) via a MuJoCo equality
    constraint — URDF has no way to express this coupling, the concrete case motivating the
    URDF/MJCF split. finger2's joint axis is already sign-flipped in the URDF relative to
    finger1's, so a direct 1:1 copy (polycoef [0,1,0,0,0]) is what makes them open/close
    symmetrically about the gripper's centerline, verified in contact_smoke_test.py."""
    scene.add_equality(
        type=mujoco.mjtEq.mjEQ_JOINT,
        name1=f"{side}_gripper_finger2_joint",
        name2=f"{side}_gripper_finger1_joint",
        data=[0, 1, 0, 0, 0] + [0] * 6,
    )


def hfov_to_fovy(hfov_deg: float, width: int, height: int) -> float:
    """Convert a horizontal FOV (how camera specs are usually quoted) to MuJoCo's vertical fovy,
    for a given pixel resolution's aspect ratio -- so the effective FOV stays correct if the
    resolution changes, rather than hardcoding a fovy that's only right for one aspect ratio."""
    aspect = width / height
    half_h = math.radians(hfov_deg) / 2.0
    half_v = math.atan(math.tan(half_h) / aspect)
    return math.degrees(half_v) * 2.0


def _load_camera_config() -> dict:
    with open(CAMERA_CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _add_head_camera(scene: mujoco.MjSpec) -> None:
    """Rigid camera fixed to torso_link (MuJoCo-only -- cameras aren't part of what the real
    robot's future ikpy-based kinematics needs, so this lives entirely in the MJCF layer). Points
    forward and down at the workspace; see config/camera.yaml and ASSUMPTIONS.md "Camera" table
    for the mount offset/pitch/FOV rationale."""
    cfg = _load_camera_config()
    width, height = cfg["resolution_default"]
    fovy = hfov_to_fovy(cfg["horizontal_fov_deg"], width, height)

    # xyaxes: camera X (right) and Y (up) axes, expressed in the parent (torso) frame. Derived
    # from a view direction of (cos(pitch)*cos(yaw), cos(pitch)*sin(yaw), -sin(pitch)) -- horizontal
    # heading yaw_deg (0 = torso-forward/+X, matching the original robot-head-camera convention;
    # 180 = facing back toward the robot, used by the opposite-side-of-table placement, see
    # ASSUMPTIONS.md "Camera" table), tilted down by pitch_down_deg -- via right = viewdir x
    # world_up, up = right x viewdir. MuJoCo's camera looks along its own -Z, so
    # Z_cam = X_cam x Y_cam must equal -viewdir (verified numerically in camera_smoke_test.py by
    # checking the rendered scene is actually framed sensibly).
    pitch = math.radians(cfg["pitch_down_deg"])
    yaw = math.radians(cfg.get("yaw_deg", 0.0))
    view_dir = np.array([
        math.cos(pitch) * math.cos(yaw), math.cos(pitch) * math.sin(yaw), -math.sin(pitch),
    ])
    world_up = np.array([0.0, 0.0, 1.0])
    right = np.cross(view_dir, world_up)
    right /= np.linalg.norm(right)
    up = np.cross(right, view_dir)

    scene.body("torso_link").add_camera(
        name=cfg["name"],
        pos=cfg["mount_pos"],
        xyaxes=list(right) + list(up),
        fovy=fovy,
        resolution=[width, height],
    )


def _load_scene_config() -> dict:
    with open(SCENE_CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def bin_geometry_from_config(cfg: dict) -> tuple[float, float, float]:
    """(bin_center_x, bin_center_y, bin_floor_top_z) from config/scene.yaml -- the single formula
    both build_model.py (to place the bin geoms) and sim_env/domain_randomization.py (to know
    where to spawn objects) use, so the two can never drift apart."""
    t, b = cfg["table"], cfg["bin"]
    cx, cy = t["center_xy"]
    floor_top_z = t["top_height"] + t["top_thickness"] + b["wall_thickness"]
    return cx, cy, floor_top_z


def _add_table_and_bin(scene: mujoco.MjSpec, cfg: dict, include_bin: bool = True) -> tuple[float, float, float]:
    """Single-pedestal table + a 5-geom open-top bin sitting on it, both static (no joints) --
    plain geoms in worldbody, same pattern as the ground plane in scene.xml. Returns
    (bin_center_x, bin_center_y, bin_floor_top_z) for object spawning / reachability checks.

    include_bin=False skips the bin geoms entirely (table only) -- used by the simplified
    cube_grasp_env.py, which has nothing to knock an object out of and doesn't need the bin's
    knockout-margin geometry. The returned "floor" z is then just the table surface."""
    t = cfg["table"]
    cx, cy = t["center_xy"]
    top_z = t["top_height"]
    top_w, top_d = t["top_size_xy"]
    ped_w, ped_d = t["pedestal_size_xy"]
    thick = t["top_thickness"]

    scene.worldbody.add_geom(
        name="table_pedestal", type=mujoco.mjtGeom.mjGEOM_BOX,
        pos=[cx, cy, top_z / 2], size=[ped_w / 2, ped_d / 2, top_z / 2],
        rgba=[0.55, 0.4, 0.25, 1],
    )
    scene.worldbody.add_geom(
        name="table_top", type=mujoco.mjtGeom.mjGEOM_BOX,
        pos=[cx, cy, top_z + thick / 2], size=[top_w / 2, top_d / 2, thick / 2],
        rgba=[0.6, 0.45, 0.3, 1],
    )

    if not include_bin:
        return cx, cy, top_z + thick

    b = cfg["bin"]
    iw, idepth, ih = b["inner_size"]
    wt = b["wall_thickness"]
    floor_z = top_z + thick + wt / 2
    bin_rgba = [0.2, 0.5, 0.8, 0.2]  # low alpha so the walls read as a boundary outline, not a
    # solid tank -- at 0.6 the four semi-transparent walls stacked in the render made the (already
    # open-topped, floor + 4 walls, no lid) bin look like a closed glass aquarium

    scene.worldbody.add_geom(
        name="bin_floor", type=mujoco.mjtGeom.mjGEOM_BOX,
        pos=[cx, cy, floor_z], size=[iw / 2 + wt, idepth / 2 + wt, wt / 2], rgba=bin_rgba,
    )
    wall_z = floor_z + wt / 2 + ih / 2
    # front/back walls (span the inner depth, offset along X)
    for name, sign in (("bin_wall_front", +1), ("bin_wall_back", -1)):
        scene.worldbody.add_geom(
            name=name, type=mujoco.mjtGeom.mjGEOM_BOX,
            pos=[cx + sign * (iw / 2 + wt / 2), cy, wall_z],
            size=[wt / 2, idepth / 2 + wt, ih / 2], rgba=bin_rgba,
        )
    # left/right walls (span the inner width, offset along Y)
    for name, sign in (("bin_wall_left", +1), ("bin_wall_right", -1)):
        scene.worldbody.add_geom(
            name=name, type=mujoco.mjtGeom.mjGEOM_BOX,
            pos=[cx, cy + sign * (idepth / 2 + wt / 2), wall_z],
            size=[iw / 2, wt / 2, ih / 2], rgba=bin_rgba,
        )

    return bin_geometry_from_config(cfg)


def _load_pick_place_scene_config() -> dict:
    with open(PICK_PLACE_SCENE_CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def pick_place_geometry_from_config(cfg: dict) -> dict:
    """(x, y, floor_top_z) for the source ("left") and destination ("right") boxes -- the single
    formula both build_model.py (to place the box geoms) and sim_env/domain_randomization.py (to
    know where to spawn/check the cube) use, mirroring bin_geometry_from_config's role for the
    single-bin task."""
    t, b = cfg["table"], cfg["boxes"]
    floor_top_z = t["top_height"] + t["top_thickness"] + b["wall_thickness"]
    src_x, src_y = b["source"]["center_xy"]
    dst_x, dst_y = b["destination"]["center_xy"]
    return {"source": (src_x, src_y, floor_top_z), "destination": (dst_x, dst_y, floor_top_z)}


def _add_open_box(
    scene: mujoco.MjSpec, name_prefix: str, cx: float, cy: float, floor_top_z: float,
    inner_size: list[float], wall_thickness: float, rgba: list[float],
) -> None:
    """One open-top box (floor + 4 walls, all static geoms) -- factored out of
    _add_table_and_bin's inline bin-wall code so the pick-place task's two boxes (source and
    destination) share it instead of duplicating the geometry math."""
    iw, idepth, ih = inner_size
    wt = wall_thickness
    floor_z = floor_top_z - wt / 2  # center of the floor slab

    scene.worldbody.add_geom(
        name=f"{name_prefix}_floor", type=mujoco.mjtGeom.mjGEOM_BOX,
        pos=[cx, cy, floor_z], size=[iw / 2 + wt, idepth / 2 + wt, wt / 2], rgba=rgba,
    )
    wall_z = floor_z + wt / 2 + ih / 2
    for name, sign in ((f"{name_prefix}_wall_front", +1), (f"{name_prefix}_wall_back", -1)):
        scene.worldbody.add_geom(
            name=name, type=mujoco.mjtGeom.mjGEOM_BOX,
            pos=[cx + sign * (iw / 2 + wt / 2), cy, wall_z],
            size=[wt / 2, idepth / 2 + wt, ih / 2], rgba=rgba,
        )
    for name, sign in ((f"{name_prefix}_wall_left", +1), (f"{name_prefix}_wall_right", -1)):
        scene.worldbody.add_geom(
            name=name, type=mujoco.mjtGeom.mjGEOM_BOX,
            pos=[cx, cy + sign * (idepth / 2 + wt / 2), wall_z],
            size=[iw / 2, wt / 2, ih / 2], rgba=rgba,
        )


def _add_pick_place_furniture(scene: mujoco.MjSpec, cfg: dict) -> dict:
    """Table + two open boxes (source/"left", destination/"right") for the suction pick-place
    task -- independent of _add_table_and_bin (the single-bin task's furniture), so that task
    stays untouched. Returns pick_place_geometry_from_config(cfg)."""
    t = cfg["table"]
    cx, cy = t["center_xy"]
    top_z = t["top_height"]
    top_w, top_d = t["top_size_xy"]
    ped_w, ped_d = t["pedestal_size_xy"]
    thick = t["top_thickness"]

    scene.worldbody.add_geom(
        name="pp_table_pedestal", type=mujoco.mjtGeom.mjGEOM_BOX,
        pos=[cx, cy, top_z / 2], size=[ped_w / 2, ped_d / 2, top_z / 2],
        rgba=[0.55, 0.4, 0.25, 1],
    )
    scene.worldbody.add_geom(
        name="pp_table_top", type=mujoco.mjtGeom.mjGEOM_BOX,
        pos=[cx, cy, top_z + thick / 2], size=[top_w / 2, top_d / 2, thick / 2],
        rgba=[0.6, 0.45, 0.3, 1],
    )

    geom = pick_place_geometry_from_config(cfg)
    b = cfg["boxes"]
    src_x, src_y, floor_top_z = geom["source"]
    dst_x, dst_y, _ = geom["destination"]
    # Distinct colours (amber source / green destination) so the dashboard video reads unambiguously
    # at a glance, low alpha for the same reason bin-picking's walls were dimmed (ASSUMPTIONS.md).
    _add_open_box(scene, "box_source", src_x, src_y, floor_top_z, b["inner_size"], b["wall_thickness"], [0.85, 0.55, 0.15, 0.35])
    _add_open_box(scene, "box_dest", dst_x, dst_y, floor_top_z, b["inner_size"], b["wall_thickness"], [0.15, 0.65, 0.35, 0.35])
    return geom


def _add_pick_place_cube(scene: mujoco.MjSpec, cfg: dict, spawn_x: float, spawn_y: float, floor_top_z: float) -> None:
    """Single free-body cube, "object_0" (same name the env/reward code expects, matching the
    bin-picking task's convention) -- this task never needs more than one object, so there's no
    multi-slot roster like _add_object_slots."""
    c = cfg["cube"]
    half = c["half_size_m"]
    body = scene.worldbody.add_body(name="object_0", pos=[spawn_x, spawn_y, floor_top_z + half + 0.005])
    body.add_freejoint(name="object_0_freejoint")
    body.add_geom(
        name="object_0_collision", type=mujoco.mjtGeom.mjGEOM_BOX,
        size=[half, half, half], mass=c["mass_g"] / 1000.0,
        friction=OBJECT_FRICTION, rgba=[0.9, 0.3, 0.2, 1],
    )


def _neutralize_gripper_fingers(scene: mujoco.MjSpec) -> None:
    """Shrink + de-collide both sides' finger collision geoms for the suction task only. These
    prong-shaped boxes (0.015x0.008x0.05m, sticking ~5cm past the gripper base) are leftovers from
    the bin-picking task's finger-grasp gripper -- suction attaches via the gripper base's own
    collision geom + a weld constraint (_add_suction_weld), not the fingers. Left in place with
    collision enabled, they were never excluded from MuJoCo's default contact resolution (only
    upper_arm/forearm are checked by SuctionPickPlaceEnv._is_arm_collision), so they could
    physically snag on the box walls -- real contact forces, not just a missed reward penalty. The
    joints/mimic-constraint/actuator stay in the model (harmless -- SuctionPickPlaceEnv holds them
    at a fixed ctrl value and never actuates them); only their collision geoms + visibility change.
    Bin-picking's build_spec path never calls this, so its finger-grasp gripper is untouched."""
    for side in ("left", "right"):
        for finger in ("finger1", "finger2"):
            geom = scene.geom(f"{side}_gripper_{finger}_collision")
            geom.size = [0.001, 0.001, 0.001]
            geom.contype = 0
            geom.conaffinity = 0
            rgba = list(geom.rgba)
            rgba[3] = 0.0
            geom.rgba = rgba


def _add_suction_weld(scene: mujoco.MjSpec, side: str) -> None:
    """A weld equality constraint between {side}_gripper_base_link and object_0, compiled inactive
    (active=False) -- SuctionPickPlaceEnv toggles it on/off per step via data.eq_active (a plain
    mutable MjData array, no recompile needed, MuJoCo 3.1+) to model suction attach/detach. anchor
    and relpose (model.eq_data) get overwritten by the env at the moment of attachment to the
    object's CURRENT relative pose -- so the object welds on wherever it actually is when suction
    fires, not a fixed pose baked in at compile time. See sim_env/suction_pick_place_env.py's
    _attach_suction for the data layout ([anchor(3), relpose_pos(3), relpose_quat(4),
    torquescale(1)] = 11 floats, mujoco.mjNEQDATA)."""
    scene.add_equality(
        name=f"{side}_suction_weld",
        type=mujoco.mjtEq.mjEQ_WELD,
        objtype=mujoco.mjtObj.mjOBJ_BODY,
        name1=f"{side}_gripper_base_link",
        name2="object_0",
        active=False,
        data=[0.0] * 11,
    )


def _add_object_slots(
    scene: mujoco.MjSpec, cfg: dict, bin_center_x: float, bin_center_y: float, bin_floor_z: float,
    n_objects: int | None = None,
) -> None:
    """A fixed roster of `max_count` free-body objects compiled into the model (geom type/size
    are compile-time/structural in MuJoCo, so they can't be randomized per-episode without a
    recompile -- domain_randomization.py instead randomizes pose every reset, and mass/friction
    via direct model-array mutation, which MuJoCo does allow post-compile). Spawned at rest,
    centered in the bin, one per slot, purely so the compiled model is valid/inspectable before
    any randomization runs -- actual episode-start poses come from domain_randomization.py.

    n_objects overrides how many slots get compiled (default: cfg's max_count) -- used by
    cube_grasp_env.py to compile exactly one object (object_0, always a cube per the shapes
    roster's index 0) instead of the full 4-slot bin-picking roster."""
    o = cfg["objects"]
    half_size = sum(o["half_size_range_m"]) / 2.0
    mass_kg = (sum(o["mass_range_g"]) / 2.0) / 1000.0
    count = o["max_count"] if n_objects is None else n_objects

    for i in range(count):
        shape = o["shapes"][i % len(o["shapes"])]
        geomtype = _SHAPE_TO_GEOMTYPE[shape]
        body = scene.worldbody.add_body(
            name=f"object_{i}", pos=[bin_center_x, bin_center_y, bin_floor_z + half_size + 0.001 + i * 0.03]
        )
        body.add_freejoint(name=f"object_{i}_freejoint")
        size = [half_size, half_size, half_size] if geomtype == mujoco.mjtGeom.mjGEOM_BOX else (
            [half_size, half_size, 0] if geomtype == mujoco.mjtGeom.mjGEOM_CYLINDER else [half_size, 0, 0]
        )
        body.add_geom(
            name=f"object_{i}_collision", type=geomtype, size=size, mass=mass_kg,
            friction=OBJECT_FRICTION,
            rgba=[0.9, 0.3, 0.2, 1] if shape == "cube" else (
                [0.2, 0.8, 0.3, 1] if shape == "cylinder" else [0.9, 0.8, 0.1, 1]
            ),
        )


def build_spec(
    include_scene_furniture: bool = True, include_bin: bool = True, n_objects: int | None = None,
    task: str = "bin_picking",
) -> mujoco.MjSpec:
    """Compose the editable (uncompiled) spec: scene shell + robot, attached at the fixed mount,
    plus the MuJoCo-only position actuators for every joint in config/joint_names.yaml, the
    gripper's finger-mimic constraints, and the head camera.

    include_scene_furniture=False skips the table/bin/objects, producing a robot-only model.
    Used by tests that specifically validate the robot's own actuator/joint dynamics (e.g.
    rollout_smoke_test.py's step-response settle check) against arbitrary test poses that would
    otherwise legitimately collide with nearby scene furniture -- that's a real, expected physical
    interaction once the workspace is populated, not an actuator-tuning defect, so it shouldn't
    be conflated with the actuator-gain check. Every other consumer (the Gymnasium env, the RL
    trainer, all other verification scripts) uses the default full scene.

    task="suction_pick_place" swaps the single-bin furniture for the two-box (source/destination)
    table used by sim_env/suction_pick_place_env.py, and additionally compiles a per-side weld
    equality constraint (inactive by default) that env toggles to model suction attach/detach.
    include_bin/n_objects are ignored in this mode (this task always has exactly one cube, no
    multi-object roster)."""
    scene = mujoco.MjSpec.from_file(str(SCENE_PATH))
    robot = _load_robot_spec()

    mount_frame = scene.frame("robot_mount")
    scene.attach(robot, prefix="", frame=mount_frame)

    for joint_name in _load_joint_order():
        joint = scene.joint(joint_name)
        effort = float(joint.actfrcrange[1]) if joint.actfrcrange[1] > 0 else 3.0
        _add_position_actuator(
            scene, joint_name, ARM_ACTUATOR_KP, ARM_ACTUATOR_KV, effort, joint.range
        )

    for joint_name in _load_gripper_joint_order():
        joint = scene.joint(joint_name)
        effort = float(joint.actfrcrange[1]) if joint.actfrcrange[1] > 0 else 10.0
        _add_position_actuator(
            scene, joint_name, GRIPPER_ACTUATOR_KP, GRIPPER_ACTUATOR_KV, effort, joint.range
        )

    for side in ("left", "right"):
        _add_gripper_mimic_constraint(scene, side)
        # shoulder_yaw_link's actuator-lump proxy geom (a plain 0.025 m box, standing in for an
        # ODrive Mini, not real robot geometry -- see GEOM_DENSITIES) sits at the same shoulder
        # mount point the pitch/roll/upper-arm cluster already packs tightly. MuJoCo auto-excludes
        # contact between direct parent/child body pairs (yaw_link vs shoulder_link never
        # collide), but shoulder_yaw_link and upper_arm_link are two joints apart, so without this
        # explicit exclude they interpenetrate ~1 cm at rest -- confirmed via data.contact -- and
        # the resulting repulsion force overwhelms the pitch/roll position actuators (measured:
        # pitch/roll stuck within ~1 deg of 0 under a 10 deg step command that used to settle
        # cleanly). Excluding here matches the same "these are non-physical actuator-lump proxies,
        # not real self-collision surfaces" reasoning already implicit in every other adjacent-body
        # exclusion in this design.
        scene.add_exclude(bodyname1=f"{side}_shoulder_yaw_link", bodyname2=f"{side}_upper_arm_link")

    _add_head_camera(scene)

    if task == "suction_pick_place":
        _neutralize_gripper_fingers(scene)
        pp_cfg = _load_pick_place_scene_config()
        geom = _add_pick_place_furniture(scene, pp_cfg)
        src_x, src_y, floor_top_z = geom["source"]
        _add_pick_place_cube(scene, pp_cfg, src_x, src_y, floor_top_z)
        for side in ("left", "right"):
            _add_suction_weld(scene, side)
    elif include_scene_furniture:
        scene_cfg = _load_scene_config()
        bin_cx, bin_cy, bin_floor_z = _add_table_and_bin(scene, scene_cfg, include_bin=include_bin)
        _add_object_slots(scene, scene_cfg, bin_cx, bin_cy, bin_floor_z, n_objects=n_objects)

    return scene


def load_model(
    include_scene_furniture: bool = True, include_bin: bool = True, n_objects: int | None = None,
    task: str = "bin_picking",
) -> tuple[mujoco.MjModel, mujoco.MjData]:
    """Build and compile the model. Also dumps the flattened MJCF for human inspection/diffing,
    but only for the default full bin-picking build -- other variants (e.g. cube_grasp_env.py's
    no-bin/single-object build) skip the dump rather than clobbering that debug artifact with a
    different scene."""
    spec = build_spec(
        include_scene_furniture=include_scene_furniture, include_bin=include_bin,
        n_objects=n_objects, task=task,
    )
    model = spec.compile()
    data = mujoco.MjData(model)

    if task == "suction_pick_place":
        GENERATED_DIR.mkdir(parents=True, exist_ok=True)
        header = (
            "<!--\n"
            "  GENERATED by scripts/build_model.py (task=suction_pick_place) — do NOT hand-edit.\n"
            "  Source of truth: models/urdf/humanoid.urdf + models/mjcf/scene.xml + build_model.py.\n"
            "-->\n"
        )
        GENERATED_PICK_PLACE_SCENE_PATH.write_text(header + spec.to_xml(), encoding="utf-8")
    elif include_scene_furniture and include_bin and n_objects is None:
        GENERATED_DIR.mkdir(parents=True, exist_ok=True)
        header = (
            "<!--\n"
            "  GENERATED by scripts/build_model.py — do NOT hand-edit.\n"
            "  Source of truth: models/urdf/humanoid.urdf + models/mjcf/scene.xml + build_model.py.\n"
            "-->\n"
        )
        GENERATED_SCENE_PATH.write_text(header + spec.to_xml(), encoding="utf-8")

    return model, data


if __name__ == "__main__":
    m, d = load_model()
    print(f"Compiled OK: {m.nbody} bodies, {m.njnt} joints, {m.nu} actuators, total mass "
          f"{sum(m.body(i).mass[0] for i in range(m.nbody)):.3f} kg")
