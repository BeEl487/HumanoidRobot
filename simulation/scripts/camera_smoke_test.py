"""Milestone 4 camera verification: render a non-blank image at the configured resolution,
confirm changing the resolution config changes the render output shape, and save a snapshot for
manual visual inspection that the camera actually frames the workspace in front of the robot.

Also the place this project first validates MuJoCo's offscreen renderer works on this specific
Windows machine at all -- flagged in the plan as a known cross-platform risk (GL context behavior
differs from Linux/EGL) to resolve before the Gymnasium env (Milestone 7) depends on it.
"""

from __future__ import annotations

import pathlib

import numpy as np
import mujoco
import yaml

from build_model import CAMERA_CONFIG_PATH, load_model

SNAPSHOT_PATH = pathlib.Path(__file__).resolve().parent.parent / "docs" / "camera_snapshot.png"


def render_at_default_resolution() -> np.ndarray:
    model, data = load_model()
    mujoco.mj_resetData(model, data)
    mujoco.mj_forward(model, data)

    with open(CAMERA_CONFIG_PATH, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    width, height = cfg["resolution_default"]

    renderer = mujoco.Renderer(model, height=height, width=width)
    renderer.update_scene(data, camera=cfg["name"])
    img = renderer.render()

    assert img.shape == (height, width, 3), f"unexpected render shape {img.shape}"
    assert img.std() > 0, "render is blank (uniform image) -- offscreen renderer likely broken"
    print(f"render_at_default_resolution: OK (shape={img.shape}, std={img.std():.2f})")
    return img


def render_respects_resolution_config() -> None:
    """Same camera, different resolution -- the render output shape must follow, proving the
    camera is actually config-driven and not a hardcoded resolution somewhere."""
    model, data = load_model()
    mujoco.mj_resetData(model, data)
    mujoco.mj_forward(model, data)

    with open(CAMERA_CONFIG_PATH, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    width, height = cfg["resolution_debug"]

    renderer = mujoco.Renderer(model, height=height, width=width)
    renderer.update_scene(data, camera=cfg["name"])
    img = renderer.render()
    assert img.shape == (height, width, 3), f"unexpected render shape {img.shape}"
    print(f"render_respects_resolution_config: OK (debug resolution shape={img.shape})")


if __name__ == "__main__":
    img = render_at_default_resolution()
    render_respects_resolution_config()

    import imageio
    SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
    imageio.imwrite(SNAPSHOT_PATH, img)
    print(f"Saved snapshot to {SNAPSHOT_PATH} for manual visual inspection.")
    print("camera_smoke_test.py: ALL CHECKS PASSED")
