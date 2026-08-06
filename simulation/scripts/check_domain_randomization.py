"""Milestone 5 domain-randomization verification: repeated randomize_objects() calls with
different seeds stay within configured ranges and vary count; same-seed calls reproduce
identically; friction/lighting jitter stay within their configured bounds too.
"""

from __future__ import annotations

import pathlib
import sys

import numpy as np
import mujoco
import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "sim_env"))

from build_model import load_model  # noqa: E402
from domain_randomization import (  # noqa: E402
    bin_geometry_from_config,
    randomize_lighting,
    randomize_object_friction,
    randomize_objects,
)

SCENE_CONFIG_PATH = pathlib.Path(__file__).resolve().parent.parent / "config" / "scene.yaml"
N_TRIALS = 50


def check_ranges_and_variety() -> None:
    with open(SCENE_CONFIG_PATH, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    obj_cfg = cfg["objects"]
    bin_cx, bin_cy, bin_floor_z = bin_geometry_from_config(cfg)
    inner_w, inner_d, _ = cfg["bin"]["inner_size"]
    margin = obj_cfg["spawn_margin_m"]
    half_w, half_d = inner_w / 2 - margin, inner_d / 2 - margin
    lo_h, hi_h = obj_cfg["drop_height_range_m"]

    model, data = load_model()
    counts = []
    for trial in range(N_TRIALS):
        rng = np.random.default_rng(trial)
        count = randomize_objects(model, data, rng)
        counts.append(count)
        assert obj_cfg["count_range"][0] <= count <= obj_cfg["count_range"][1], \
            f"trial {trial}: count {count} outside configured range"
        active = 0
        for i in range(obj_cfg["max_count"]):
            qposadr = model.joint(f"object_{i}_freejoint").qposadr[0]
            x, y, z = data.qpos[qposadr:qposadr + 3]
            if z > 0:  # parked slots are placed at z=-5
                active += 1
                assert bin_cx - half_w - 1e-6 <= x <= bin_cx + half_w + 1e-6, f"trial {trial} obj {i}: x={x} out of range"
                assert bin_cy - half_d - 1e-6 <= y <= bin_cy + half_d + 1e-6, f"trial {trial} obj {i}: y={y} out of range"
                assert bin_floor_z + lo_h - 1e-6 <= z <= bin_floor_z + hi_h + 1e-6, f"trial {trial} obj {i}: z={z} out of range"
        assert active == count, f"trial {trial}: {active} active slots but count()={count}"

    assert len(set(counts)) > 1, f"count never varied across {N_TRIALS} trials: {counts}"
    print(f"check_ranges_and_variety: OK ({N_TRIALS} trials, all poses within configured ranges, "
          f"counts varied: {sorted(set(counts))})")


def check_determinism() -> None:
    model, data = load_model()
    rng1 = np.random.default_rng(7)
    randomize_objects(model, data, rng1)
    qpos1 = data.qpos.copy()

    model2, data2 = load_model()
    rng2 = np.random.default_rng(7)
    randomize_objects(model2, data2, rng2)
    qpos2 = data2.qpos.copy()

    assert np.array_equal(qpos1, qpos2), "same-seed randomize_objects calls produced different poses"
    print("check_determinism: OK (same-seed calls reproduce identically)")


def check_friction_and_lighting_jitter() -> None:
    with open(SCENE_CONFIG_PATH, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    pct = cfg["objects"]["friction_jitter_pct"] / 100.0
    lo_amb, hi_amb = cfg["lighting"]["ambient_range"]

    model, data = load_model()
    nominal = model.geom_friction[mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, "object_0_collision"), 0]
    for trial in range(N_TRIALS):
        rng = np.random.default_rng(100 + trial)
        randomize_object_friction(model, rng)
        f = model.geom_friction[mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, "object_0_collision"), 0]
        assert nominal * (1 - pct) - 1e-9 <= f <= nominal * (1 + pct) + 1e-9, \
            f"trial {trial}: friction {f} outside +/-{pct*100:.0f}% of nominal {nominal}"

        randomize_lighting(model, rng)
        assert lo_amb - 1e-9 <= model.light_ambient[0, 0] <= hi_amb + 1e-9, \
            f"trial {trial}: ambient {model.light_ambient[0]} outside configured range"
    print(f"check_friction_and_lighting_jitter: OK ({N_TRIALS} trials, friction and ambient "
          "stayed within configured ranges)")


if __name__ == "__main__":
    check_ranges_and_variety()
    check_determinism()
    check_friction_and_lighting_jitter()
    print("check_domain_randomization.py: ALL CHECKS PASSED")
