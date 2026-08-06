"""Milestone 2 dynamic-stability verification for the arms (the model's first moving subsystem):
zero-command hold, small-amplitude tracking accuracy (validates the position-actuator kp/kv
aren't nonsense), rollout determinism, and an FK sanity check that shoulder_roll actually swings
the arm sideways rather than spinning it uselessly about its own long axis.
"""

from __future__ import annotations

import numpy as np
import mujoco

from build_model import load_model, _load_joint_order, _load_gripper_joint_order

N_HOLD_STEPS = 2000
N_STEP_RESPONSE_STEPS = 1500  # 3 s at dt=0.002 -- long enough to settle given the tuned kp/kv
SETTLE_FRACTION = 0.2  # final 20% of the step-response rollout used for the settle-accuracy check
STEP_TARGET_DEG = 10.0
ANGLE_TOL_RAD = np.deg2rad(2.0)


def zero_command_hold() -> None:
    """Zero-control hold, scoped to the robot's own actuated joints (not free-jointed scene
    objects, added in Milestone 5): limit checking only applies to the robot's limited
    (hinge/slide) joints, indexed by qposadr -- a blind data.qpos-vs-jnt_range compare no longer
    lines up shape-wise once 7-wide free-joint qpos blocks exist. Similarly the qvel-growth
    heuristic is scoped to the robot's own DOFs -- objects settling from a drop (including a
    low-rolling-friction sphere that keeps a small steady spin) legitimately have nonzero
    late-rollout velocity that isn't a robot-joint instability; the scene's own settle behavior
    is checked separately by check_scene_settle.py, matching the Milestone 5 plan."""
    model, data = load_model()
    mujoco.mj_resetData(model, data)
    data.ctrl[:] = 0.0

    robot_joint_names = _load_joint_order() + _load_gripper_joint_order()
    robot_dofadrs = [model.joint(n).dofadr[0] for n in robot_joint_names]
    limited_joint_ids = [i for i in range(model.njnt) if model.jnt_limited[i]]
    limited_qposadrs = [model.jnt_qposadr[i] for i in limited_joint_ids]
    lo = model.jnt_range[limited_joint_ids, 0]
    hi = model.jnt_range[limited_joint_ids, 1]

    qvel_norms = np.empty(N_HOLD_STEPS)
    for step in range(N_HOLD_STEPS):
        mujoco.mj_step(model, data)
        assert np.all(np.isfinite(data.qpos)) and np.all(np.isfinite(data.qvel)), \
            f"non-finite qpos/qvel at step {step}"
        limited_qpos = data.qpos[limited_qposadrs]
        assert np.all(limited_qpos >= lo - 1e-3) and np.all(limited_qpos <= hi + 1e-3), \
            f"joint limit violated at step {step}: qpos={limited_qpos}"
        qvel_norms[step] = np.linalg.norm(data.qvel[robot_dofadrs])
    tenth = max(1, N_HOLD_STEPS // 10)
    first, last = qvel_norms[:tenth].mean(), qvel_norms[-tenth:].mean()
    assert last < 2 * first + 1e-6, f"robot-joint qvel grew: first10%={first:.4f} last10%={last:.4f}"
    print(f"zero_command_hold: OK ({N_HOLD_STEPS} steps, robot-joint qvel |first10%|={first:.4f} "
          f"|last10%|={last:.4f})")


def step_response_settle() -> None:
    """Step every ARM joint (the ones this test's angular tolerance applies to — the gripper's
    own settling behavior is separately checked by contact_smoke_test.py's mimic-tracking test,
    since its target unit is meters, not degrees) to a fixed small-amplitude target and confirm
    it settles within tolerance. This validates the position-actuator kp/kv aren't nonsense — a
    continuous sinusoidal target would conflate settling accuracy with phase lag, hence a step.

    Uses the robot-only model (no table/bin/objects, see build_model.load_model's
    include_scene_furniture) -- once the workspace was populated (Milestone 5) this generic
    all-joints-to-10-degrees test pose legitimately collides with the now-much-closer table/bin,
    which is a real physical interaction the actuator can't and shouldn't just power through, not
    an actuator-tuning defect. What this check validates (gain sanity) is properly isolated from
    what changed (a populated workspace) by testing the robot in isolation."""
    model, data = load_model(include_scene_furniture=False)
    mujoco.mj_resetData(model, data)
    arm_joint_names = _load_joint_order()
    qposadrs = [model.joint(n).qposadr[0] for n in arm_joint_names]
    actuator_ids = [
        mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_ACTUATOR, f"{n}_position") for n in arm_joint_names
    ]
    target_val = np.deg2rad(STEP_TARGET_DEG)
    qpos_hist = np.empty((N_STEP_RESPONSE_STEPS, len(arm_joint_names)))
    for step in range(N_STEP_RESPONSE_STEPS):
        for act_id in actuator_ids:
            data.ctrl[act_id] = target_val
        mujoco.mj_step(model, data)
        assert np.all(np.isfinite(data.qpos)), f"non-finite qpos at step {step}"
        qpos_hist[step] = data.qpos[qposadrs]
    tail = int(N_STEP_RESPONSE_STEPS * SETTLE_FRACTION)
    max_err = np.abs(qpos_hist[-tail:] - target_val).max()
    assert max_err < ANGLE_TOL_RAD, \
        f"settle error {np.rad2deg(max_err):.2f} deg exceeds {np.rad2deg(ANGLE_TOL_RAD):.0f} deg tolerance"
    print(f"step_response_settle: OK (max error over final {int(SETTLE_FRACTION*100)}% of a "
          f"{STEP_TARGET_DEG:.0f} deg step: {np.rad2deg(max_err):.3f} deg)")


