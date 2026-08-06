"""Fail loudly if the compiled model's joint set ever drifts from config/joint_names.yaml —
that file is the index<->joint contract every action/obs vector in sim_env/* relies on. Run this
after any URDF edit that could reorder, rename, add, or remove joints.

Every arm joint (joint_order) and every gripper drive joint (gripper_joint_order) must have a
matching "<name>_position" actuator. finger2 joints are the one documented exception — they are
mimic joints (mirrored via an equality constraint, not independently actuated, see
build_model.py's _add_gripper_mimic_constraint) — so they're checked separately, for having NO
actuator and exactly one equality constraint each, instead.
"""

from __future__ import annotations

import mujoco

from build_model import _load_gripper_joint_order, _load_joint_order, load_model


def _assert_has_actuator(model: mujoco.MjModel, joint_name: str) -> None:
    actuator_name = f"{joint_name}_position"
    if mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_ACTUATOR, actuator_name) == -1:
        raise AssertionError(f"Joint {joint_name!r} has no matching actuator {actuator_name!r}")


if __name__ == "__main__":
    expected_arm = _load_joint_order()
    expected_gripper = _load_gripper_joint_order()
    model, _ = load_model()

    all_joint_names = [model.joint(i).name for i in range(model.njnt)]
    # Scene objects (Milestone 5) get their own free joints, unrelated to the robot's own joint
    # contract entirely -- not "driven" or "mimic" in the sense this check cares about.
    robot_joint_names = [n for n in all_joint_names if not n.startswith("object_")]
    mimic_joints = [n for n in robot_joint_names if n.endswith("_gripper_finger2_joint")]
    driven_joints = [n for n in robot_joint_names if n not in mimic_joints]

    # Set, not order: MuJoCo's internal joint enumeration follows the URDF tree structure
    # (arm and its gripper are siblings in the tree), not joint_names.yaml's logical grouping.
    # sim_env code indexes qpos/ctrl by NAME (via qposadr / actuator id lookup), never by raw
    # positional index into this list, so only set-equality is actually a correctness contract.
    expected_set = set(expected_arm) | set(expected_gripper)
    if set(driven_joints) != expected_set:
        raise AssertionError(
            "Driven-joint set mismatch between the compiled model and joint_names.yaml.\n"
            f"  model:  {sorted(driven_joints)}\n  config: {sorted(expected_set)}"
        )
    for name in driven_joints:
        _assert_has_actuator(model, name)

    for name in mimic_joints:
        if mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_ACTUATOR, f"{name}_position") != -1:
            raise AssertionError(f"Mimic joint {name!r} unexpectedly has its own actuator")
        side = name.split("_gripper_finger2_joint")[0]
        eq_name1 = f"{side}_gripper_finger2_joint"
        found = any(
            model.eq_obj1id[i] == mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, eq_name1)
            for i in range(model.neq)
        )
        if not found:
            raise AssertionError(f"Mimic joint {name!r} has no equality constraint")

    print(
        f"check_joint_consistency.py: OK — {len(driven_joints)} driven joints match "
        f"joint_names.yaml, {len(mimic_joints)} mimic joints correctly constrained"
    )
