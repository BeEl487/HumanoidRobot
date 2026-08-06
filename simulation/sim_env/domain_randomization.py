"""Domain randomization for the bin-picking scene: object pose/count/friction per reset, and a
lighting-jitter schema for Milestone 7's vision pipeline.

Object geometry (shape/size) is fixed at compile time -- MuJoCo can't change a geom's type or
size without recompiling the model, which is too slow to do every RL episode reset. What *can*
change post-compile (and is what actually varies episode-to-episode) is pose, friction, and
lighting -- all plain mutable arrays on MjModel/MjData, no recompilation needed.
"""

from __future__ import annotations

import pathlib

import mujoco
import numpy as np
import yaml

SCENE_CONFIG_PATH = pathlib.Path(__file__).resolve().parent.parent / "config" / "scene.yaml"


def _load_scene_config() -> dict:
    with open(SCENE_CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def bin_geometry_from_config(cfg: dict) -> tuple[float, float, float]:
    """(bin_center_x, bin_center_y, bin_floor_top_z) -- must match
    scripts/build_model.py:bin_geometry_from_config exactly (same formula, duplicated rather than
    imported to keep sim_env/ independent of scripts/ as a runtime dependency; a mismatch would
    be caught immediately by check_scene_settle.py-style spawn/interpenetration checks)."""
    t, b = cfg["table"], cfg["bin"]
    cx, cy = t["center_xy"]
    floor_top_z = t["top_height"] + t["top_thickness"] + b["wall_thickness"]
    return cx, cy, floor_top_z


def randomize_objects(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    rng: np.random.Generator,
    count: int | None = None,
    active_slots: list[int] | None = None,
) -> int:
    """Reset every object slot's freejoint qpos/qvel. `count` slots (random within
    scene.yaml's objects.count_range if not given) get a randomized pose above the bin floor
    (random XY within the bin footprint minus a keep-out margin, random drop height, random yaw);
    remaining slots are parked far outside the workspace so they don't interfere physically or
    appear in camera view. Returns the actual active count.

    active_slots overrides which slots get activated (still `count`-many of them, taken in the
    order given) -- used by BinPickingEnv, which always tracks slot 0 as its fixed grasp target
    and would otherwise have it parked out of the workspace whenever the random slot permutation
    happened to pick a different slot (this was an actual bug caught by check_env.py: a scripted
    approach controller saw the target object missing in ~3/4 of episodes)."""
    cfg = _load_scene_config()
    obj_cfg = cfg["objects"]
    max_count = obj_cfg["max_count"]
    if count is None:
        count = int(rng.integers(obj_cfg["count_range"][0], obj_cfg["count_range"][1] + 1))
    count = min(count, max_count)

    bin_cx, bin_cy, bin_floor_z = bin_geometry_from_config(cfg)
    inner_w, inner_d, _ = cfg["bin"]["inner_size"]
    margin = obj_cfg["spawn_margin_m"]
    half_w = max(inner_w / 2 - margin, 0.005)
    half_d = max(inner_d / 2 - margin, 0.005)

    if active_slots is not None:
        active_slots = list(active_slots)[:count]
    else:
        active_slots = rng.permutation(max_count)[:count]
    for i in range(max_count):
        joint_name = f"object_{i}_freejoint"
        qposadr = model.joint(joint_name).qposadr[0]
        dofadr = model.joint(joint_name).dofadr[0]
        if i in active_slots:
            x = bin_cx + rng.uniform(-half_w, half_w)
            y = bin_cy + rng.uniform(-half_d, half_d)
            z = bin_floor_z + rng.uniform(*obj_cfg["drop_height_range_m"])
            yaw = rng.uniform(-np.pi, np.pi)
            data.qpos[qposadr:qposadr + 3] = [x, y, z]
            data.qpos[qposadr + 3:qposadr + 7] = [np.cos(yaw / 2), 0, 0, np.sin(yaw / 2)]
        else:
            # parked below the ground plane, well outside the workspace and camera frustum
            data.qpos[qposadr:qposadr + 3] = [10.0 + i, 10.0, -5.0]
            data.qpos[qposadr + 3:qposadr + 7] = [1, 0, 0, 0]
        data.qvel[dofadr:dofadr + 6] = 0.0
    return count


def randomize_object_friction(model: mujoco.MjModel, rng: np.random.Generator) -> None:
    """+/- friction_jitter_pct around each object geom's nominal sliding friction. The nominal
    value is read from build_model.OBJECT_FRICTION (the fixed baseline set at build time), NOT
    from the geom's current friction -- reading current state would jitter around whatever the
    *previous* call left behind, compounding into unbounded drift across repeated calls (caught
    by check_domain_randomization.py). geom_friction is a plain mutable MjModel array, so setting
    it needs no recompilation."""
    import build_model  # local import: avoids sim_env/ depending on scripts/ at module load time

    nominal = build_model.OBJECT_FRICTION[0]
    cfg = _load_scene_config()["objects"]
    pct = cfg["friction_jitter_pct"] / 100.0
    for i in range(cfg["max_count"]):
        geom_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, f"object_{i}_collision")
        if geom_id == -1:
            continue
        model.geom_friction[geom_id, 0] = nominal * (1.0 + rng.uniform(-pct, pct))


def randomize_lighting(model: mujoco.MjModel, rng: np.random.Generator) -> None:
    """Jitter the key light's position and the scene's ambient level. Schema/plumbing defined now
    (Milestone 5, since it's just model-array mutation, no rendering dependency) but not yet
    exercised by any vision code -- nothing calls this until Milestone 7's camera observations."""
    cfg = _load_scene_config()["lighting"]
    jitter = cfg["key_light_pos_jitter_m"]
    model.light_pos[0] = model.light_pos[0] + rng.uniform(-jitter, jitter, size=3)
    lo, hi = cfg["ambient_range"]
    model.light_ambient[0, :] = rng.uniform(lo, hi)
