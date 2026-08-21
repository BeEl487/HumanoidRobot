"""Atomic writers for the "actively training" side of the run convention (see RUN_CONVENTION.md):
`live_status.json` + `live/<camera>.jpg`. Plain stdlib + PIL only -- this runs inside a training
process, not the dashboard, so it deliberately has no PyQt dependency.
"""

from __future__ import annotations

import json
import pathlib
import tempfile
import time
from datetime import datetime, timezone

import numpy as np
from PIL import Image

# On Windows, os.replace onto a target another process currently has open for reading (e.g. the
# dashboard polling this exact file) can raise PermissionError (WinError 5) instead of atomically
# succeeding the way POSIX rename does -- confirmed fatal in practice: it propagated out of a
# training callback and killed the whole run (touch_cube_v1, 2026-08-21). The reader lock is
# transient (a dashboard poll holds the handle for a moment, not indefinitely), so a short bounded
# retry resolves it without changing behavior on POSIX, where this branch is simply never taken.
_REPLACE_RETRIES = 5
_REPLACE_RETRY_DELAY_S = 0.02


def _atomic_write_bytes(path: pathlib.Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp_", suffix=path.suffix)
    try:
        with open(fd, "wb") as f:
            f.write(data)
        for attempt in range(_REPLACE_RETRIES):
            try:
                pathlib.Path(tmp_name).replace(path)
                return
            except PermissionError:
                if attempt == _REPLACE_RETRIES - 1:
                    raise
                time.sleep(_REPLACE_RETRY_DELAY_S)
    except BaseException:
        pathlib.Path(tmp_name).unlink(missing_ok=True)
        raise


def write_live_status(
    run_dir: pathlib.Path,
    *,
    sim_engine: str,
    step: int,
    cameras: list[str],
    episode_started: datetime,
    note: str = "",
) -> None:
    payload = {
        "sim_engine": sim_engine,
        "step": step,
        "updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "episode_started": episode_started.isoformat(timespec="seconds"),
        "cameras": cameras,
        "note": note,
    }
    _atomic_write_bytes(run_dir / "live_status.json", json.dumps(payload, indent=2).encode("utf-8"))


def clear_live_status(run_dir: pathlib.Path) -> None:
    (run_dir / "live_status.json").unlink(missing_ok=True)


def write_live_frame(run_dir: pathlib.Path, camera_name: str, frame: np.ndarray) -> None:
    """`frame`: HxWx3 uint8 RGB."""
    buffer_path = run_dir / "live" / f"{camera_name}.jpg"
    image = Image.fromarray(frame, mode="RGB")
    import io
    buf = io.BytesIO()
    image.save(buf, format="JPEG", quality=80)
    _atomic_write_bytes(buffer_path, buf.getvalue())
