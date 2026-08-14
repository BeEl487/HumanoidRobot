"""Small RGB-D + proprioception encoder for Stable-Baselines3 PPO."""

from __future__ import annotations

import torch
from gymnasium import spaces
from stable_baselines3.common.torch_layers import BaseFeaturesExtractor
from torch import nn


class RGBDProprioExtractor(BaseFeaturesExtractor):
    """Fuse 4-channel head-camera images with only deployable robot state."""

    def __init__(self, observation_space: spaces.Dict, features_dim: int = 128):
        super().__init__(observation_space, features_dim)
        self._proprio_keys = tuple(key for key in observation_space.spaces if key not in {"rgb", "depth"})
        self._proprio_dim = sum(
            int(torch.tensor(observation_space.spaces[key].shape).prod()) for key in self._proprio_keys
        )
        self.visual_encoder = nn.Sequential(
            nn.Conv2d(4, 16, kernel_size=5, stride=2, padding=2), nn.ReLU(),
            nn.Conv2d(16, 32, kernel_size=3, stride=2, padding=1), nn.ReLU(),
            nn.Conv2d(32, 64, kernel_size=3, stride=2, padding=1), nn.ReLU(),
            nn.AdaptiveAvgPool2d((1, 1)), nn.Flatten(), nn.Linear(64, 96), nn.ReLU(),
        )
        self.fusion = nn.Sequential(nn.Linear(96 + self._proprio_dim, features_dim), nn.ReLU())

    def forward(self, observations: dict[str, torch.Tensor]) -> torch.Tensor:
        rgb = observations["rgb"].float() / 255.0
        depth = observations["depth"].float() / 2.0
        visual_features = self.visual_encoder(torch.cat((rgb, depth), dim=1))
        proprioception = [observations[key].float().flatten(start_dim=1) for key in self._proprio_keys]
        return self.fusion(torch.cat((visual_features, *proprioception), dim=1))
