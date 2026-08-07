"""SB3 callback that turns a training run into a self-updating progress dashboard: every
`interval_steps`, saves a checkpoint, runs a deterministic evaluation, renders a video of that
checkpoint attempting the task, and appends the result to a JSON manifest a static HTML page polls.

Directory layout (all under `run_dir`, one per training run -- see `--run-name` in train_ppo.py):
    run_dir/
      checkpoints/ckpt_000200000.zip, ckpt_000400000.zip, ...   -- kept forever, never overwritten
      videos/ckpt_000200000_ext.mp4, ckpt_000200000_pov.mp4     -- ditto
      manifest.json                                              -- the dashboard's only data source
      dashboard.html                                             -- static page, polls manifest.json

Why a local static dashboard rather than something published elsewhere: this needs to update
*during* training, unattended, from inside the training process itself -- a plain file the process
can append to and a page that polls it is the simplest thing that has no external dependency and
can't silently stop working. Serve the run directory with any static file server, e.g.:
    python -m http.server 8000 --directory training/runs/<run_name>
then open http://localhost:8000/dashboard.html -- see serve_dashboard.py for a thin wrapper.

Modularity: metrics come entirely from evaluate.py's `evaluate()` return dict, so adding a new
metric there (or a new metric key any future evaluate() adds) shows up in the manifest and on the
dashboard automatically -- dashboard.html renders whatever keys are present under "metrics" rather
than a hardcoded list, deliberately, so this doesn't need to be touched to add one.
"""

from __future__ import annotations

import json
import pathlib
import shutil
import sys
import tempfile
from datetime import datetime, timezone

from stable_baselines3.common.callbacks import BaseCallback

SIM_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SIM_ROOT))
sys.path.insert(0, str(SIM_ROOT / "scripts"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))  # training/ itself, for evaluate.py

from evaluate import evaluate  # noqa: E402
from render_policy_rollout import render_rollout  # noqa: E402

DASHBOARD_TEMPLATE = pathlib.Path(__file__).resolve().parent / "dashboard_template.html"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _write_json_atomic(path: pathlib.Path, data: dict) -> None:
    """Write via a temp file + rename so a dashboard polling mid-write never sees a truncated
    or partially-written manifest (rename is atomic on the same filesystem, unlike a direct write)."""
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=".manifest_", suffix=".tmp")
    try:
        with open(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        pathlib.Path(tmp_name).replace(path)
    except BaseException:
        pathlib.Path(tmp_name).unlink(missing_ok=True)
        raise


class ProgressArtifactCallback(BaseCallback):
    """Every `interval_steps` timesteps: checkpoint, evaluate, render a video, update the
    dashboard manifest. Runs synchronously (training pauses for the ~5-15s this takes) -- simpler
    than async and negligible next to a multi-hundred-thousand-step run at this interval."""

    def __init__(
        self,
        run_dir: pathlib.Path,
        profile: str,
        total_timesteps: int,
        interval_steps: int = 200_000,
        eval_episodes: int = 10,
        video_seed: int = 0,
        run_name: str | None = None,
        verbose: int = 1,
    ):
        super().__init__(verbose)
        self.run_dir = pathlib.Path(run_dir)
        self.profile = profile
        self.total_timesteps = total_timesteps
        self.interval_steps = interval_steps
        self.eval_episodes = eval_episodes
        self.video_seed = video_seed
        self.run_name = run_name or self.run_dir.name
        self._next_trigger = interval_steps

    def _init_callback(self) -> None:
        (self.run_dir / "checkpoints").mkdir(parents=True, exist_ok=True)
        (self.run_dir / "videos").mkdir(parents=True, exist_ok=True)
        shutil.copyfile(DASHBOARD_TEMPLATE, self.run_dir / "dashboard.html")

        manifest_path = self.run_dir / "manifest.json"
        if not manifest_path.exists():
            _write_json_atomic(manifest_path, {
                "run_name": self.run_name,
                "profile": self.profile,
                "total_timesteps": self.total_timesteps,
                "created": _now_iso(),
                "updated": _now_iso(),
                "checkpoints": [],
            })

    def _on_step(self) -> bool:
        if self.num_timesteps < self._next_trigger:
            return True
        self._next_trigger += self.interval_steps
        self._generate_artifact(self.num_timesteps)
        return True

    def _on_training_end(self) -> None:
        # Always capture the final model too, even if total_timesteps isn't an exact multiple of
        # interval_steps (e.g. 500k steps with a 200k interval stops at 400k otherwise), and even
        # if the last on_step trigger happened to land exactly on the final step already.
        if not self._last_logged_step_is(self.num_timesteps):
            self._generate_artifact(self.num_timesteps, final=True)

    def _last_logged_step_is(self, step: int) -> bool:
        manifest_path = self.run_dir / "manifest.json"
        if not manifest_path.exists():
            return False
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        return bool(data["checkpoints"]) and data["checkpoints"][-1]["step"] == step

    def _generate_artifact(self, step: int, final: bool = False) -> None:
        tag = f"ckpt_{step:09d}"
        ckpt_path = self.run_dir / "checkpoints" / f"{tag}.zip"
        video_ext = self.run_dir / "videos" / f"{tag}_ext.mp4"
        video_pov = self.run_dir / "videos" / f"{tag}_pov.mp4"

        if self.verbose:
            label = "final" if final else "checkpoint"
            print(f"[progress_artifacts] {label} at step {step}: saving, evaluating, rendering...")

        self.model.save(str(ckpt_path))
        metrics = evaluate(str(ckpt_path), self.profile, self.eval_episodes)
        render_rollout(str(ckpt_path), self.profile, video_ext, seed=self.video_seed, pov_out_path=video_pov)

        manifest_path = self.run_dir / "manifest.json"
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        data["checkpoints"] = [c for c in data["checkpoints"] if c["step"] != step]  # replace, not duplicate
        data["checkpoints"].append({
            "step": step,
            "final": final,
            "timestamp": _now_iso(),
            "checkpoint_path": f"checkpoints/{tag}.zip",
            "video_ext": f"videos/{tag}_ext.mp4",
            "video_pov": f"videos/{tag}_pov.mp4",
            "metrics": metrics,
        })
        data["checkpoints"].sort(key=lambda c: c["step"])
        data["updated"] = _now_iso()
        _write_json_atomic(manifest_path, data)

        if self.verbose:
            print(f"[progress_artifacts] manifest updated: {manifest_path}")
