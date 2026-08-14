from __future__ import annotations

import csv
import pathlib
from typing import Iterable


class TaskMetricsLogger:
    """Task-specific CSV logging for camera pick-place training runs."""

    DEFAULT_COLUMNS = [
        "task", "run_name", "global_step", "episode_reward", "episode_length",
        "success_rate", "avg_reward_100", "policy_loss", "value_loss", "entropy",
        "learning_rate", "fps", "eta_seconds", "timestamp",
    ]

    def __init__(self, csv_path: pathlib.Path, task_name: str, run_name: str, columns: Iterable[str] | None = None):
        self.csv_path = csv_path
        self.task_name = task_name
        self.run_name = run_name
        self.columns = ["task", "run_name"] + list(columns or self.DEFAULT_COLUMNS[2:])
        if not self.csv_path.exists():
            self.csv_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.csv_path, "w", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow(self.columns)

    def log_row(self, row: dict) -> None:
        row_data = {**row, "task": self.task_name, "run_name": self.run_name}
        with open(self.csv_path, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([row_data.get(col, "") for col in self.columns])
