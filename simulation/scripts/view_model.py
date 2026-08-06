"""Open an interactive MuJoCo viewer for manual visual inspection.

Run after any model change to eyeball proportions, joint motion, and geometry — the qualitative
check automated NaN/limit/mass checks in check_model.py can't catch on their own.
"""

from __future__ import annotations

import mujoco
import mujoco.viewer

from build_model import load_model

if __name__ == "__main__":
    model, data = load_model()
    with mujoco.viewer.launch_passive(model, data) as viewer:
        while viewer.is_running():
            mujoco.mj_step(model, data)
            viewer.sync()
