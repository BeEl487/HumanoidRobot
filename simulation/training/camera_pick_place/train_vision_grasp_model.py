from __future__ import annotations

import pathlib
import sys

import torch
from torch import nn

SIM_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(SIM_ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from vision_grasp_model import SimpleEndEffectorRegressor  # noqa: E402

OUT_PATH = pathlib.Path(__file__).resolve().parent / "runs" / "vision_grasp_model.pt"


def train_demo_model(total_steps: int = 100, batch_size: int = 16, lr: float = 1e-3) -> torch.nn.Module:
    model = SimpleEndEffectorRegressor(image_size=(64, 64))
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)

    for _ in range(total_steps):
        images = torch.rand(batch_size, 3, 64, 64)
        targets = torch.rand(batch_size, 3)
        predictions = model(images)
        loss = nn.functional.mse_loss(predictions, targets)
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), OUT_PATH)
    print(f"saved {OUT_PATH}")
    return model


if __name__ == "__main__":
    train_demo_model()
