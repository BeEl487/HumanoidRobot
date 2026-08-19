"""Hip gimbal IK: desired torso orientation -> (pitch, roll) -> motor crank angles.

Geometry source: Onshape "Arm" document (UpperBodyStructure / Gimbal /
SideMotorAssm / TorseLinkageHeim), pulled via the assembly API, ~+/-1mm.
Base-pivot coordinates carry more error (chained transforms) -- re-check
in Onshape's measure tool if sub-mm accuracy is ever needed.

Frames:
  Base frame:   origin at the pitch-axis point. x = roll-axis direction
                at zero pitch, y = pitch axis, z = common perpendicular
                toward the torso.
  Torso frame:  origin at the roll-axis point. x = roll-axis direction,
                fixed to the torso (carried along by pitch).

Two generalized coords: pitch phi (about base y), roll theta (about the
roll axis, itself carried by phi). Torso orientation relative to base:
    R(phi, theta) = Ry(phi) @ Rx(theta)
Roll-axis pivot, seen from the base:
    p_roll(phi) = Ry(phi) @ [0, 0, d]
A torso-fixed point P_T maps to the base frame as:
    P_world(phi, theta) = Ry(phi) @ ([0, 0, d] + Rx(theta) @ P_T)
"""

import numpy as np

# ---- Measured geometry (mm) ----
D_ROLL_OFFSET = 440.0      # distance from pitch axis to roll axis, along carried z
LINK_LENGTH = 120.0        # heim-to-heim length, both sides
CRANK_RADIUS = 45.1        # both motors

# Motor pivots, torso-local frame (mirror pair)
MOTOR_PIVOTS_TORSO = {
    "left": np.array([75.7, -19.2, -143.2]),
    "right": np.array([-75.9, -19.2, -143.2]),
}

# Base pivots, base frame (fixed)
BASE_PIVOTS = {
    "left": np.array([46.0, -66.0, 202.0]),
    "right": np.array([-57.0, -71.0, 211.0]),
}

# Crank-plane unit vectors (perpendicular to the roll axis), torso-local.
# PLACEHOLDER: not yet pulled numerically from CAD -- using the local Y/Z
# basis at the motor mount per the CAD description. Swap these for the
# exact normalized u_hat/v_hat once pulled.
CRANK_PLANE_U = {"left": np.array([0.0, 1.0, 0.0]), "right": np.array([0.0, 1.0, 0.0])}
CRANK_PLANE_V = {"left": np.array([0.0, 0.0, 1.0]), "right": np.array([0.0, 0.0, 1.0])}


def Ry(angle):
    c, s = np.cos(angle), np.sin(angle)
    return np.array([
        [c, 0.0, s],
        [0.0, 1.0, 0.0],
        [-s, 0.0, c],
    ])


def Rx(angle):
    c, s = np.cos(angle), np.sin(angle)
    return np.array([
        [1.0, 0.0, 0.0],
        [0.0, c, -s],
        [0.0, s, c],
    ])


def torso_orientation(phi, theta):
    """Base->torso rotation matrix for the given (pitch, roll)."""
    return Ry(phi) @ Rx(theta)


def roll_axis_point_world(phi):
    return Ry(phi) @ np.array([0.0, 0.0, D_ROLL_OFFSET])


def point_torso_to_world(point_torso, phi, theta):
    return Ry(phi) @ (np.array([0.0, 0.0, D_ROLL_OFFSET]) + Rx(theta) @ point_torso)


def stage1_orientation_to_angles(R_des):
    """Closed-form solve of Ry(phi) @ Rx(theta) = R_des.

    No singularity: this is a 2-DOF decomposition, not a 3-angle Euler set.
    """
    theta = np.arctan2(-R_des[1, 2], R_des[1, 1])
    phi = np.arctan2(R_des[0, 2], R_des[2, 2])
    return phi, theta