def determinism() -> None:
    def run() -> np.ndarray:
        model, data = load_model()
        mujoco.mj_resetData(model, data)
        rng = np.random.default_rng(42)
        traj = np.empty((200, model.nq))
        for step in range(200):
            data.ctrl[:] = rng.uniform(-0.3, 0.3, size=model.nu)
            mujoco.mj_step(model, data)
            traj[step] = data.qpos
        return traj

    t1, t2 = run(), run()
    assert np.array_equal(t1, t2), "determinism check failed: identical-seed rollouts diverged"
    print("determinism: OK (two identical-seed rollouts match exactly)")


def fk_sanity_check() -> None:
    """shoulder_roll rotates about the fore-aft (X) axis, perpendicular to the down-hanging arm's
    own pointing direction (Z) at rest — so it should swing the end effector sideways (large |dy|),
    not spin it in place. This is exactly the failure mode ruled out during URDF authoring (an
    earlier "arms forward at rest" convention would have made shoulder_roll's axis coincide with
    the arm's own pointing direction, making it a no-op) — this check catches a regression of that."""
    model, data = load_model()
    mujoco.mj_resetData(model, data)
    mujoco.mj_forward(model, data)
    ee_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "left_ee_mount_link")
    pos_rest = data.xpos[ee_id].copy()

    roll_qposadr = model.joint("left_shoulder_roll_joint").qposadr[0]
    mujoco.mj_resetData(model, data)
    data.qpos[roll_qposadr] = np.deg2rad(90)
    mujoco.mj_forward(model, data)
    pos_rolled = data.xpos[ee_id].copy()

    delta = pos_rolled - pos_rest
    print(f"fk_sanity_check: left EE pos rest={pos_rest}, rolled90deg={pos_rolled}, delta={delta}")
    assert abs(delta[1]) > 0.1, (
        f"shoulder_roll should swing the EE sideways (|dy| > 0.1 m), got dy={delta[1]:.4f} — "
        "possible axis/sign regression, see URDF comments on the rest-pose convention"
    )
    print("fk_sanity_check: OK (shoulder_roll swings the arm sideways as intended)")


if __name__ == "__main__":
    zero_command_hold()
    step_response_settle()
    determinism()
    fk_sanity_check()
    print("rollout_smoke_test.py: ALL CHECKS PASSED")
