from __future__ import annotations

import pathlib
import sys

import torch
from torch import nn

SIM_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(SIM_ROOT))


class SimpleEndEffectorRegressor(nn.Module):
    """A lightweight image-to-end-effector-position regressor.

    The goal is not to replace a full segmentation pipeline, but to provide a simple trainable
    baseline that maps an RGB image to a 3D end-effector target (x, y, z) in robot/world space.
    This is intentionally small so it can be trained on a few hundred labeled images with a CPU
    or a small GPU.
    """

    def __init__(self, image_size: tuple[int, int] = (64, 64), latent_dim: int = 64):
        super().__init__()
        height, width = image_size
        self.backbone = nn.Sequential(
            nn.Conv2d(3, 16, kernel_size=3, stride=2, padding=1),
            nn.ReLU(),
            nn.Conv2d(16, 32, kernel_size=3, stride=2, padding=1),
            nn.ReLU(),
            nn.Conv2d(32, 64, kernel_size=3, stride=2, padding=1),
            nn.ReLU(),
        )
        conv_out = (height // 8) * (width // 8) * 64
        self.head = nn.Sequential(
            nn.Flatten(),
            nn.Linear(conv_out, latent_dim),
            nn.ReLU(),
            nn.Linear(latent_dim, 3),
        )

    def forward(self, images: torch.Tensor) -> torch.Tensor:
        if images.ndim != 4:
            raise ValueError("expected images with shape [batch, 3, H, W]")
        features = self.backbone(images)
        return self.head(features)


class CameraBinSorter(nn.Module):
    """Predict a grasp target and destination-bin class from one RGB frame.

    The model intentionally predicts only the variable part of a sorting task: the
    object's grasp point and its bin class.  A calibrated ``bin_poses`` map turns
    that class into the fixed placement end-effector position; it must not be
    learned from a small image dataset.
    """

    def __init__(self, num_bins: int, latent_dim: int = 64):
        super().__init__()
        if num_bins < 2:
            raise ValueError("num_bins must be at least 2")
        self.backbone = nn.Sequential(
            nn.Conv2d(3, 16, kernel_size=3, stride=2, padding=1),
            nn.ReLU(),
            nn.Conv2d(16, 32, kernel_size=3, stride=2, padding=1),
            nn.ReLU(),
            nn.Conv2d(32, 64, kernel_size=3, stride=2, padding=1),
            nn.ReLU(),
            nn.AdaptiveAvgPool2d((1, 1)),
            nn.Flatten(),
            nn.Linear(64, latent_dim),
            nn.ReLU(),
        )
        self.grasp_head = nn.Linear(latent_dim, 3)
        self.bin_head = nn.Linear(latent_dim, num_bins)

    def forward(self, images: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        """Return ``(grasp_xyz_robot, bin_logits)`` for NCHW RGB float tensors."""
        if images.ndim != 4 or images.shape[1] != 3:
            raise ValueError("expected images with shape [batch, 3, H, W]")
        features = self.backbone(images)
        return self.grasp_head(features), self.bin_head(features)


def make_sort_plan(
    grasp_xyz_robot: torch.Tensor,
    bin_logits: torch.Tensor,
    bin_poses_robot: torch.Tensor,
) -> dict[str, torch.Tensor]:
    """Turn model outputs into calibrated pick and place end-effector targets.

    ``bin_poses_robot`` is shaped ``[num_bins, 3]`` and is measured after
    hand-eye calibration. The returned positions are in the robot-base frame.
    """
    if grasp_xyz_robot.ndim != 2 or grasp_xyz_robot.shape[1] != 3:
        raise ValueError("grasp_xyz_robot must have shape [batch, 3]")
    if bin_poses_robot.ndim != 2 or bin_poses_robot.shape[1] != 3:
        raise ValueError("bin_poses_robot must have shape [num_bins, 3]")
    if bin_logits.shape[1] != bin_poses_robot.shape[0]:
        raise ValueError("bin logits and bin_poses_robot must have the same bin count")

    bin_index = bin_logits.argmax(dim=1)
    return {
        "pick_end_effector_xyz": grasp_xyz_robot,
        "bin_index": bin_index,
        "place_end_effector_xyz": bin_poses_robot[bin_index],
    }
