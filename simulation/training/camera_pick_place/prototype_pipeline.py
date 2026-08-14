from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence, Tuple

import numpy as np


@dataclass
class GraspCandidate:
    xyz_cam: np.ndarray
    surface_normal: np.ndarray
    approach_vector: np.ndarray
    confidence: float
    depth_range_ok: bool
    visible: bool
    reason: str


def estimate_grasp_candidate(
    rgb: np.ndarray,
    depth: np.ndarray,
    object_mask: np.ndarray,
    depth_min_range_m: float,
    intrinsics: Tuple[float, float, float, float],
) -> GraspCandidate:
    """Create a simple grasp candidate from a synthetic RGB-D frame.

    This is intentionally conservative and uses only a simple centroid + normal proxy.
    It also flags whether the object is too close for reliable depth use with a head-mounted
    camera such as the D435i.
    """

    if rgb.ndim != 3:
        raise ValueError("rgb must be a 3-channel image")
    if depth.shape != object_mask.shape:
        raise ValueError("depth and object_mask must have the same shape")

    ys, xs = np.where(object_mask)
    if len(xs) == 0:
        raise ValueError("object_mask must contain at least one foreground pixel")

    fx, fy, cx, cy = intrinsics
    z = np.median(depth[ys, xs])
    if np.isnan(z) or np.isinf(z):
        raise ValueError("depth values must be finite")

    depth_range_ok = z >= depth_min_range_m

    u = np.median(xs)
    v = np.median(ys)
    x = (u - cx) * z / fx
    y = (v - cy) * z / fy
    xyz_cam = np.array([x, y, z], dtype=float)

    # Simple surface-normal proxy: assume a top-facing normal from the mask centroid.
    surface_normal = np.array([0.0, 0.0, 1.0], dtype=float)
    approach_vector = np.array([0.0, -1.0, 0.0], dtype=float)

    confidence = 0.8 if depth_range_ok else 0.55
    if not depth_range_ok:
        reason = "object is inside minimum depth range"
    else:
        reason = "simple centroid-based grasp"

    return GraspCandidate(
        xyz_cam=xyz_cam,
        surface_normal=surface_normal,
        approach_vector=approach_vector,
        confidence=confidence,
        depth_range_ok=depth_range_ok,
        visible=True,
        reason=reason,
    )


def estimate_hand_eye_transform(
    camera_points: Sequence[Sequence[float]],
    robot_points: Sequence[Sequence[float]],
) -> np.ndarray:
    """Estimate a 4x4 camera-to-robot transform from paired 3D points.

    This is a simple least-squares rigid-body fit using the Kabsch algorithm.
    """

    camera_arr = np.asarray(camera_points, dtype=float)
    robot_arr = np.asarray(robot_points, dtype=float)
    if camera_arr.ndim != 2 or robot_arr.ndim != 2 or camera_arr.shape != robot_arr.shape:
        raise ValueError("camera_points and robot_points must be matching Nx3 arrays")
    if camera_arr.shape[1] != 3:
        raise ValueError("camera_points and robot_points must contain 3D points")
    if len(camera_arr) < 2:
        raise ValueError("at least two point pairs are required")

    camera_centroid = np.mean(camera_arr, axis=0)
    robot_centroid = np.mean(robot_arr, axis=0)
    camera_centered = camera_arr - camera_centroid
    robot_centered = robot_arr - robot_centroid

    covariance = camera_centered.T @ robot_centered
    u, _, vt = np.linalg.svd(covariance)
    rotation = vt.T @ u.T
    if np.linalg.det(rotation) < 0:
        vt[-1, :] *= -1.0
        rotation = vt.T @ u.T

    translation = robot_centroid - rotation @ camera_centroid
    transform = np.eye(4, dtype=float)
    transform[:3, :3] = rotation
    transform[:3, 3] = translation
    return transform


def apply_hand_eye_transform(candidate: GraspCandidate, camera_to_robot: np.ndarray) -> np.ndarray:
    """Apply a camera-to-robot transform to the grasp point."""

    if camera_to_robot.shape != (4, 4):
        raise ValueError("camera_to_robot must be a 4x4 homogeneous transform")

    xyz_h = np.array([candidate.xyz_cam[0], candidate.xyz_cam[1], candidate.xyz_cam[2], 1.0])
    transformed = camera_to_robot @ xyz_h
    return transformed[:3]


def plan_grasp_motion(
    candidate: GraspCandidate,
    camera_to_robot: np.ndarray,
    approach_offset_m: float = 0.05,
    retreat_offset_m: float = 0.10,
) -> dict[str, np.ndarray]:
    """Create a simple pre-grasp, grasp, and post-grasp pose plan in robot coordinates."""

    grasp_pose_robot = apply_hand_eye_transform(candidate, camera_to_robot)
    approach_vector = candidate.approach_vector / np.linalg.norm(candidate.approach_vector)
    pre_grasp_pose_robot = grasp_pose_robot + approach_offset_m * approach_vector
    post_grasp_pose_robot = grasp_pose_robot + retreat_offset_m * approach_vector

    return {
        "grasp_pose_robot": grasp_pose_robot,
        "pre_grasp_pose_robot": pre_grasp_pose_robot,
        "post_grasp_pose_robot": post_grasp_pose_robot,
    }


def run_scripted_grasp_loop(
    rgb: np.ndarray,
    depth: np.ndarray,
    object_mask: np.ndarray,
    intrinsics: Tuple[float, float, float, float],
    camera_to_robot: np.ndarray,
    depth_min_range_m: float = 0.28,
    iq_samples: Sequence[float] | None = None,
    grasp_feedback_threshold_ma: float = 0.5,
) -> dict[str, object]:
    """Run the simplified grasp pipeline from perception to a single grasp-state decision."""

    candidate = estimate_grasp_candidate(
        rgb=rgb,
        depth=depth,
        object_mask=object_mask,
        depth_min_range_m=depth_min_range_m,
        intrinsics=intrinsics,
    )

    if not candidate.visible:
        return {"status": "rejected", "candidate": candidate, "grasp_succeeded": False}
    if not candidate.depth_range_ok:
        return {
            "status": "rejected_depth_range",
            "candidate": candidate,
            "grasp_succeeded": False,
        }

    plan = plan_grasp_motion(candidate, camera_to_robot)
    grasp_feedback = evaluate_grasp_feedback(iq_samples or [], threshold_ma=grasp_feedback_threshold_ma)
    return {
        "status": "ready",
        "candidate": candidate,
        "grasp_pose_robot": plan["grasp_pose_robot"],
        "pre_grasp_pose_robot": plan["pre_grasp_pose_robot"],
        "post_grasp_pose_robot": plan["post_grasp_pose_robot"],
        "grasp_succeeded": grasp_feedback,
    }


def evaluate_grasp_feedback(iq_samples: np.ndarray | list[float], threshold_ma: float = 0.5) -> bool:
    """Use current telemetry as a grasp-success proxy.

    The plan will use this as a simple contact/grasp indicator: if the motor current rises above
    a threshold, that suggests the gripper or arm is applying force and the object is being held.
    """

    arr = np.asarray(iq_samples, dtype=float)
    if arr.size == 0:
        return False
    return float(np.max(arr)) >= threshold_ma
