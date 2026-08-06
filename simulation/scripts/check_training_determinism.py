"""Milestone 8 determinism gate: train the state profile twice with an identical seed and
timestep budget (single env, no subprocess parallelism) and confirm the final policy weights
match -- the final gate on the whole simulation pipeline (URDF -> MuJoCo -> Gym env -> SB3).
"""

from __future__ import annotations

import pathlib
import sys

import torch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "training"))
from train_ppo import train  # noqa: E402

N_TIMESTEPS = 2048  # small budget: this checks bit-for-bit reproducibility, not training quality


def main() -> None:
    path1 = train("state", total_timesteps=N_TIMESTEPS, checkpoint_name="determinism_check_1")
    path2 = train("state", total_timesteps=N_TIMESTEPS, checkpoint_name="determinism_check_2")

    from stable_baselines3 import PPO
    model1 = PPO.load(str(path1))
    model2 = PPO.load(str(path2))

    sd1 = model1.policy.state_dict()
    sd2 = model2.policy.state_dict()
    assert sd1.keys() == sd2.keys(), "policy state_dict keys differ between runs"
    for key in sd1:
        assert torch.equal(sd1[key], sd2[key]), f"policy weight {key!r} differs between identical-seed runs"

    print(f"check_training_determinism: OK ({N_TIMESTEPS} timesteps, identical final policy weights "
          f"across {len(sd1)} parameter tensors)")


if __name__ == "__main__":
    main()
