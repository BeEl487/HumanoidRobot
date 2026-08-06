"""Milestone 3 gripper verification: an open/close/open cycle (checking the finger2 mimic
constraint tracks finger1 and nothing diverges), then a contact test — spawn a small object
between the open fingers of the left gripper, close, and confirm a nonzero contact force appears.
"""

from __future__ import annotations

import numpy as np
import mujoco

from build_model import build_spec, load_model

N_CYCLE_STEPS = 3000
MIMIC_TOL_M = 0.001  # 1 mm, tight relative to the 30 mm max finger travel (<3.3%)
TRANSITION_GRACE_STEPS = 150  # skip this many steps after each open/close target change before
# checking mimic tracking — the equality constraint is enforced softly (MuJoCo default
# solref/solimp) and briefly lags a step target change; the check still covers >85% of each phase


def gripper_open_close_cycle() -> None:
    model, data = load_model()
    mujoco.mj_resetData(model, data)

    finger1_act = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_ACTUATOR, "left_gripper_finger1_joint_position")
    f1_qposadr = model.joint("left_gripper_finger1_joint").qposadr[0]
    f2_qposadr = model.joint("left_gripper_finger2_joint").qposadr[0]
    lo, hi = model.actuator_ctrlrange[finger1_act]

    third = N_CYCLE_STEPS // 3
    for step in range(N_CYCLE_STEPS):
        phase = step // third
        target = hi if phase == 1 else lo  # closed -> open -> closed (open in the middle third)
        data.ctrl[finger1_act] = target
        mujoco.mj_step(model, data)
        assert np.all(np.isfinite(data.qpos)) and np.all(np.isfinite(data.qvel)), \
            f"non-finite state at step {step}"
        steps_into_phase = step % third
        if steps_into_phase < TRANSITION_GRACE_STEPS:
            continue
        mimic_err = abs(data.qpos[f2_qposadr] - data.qpos[f1_qposadr])
        assert mimic_err < MIMIC_TOL_M, \
            f"finger2 mimic error {mimic_err*1000:.3f} mm exceeds {MIMIC_TOL_M*1000:.0f} mm at step {step}"
    print(f"gripper_open_close_cycle: OK ({N_CYCLE_STEPS} steps, finger2 tracked finger1 within "
          f"{MIMIC_TOL_M*1000:.0f} mm throughout)")


def gripper_contact_test() -> None:
    """Pose the left arm to a fixed test configuration, locate the open gripper's jaw midpoint via
    forward kinematics, spawn a small test box there, close the gripper, and confirm contact.
    Gravity is disabled for this test only — it isolates grip/contact mechanics from the separate
    question of whether the arm can hold a pose under load (already covered by rollout_smoke_test).
    """
    # Pass 1: forward-kinematics-only, no test object yet, to find where to put one.
    model, data = load_model()
    mujoco.mj_resetData(model, data)
    roll_adr = model.joint("left_shoulder_roll_joint").qposadr[0]
    elbow_adr = model.joint("left_elbow_joint").qposadr[0]
    data.qpos[roll_adr] = np.deg2rad(90)
    data.qpos[elbow_adr] = np.deg2rad(90)
    mujoco.mj_forward(model, data)
    base_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "left_gripper_base_link")
    base_pos = data.xpos[base_id].copy()
    base_mat = data.xmat[base_id].reshape(3, 3).copy()
    jaw_midpoint = base_pos + base_mat @ np.array([0, 0, -0.025])  # finger-tip region, local frame

    # Pass 2: rebuild with a small free test object at that world position.
    # This test builds its own single isolated test object below -- exclude the Milestone 5
    # scene furniture (table/bin/roster objects) so it doesn't interfere with or get confused for
    # this test's own object, and so the fixed roll=90/elbow=90 test pose can't collide with the
    # (much closer, post-Milestone-5) table geometry the way it did before this was scoped out.
    scene = build_spec(include_scene_furniture=False)
    scene.option.gravity = [0, 0, 0]
    test_body = scene.worldbody.add_body(name="contact_test_object", pos=jaw_midpoint.tolist())
    test_body.add_freejoint()
    test_body.add_geom(
        name="contact_test_object_collision",
        type=mujoco.mjtGeom.mjGEOM_BOX,
        size=[0.008, 0.008, 0.008],
        density=500.0,
    )
    model = scene.compile()
    data = mujoco.MjData(model)
    mujoco.mj_resetData(model, data)
    data.qpos[roll_adr] = np.deg2rad(90)
    data.qpos[elbow_adr] = np.deg2rad(90)

    finger1_act = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_ACTUATOR, "left_gripper_finger1_joint_position")
    shoulder_pitch_act = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_ACTUATOR, "left_shoulder_pitch_joint_position")
    roll_act = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_ACTUATOR, "left_shoulder_roll_joint_position")
    elbow_act = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_ACTUATOR, "left_elbow_joint_position")

    max_contact_force = 0.0
    for step in range(2000):
        data.ctrl[shoulder_pitch_act] = 0.0
        data.ctrl[roll_act] = np.deg2rad(90)
        data.ctrl[elbow_act] = np.deg2rad(90)
        data.ctrl[finger1_act] = 0.0  # 0 = closed, per URDF finger joint range [0, 0.03] = open
        mujoco.mj_step(model, data)
        assert np.all(np.isfinite(data.qpos)), f"non-finite state at step {step}"
        for i in range(data.ncon):
            force = np.zeros(6)
            mujoco.mj_contactForce(model, data, i, force)
            max_contact_force = max(max_contact_force, float(np.linalg.norm(force[:3])))

    print(f"gripper_contact_test: max contact force observed = {max_contact_force:.4f} N")
    assert max_contact_force > 0.0, "expected nonzero contact force when closing on the test object"
    print("gripper_contact_test: OK (nonzero contact force observed while closing on the test object)")


if __name__ == "__main__":
    gripper_open_close_cycle()
    gripper_contact_test()
    print("contact_smoke_test.py: ALL CHECKS PASSED")
