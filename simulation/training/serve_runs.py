"""Auto-discovering HTTP server for browsing every training run on this machine, across any task
type, whether or not anything is training right now. Serves `runs_browser.html` plus a
dynamically-computed `/index.json` and read-only access to each run's `manifest.json`/videos/
checkpoints -- it only reads files these pipelines already write, so it needs no changes to any
training script and can't fall out of sync with what's actually on disk.

Discovery convention (no registration needed for a new task -- this is what makes "any type of
task" work without a maintained list):
  training/runs/<run_name>/manifest.json            -> task "bin_picking" (the flat/default layout,
                                                        matches progress_artifacts.py)
  training/<task_dir>/runs/<run_name>/manifest.json -> task "<task_dir>" (e.g. "pick_place", and
                                                        automatically any future
                                                        training/<new_task>/runs/ someone adds)
Both known manifest.json schemas (bin-picking's nested "metrics" dict + two videos, pick-place's
flat metrics + one video) are handled client-side by runs_browser.html's normalizer -- this server
does no schema interpretation, just discovery and file serving.

Usage:
    python serve_runs.py [--port 8000]
    # open http://localhost:8000/
"""

from __future__ import annotations

import argparse
import http.server
import json
import mimetypes
import pathlib
import urllib.parse

SIM_ROOT = pathlib.Path(__file__).resolve().parent.parent
TRAINING_ROOT = SIM_ROOT / "training"
STATIC_DIR = pathlib.Path(__file__).resolve().parent
FLAT_TASK_LABEL = "bin_picking"


def _collect(runs: list[dict], task: str, runs_dir: pathlib.Path) -> None:
    for run_dir in sorted(p for p in runs_dir.iterdir() if p.is_dir()):
        manifest_path = run_dir / "manifest.json"
        if not manifest_path.is_file():
            continue
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue  # mid-write or unreadable this instant -- next poll will pick it up
        checkpoints = data.get("checkpoints", [])
        runs.append({
            "task": task,
            "run_name": run_dir.name,
            "manifest_url": f"/runs/{task}/{run_dir.name}/manifest.json",
            "updated": data.get("updated") or data.get("last_updated") or "",
            "latest_step": checkpoints[-1]["step"] if checkpoints else 0,
            "total_timesteps": data.get("total_timesteps") or data.get("total_timesteps_target") or 0,
            "num_checkpoints": len(checkpoints),
        })


def discover_runs() -> list[dict]:
    runs: list[dict] = []
    flat_runs_dir = TRAINING_ROOT / "runs"
    if flat_runs_dir.is_dir():
        _collect(runs, FLAT_TASK_LABEL, flat_runs_dir)
    for task_dir in sorted(p for p in TRAINING_ROOT.iterdir() if p.is_dir()):
        if task_dir.name == "runs":
            continue  # that's the flat layout, already handled above
        nested_runs_dir = task_dir / "runs"
        if nested_runs_dir.is_dir():
            _collect(runs, task_dir.name, nested_runs_dir)
    runs.sort(key=lambda r: r["updated"], reverse=True)
    return runs


def _run_root_for_task(task: str) -> pathlib.Path:
    return TRAINING_ROOT / "runs" if task == FLAT_TASK_LABEL else TRAINING_ROOT / task / "runs"


class RunsHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:  # quieter default logging
        pass

    def _send_json(self, payload, status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: pathlib.Path) -> None:
        if not path.is_file():
            self.send_error(404, "Not found")
            return
        content_type = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 (http.server's naming convention)
        parsed = urllib.parse.urlparse(self.path)
        parts = [urllib.parse.unquote(p) for p in parsed.path.split("/") if p]

        if not parts or parts == ["runs_browser.html"]:
            self._send_file(STATIC_DIR / "runs_browser.html")
            return

        if parts == ["index.json"]:
            self._send_json({"runs": discover_runs()})
            return

        if len(parts) >= 3 and parts[0] == "runs":
            task, run_name, *rest = parts[1:]
            run_root = _run_root_for_task(task) / run_name
            requested = (run_root / pathlib.Path(*rest)).resolve()
            try:
                requested.relative_to(run_root.resolve())
            except ValueError:
                self.send_error(403, "Forbidden")
                return
            self._send_file(requested)
            return

        self.send_error(404, "Not found")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    with http.server.ThreadingHTTPServer(("127.0.0.1", args.port), RunsHandler) as httpd:
        print(f"Serving cross-run dashboard at http://localhost:{args.port}/")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
