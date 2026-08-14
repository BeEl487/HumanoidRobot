"""Train the lightweight RGB camera-to-bin-sorter model from a CSV manifest.

Each manifest row has ``image_path,x,y,z,bin_label``. XYZ is the calibrated
robot-base grasp/end-effector position in metres; ``bin_label`` is a stable
name such as ``recycling`` or ``parts``. Train with a few hundred manually
labelled images before considering a larger detector/segmenter.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from torch import nn
from torch.utils.data import DataLoader, Dataset

from vision_grasp_model import CameraBinSorter


@dataclass(frozen=True)
class SortLabel:
    image_path: Path
    grasp_xyz: tuple[float, float, float]
    bin_index: int


class CameraSortingDataset(Dataset[tuple[torch.Tensor, torch.Tensor, torch.Tensor]]):
    def __init__(self, manifest_path: Path, image_size: int = 64):
        with manifest_path.open(newline="", encoding="utf-8") as manifest_file:
            rows = list(csv.DictReader(manifest_file))
        required = {"image_path", "x", "y", "z", "bin_label"}
        if not rows or not required.issubset(rows[0]):
            raise ValueError(f"manifest must contain columns: {sorted(required)}")

        self.image_size = image_size
        labels = sorted({row["bin_label"] for row in rows})
        self.bin_to_index = {label: index for index, label in enumerate(labels)}
        self.index_to_bin = labels
        self.samples = [
            SortLabel(
                image_path=(manifest_path.parent / row["image_path"]).resolve(),
                grasp_xyz=(float(row["x"]), float(row["y"]), float(row["z"])),
                bin_index=self.bin_to_index[row["bin_label"]],
            )
            for row in rows
        ]

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, index: int) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        sample = self.samples[index]
        with Image.open(sample.image_path) as image:
            image_array = np.asarray(
                image.convert("RGB").resize((self.image_size, self.image_size)), dtype=np.float32
            ).copy()
            image_tensor = torch.from_numpy(image_array).permute(2, 0, 1) / 255.0
        return (
            image_tensor,
            torch.tensor(sample.grasp_xyz, dtype=torch.float32),
            torch.tensor(sample.bin_index, dtype=torch.long),
        )


def train(manifest_path: Path, output_path: Path, epochs: int = 30, batch_size: int = 16) -> None:
    dataset = CameraSortingDataset(manifest_path)
    if len(dataset.bin_to_index) < 2:
        raise ValueError("sorting requires at least two destination bins")
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)
    model = CameraBinSorter(num_bins=len(dataset.bin_to_index))
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)

    model.train()
    for _ in range(epochs):
        for images, grasp_xyz, bin_index in loader:
            predicted_xyz, bin_logits = model(images)
            loss = nn.functional.mse_loss(predicted_xyz, grasp_xyz)
            loss = loss + nn.functional.cross_entropy(bin_logits, bin_index)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {"model_state_dict": model.state_dict(), "bin_to_index": dataset.bin_to_index}, output_path
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", type=Path, default=Path("runs/camera_bin_sorter.pt"))
    parser.add_argument("--epochs", type=int, default=30)
    args = parser.parse_args()
    train(args.manifest, args.output, epochs=args.epochs)