def stage2_motor_angle(side, phi, theta, prev_alpha=None):
    """Given (phi, theta), solve the crank angle for one side's motor.

    Returns None if the pose is unreachable (|C| > sqrt(A^2+B^2)).
    When prev_alpha is given, picks whichever of the two elbow-up/down
    roots is closest to prev_alpha (continuity); otherwise returns both.
    """
    M_local = MOTOR_PIVOTS_TORSO[side]
    B = BASE_PIVOTS[side]
    u_local = CRANK_PLANE_U[side]
    v_local = CRANK_PLANE_V[side]

    R = Ry(phi) @ Rx(theta)
    M_world = point_torso_to_world(M_local, phi, theta)
    U = R @ u_local
    V = R @ v_local

    d_vec = M_world - B
    A = 2.0 * CRANK_RADIUS * np.dot(d_vec, U)
    Bc = 2.0 * CRANK_RADIUS * np.dot(d_vec, V)
    C = LINK_LENGTH**2 - CRANK_RADIUS**2 - np.dot(d_vec, d_vec)

    denom = np.hypot(A, Bc)
    if denom < 1e-12 or abs(C / denom) > 1.0:
        return None

    base_angle = np.arctan2(Bc, A)
    delta = np.arccos(np.clip(C / denom, -1.0, 1.0))
    roots = (base_angle + delta, base_angle - delta)

    if prev_alpha is None:
        return roots

    def ang_diff(a, b):
        return abs(np.arctan2(np.sin(a - b), np.cos(a - b)))

    return min(roots, key=lambda r: ang_diff(r, prev_alpha))


def crank_tip_world(side, phi, theta, alpha):
    """World position of the link's motor-side ball joint, for FK checks."""
    M_world = point_torso_to_world(MOTOR_PIVOTS_TORSO[side], phi, theta)
    R = Ry(phi) @ Rx(theta)
    U = R @ CRANK_PLANE_U[side]
    V = R @ CRANK_PLANE_V[side]
    return M_world + CRANK_RADIUS * (np.cos(alpha) * U + np.sin(alpha) * V)


def _self_test():
    rng = np.random.default_rng(0)
    max_stage1_err = 0.0
    max_link_err = 0.0
    unreachable = 0

    for _ in range(500):
        phi = rng.uniform(-0.3, 0.3)
        theta = rng.uniform(-0.3, 0.3)

        # Stage 1 round-trip: build R_des from (phi,theta), decompose, compare.
        R_des = torso_orientation(phi, theta)
        phi_hat, theta_hat = stage1_orientation_to_angles(R_des)
        max_stage1_err = max(max_stage1_err, abs(phi - phi_hat), abs(theta - theta_hat))

        # Stage 2: solve alpha, then verify the link length constraint holds.
        for side in ("left", "right"):
            roots = stage2_motor_angle(side, phi, theta)
            if roots is None:
                unreachable += 1
                continue
            for alpha in roots:
                tip = crank_tip_world(side, phi, theta, alpha)
                err = abs(np.linalg.norm(tip - BASE_PIVOTS[side]) - LINK_LENGTH)
                max_link_err = max(max_link_err, err)

    print(f"stage1 max angle error:   {max_stage1_err:.3e} rad")
    print(f"stage2 max link-length err: {max_link_err:.3e} mm")
    print(f"unreachable samples:      {unreachable}/1000")

    # Continuity selection sanity check: sweep theta, confirm no jump > ~90deg.
    phi = 0.0
    prev = {"left": None, "right": None}
    max_jump = {"left": 0.0, "right": 0.0}
    for theta in np.linspace(-0.3, 0.3, 200):
        for side in ("left", "right"):
            result = stage2_motor_angle(side, phi, theta, prev_alpha=prev[side])
            if result is None:
                continue
            a = result[1] if prev[side] is None else result
            if prev[side] is not None:
                jump = abs(np.arctan2(np.sin(a - prev[side]), np.cos(a - prev[side])))
                max_jump[side] = max(max_jump[side], jump)
            prev[side] = a
    print(f"max per-step angle jump under continuity selection: {max_jump}")


if __name__ == "__main__":
    _self_test()
