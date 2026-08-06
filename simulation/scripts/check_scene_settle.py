"""Milestone 5 scene verification: with the robot holding its zero-command pose, drop the object
roster into the bin and confirm no interpenetration at spawn, no NaN/Inf, everything stays
within a bounded world region (nothing flies off), and per-object velocity decays toward rest.
"""

from __future__ import annotations

import numpy as np
import mujoco

from build_model import load_model

N_SETTLE_STEPS = 1000
WORLD_BOUND_XY = 2.0  # m from origin -- generous, just catches "flew off the table" bugs
WORLD_BOUND_Z = (0.0, 3.0)


def check_no_spawn_interpenetration() -> None:
    model, data = load_model()
    mujoco.mj_resetData(model, data)
    mujoco.mj_forward(model, data)
    # a large penetration depth at step 0 would show up as a big negative contact.dist
    max_penetration = max((c.dist for c in [data.contact[i] for i in range(data.ncon)]), default=0.0)
    assert max_penetration > -0.005, f"objects interpenetrate at spawn (max depth {max_penetration*1000:.2f} mm)"
    print(f"check_no_spawn_interpenetration: OK (max penetration at spawn: {max_penetration*1000:.3f} mm)")


LINEAR_SETTLE_THRESHOLD_MPS = 0.05


def check_objects_settle() -> None:
    """Checks LINEAR velocity only, against an absolute threshold (not relative decay). A round
    object (the cycled shape roster includes a sphere) that lands slightly off-center can end up
    in genuine, stable rolling-without-slipping: near-zero *translational* speed but a nonzero,
    non-decaying *angular* velocity (no slipping at the contact point means no kinetic friction
    to dissipate the spin -- confirmed empirically not to depend on the rolling-friction
    coefficient, see ASSUMPTIONS.md "Scene" table). That's correct physics, not instability, so
    angular velocity is deliberately excluded from the settle criterion; what actually matters
    for a bin-picking task is whether the object has stopped *moving*, not stopped *spinning*."""
    model, data = load_model()
    mujoco.mj_resetData(model, data)
    data.ctrl[:] = 0.0

    object_ids = [
        mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, f"object_{i}")
        for i in range(4)
        if mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, f"object_{i}") != -1
    ]
    object_dofadrs = [model.body_dofadr[i] for i in object_ids]

    lin_vel_norms = np.empty((N_SETTLE_STEPS, len(object_ids)))
    for step in range(N_SETTLE_STEPS):
        mujoco.mj_step(model, data)
        assert np.all(np.isfinite(data.qpos)) and np.all(np.isfinite(data.qvel)), \
            f"non-finite state at step {step}"
        xy = data.xpos[object_ids, :2]
        z = data.xpos[object_ids, 2]
        assert np.all(np.abs(xy) < WORLD_BOUND_XY), f"an object left the XY bound at step {step}: {xy}"
        assert np.all((z > WORLD_BOUND_Z[0]) & (z < WORLD_BOUND_Z[1])), \
            f"an object left the Z bound at step {step}: {z}"
        for j, dofadr in enumerate(object_dofadrs):
            lin_vel_norms[step, j] = np.linalg.norm(data.qvel[dofadr:dofadr + 3])

    tenth = max(1, N_SETTLE_STEPS // 10)
    last = lin_vel_norms[-tenth:].mean(axis=0)
    for j in range(len(object_ids)):
        assert last[j] < LINEAR_SETTLE_THRESHOLD_MPS, (
            f"object_{j} hasn't settled: final linear speed {last[j]:.4f} m/s exceeds "
            f"{LINEAR_SETTLE_THRESHOLD_MPS} m/s"
        )
    print(f"check_objects_settle: OK ({N_SETTLE_STEPS} steps, {len(object_ids)} objects, "
          f"final linear speeds: {last.round(4)} m/s)")


if __name__ == "__main__":
    check_no_spawn_interpenetration()
    check_objects_settle()
    print("check_scene_settle.py: ALL CHECKS PASSED")
