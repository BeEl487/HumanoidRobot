"""RGB-D point-cloud primitives for perception diagnostics and scripted baselines."""

from __future__ import annotations

import numpy as np


def depth_to_point_cloud(
    depth_m: np.ndarray, intrinsics: tuple[float, float, float, float], mask: np.ndarray | None = None
) -> np.ndarray:
    """Project valid depth pixels into camera-frame XYZ points without simulator state."""
    if depth_m.ndim != 2:
        raise ValueError("depth_m must have shape [height, width]")
    if mask is None:
        mask = np.ones_like(depth_m, dtype=bool)
    if mask.shape != depth_m.shape:
        raise ValueError("mask and depth_m must have matching shapes")
    fy, fx = intrinsics[1], intrinsics[0]
    cx, cy = intrinsics[2], intrinsics[3]
    rows, cols = np.where(mask & np.isfinite(depth_m) & (depth_m > 0.0))
    z = depth_m[rows, cols]
    x = (cols - cx) * z / fx
    y = (rows - cy) * z / fy
    return np.column_stack((x, y, z)).astype(np.float32)


def robust_cluster_centroid(points: np.ndarray, z_score: float = 3.0) -> np.ndarray:
    """Return an outlier-filtered point-cloud centroid for a segmented object."""
    if points.ndim != 2 or points.shape[1] != 3 or len(points) == 0:
        raise ValueError("points must be a non-empty [N, 3] array")
    median = np.median(points, axis=0)
    distances = np.linalg.norm(points - median, axis=1)
    mad = np.median(np.abs(distances - np.median(distances)))
    if mad == 0.0:
        # A compact cluster frequently has several identical/near-identical depths. Keep
        # the closest median-distance group rather than allowing one distant pixel through.
        inliers = distances <= np.median(distances) + 1e-6
        return np.mean(points[inliers], axis=0)
    inliers = distances <= np.median(distances) + z_score * 1.4826 * mad
    return np.mean(points[inliers], axis=0)
