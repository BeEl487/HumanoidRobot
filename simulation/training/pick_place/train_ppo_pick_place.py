"""SB3 PPO training entrypoint for the suction pick-place task (sim_env/suction_pick_place_env.py).

Separate from training/train_ppo.py (the bin-picking task's trainer) -- different env, different
run directory layout -- per the "modular so additional tasks can easily be added later"
requirement, rather than overloading one trainer with two task modes.

Every `--eval-freq` timesteps (default 200,000), PeriodicArtifactCallback:
  1. saves a checkpoint (training/pick_place/runs/<run_name>/checkpoints/ckpt_<step>.zip)
  2. runs `--n-eval-episodes` deterministic evaluation episodes and computes success/pick rates
  3. renders one deterministic evaluation episode to video (.../videos/ckpt_<step>.mp4)
  4. appends the result to .../manifest.json and regenerates the dashboard HTML next to it
     (scripts/generate_pick_place_dashboard.py) -- so the dashboard reflects the latest checkpoint
     automatically, without a separate manual step, satisfying "the dashboard should refresh
     automatically whenever a new checkpoint is generated" for the on-disk artifact. Publishing
     that HTML as a claude.ai Artifact (a network call) is a separate, deliberate step outside
     this training loop -- see TRAINING_LOG.md for the interval-publish cadence.
"""

from __future__ import annotations

import os

# Must be set before numpy/mujoco import: with SubprocVecEnv, each of the n_envs worker
# processes otherwise lets its BLAS library grab every core for itself, so the workers spend
# more time fighting each other for CPU than stepping the sim. Capping each process to 1 BLAS
# thread is pure scheduling -- no effect on results, just removes the contention. Set via
# os.environ (not a CLI flag) so it's inherited by the spawned worker processes automatically.
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

import argparse
import datetime
import json
import pathlib
import sys
import time
from collections import deque

import imageio
import mujoco
import numpy as np
import subprocess
import yaml
from PIL import Image, ImageDraw
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.vec_env import DummyVecEnv, SubprocVecEnv

SIM_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(SIM_ROOT))
sys.path.insert(0, str(SIM_ROOT / "scripts"))

from sim_env.suction_pick_place_env import SuctionPickPlaceEnv, ENV_CONFIG_PATH  # noqa: E402
from generate_pick_place_dashboard import generate_dashboard  # noqa: E402
import self_monitor  # noqa: E402

CONFIG_PATH = SIM_ROOT / "config" / "train_pick_place_ppo.yaml"
RUNS_ROOT = pathlib.Path(__file__).resolve().parent / "runs"

EXT_CAM_LOOKAT = [0.16, 0.0, 0.78]
EXT_CAM_DISTANCE = 0.85
EXT_CAM_AZIMUTH = 140
EXT_CAM_ELEVATION = -25


def make_env():
    return Monitor(SuctionPickPlaceEnv())


def _draw_stats_overlay(frame: np.ndarray, step: int, info: dict, reward: float) -> np.ndarray:
    """Burns a small per-frame telemetry panel onto a rendered RGB frame, reading from the SAME
    info dict the reward/dashboard use (SuctionPickPlaceEnv.step) -- not a separate computation --
    so what's on screen can't drift from what actually drove that step's reward. Baked directly
    into the video (rather than a JS overlay keyed to video playback time) so it stays correct
    wherever the video is played, with no separate frame-index/timestamp sync logic to get wrong.
    """
    img = Image.fromarray(frame).convert("RGB")
    draw = ImageDraw.Draw(img, "RGBA")
    is_stalled = bool(info.get("is_stalled"))
    is_collision = bool(info.get("is_arm_collision"))
    is_idle = bool(info.get("is_idle"))
    warn = (255, 110, 110, 255)
    normal = (255, 255, 255, 255)
    lines = [
        (f"step {step}", normal),
        (f"attached: {bool(info.get('is_attached'))}", normal),
        (f"suction_cmd: {bool(info.get('suction_cmd'))}", normal),
        (f"stage: {info.get('stage', 0)}", normal),
        (f"ee->cube: {info.get('ee_to_cube_dist', 0.0):.3f} m", normal),
        (f"cube->dest: {info.get('carry_dist', 0.0):.3f} m", normal),
        (f"cube height: {info.get('cube_height', 0.0):.3f} m", normal),
        (f"collision: {is_collision}  stalled: {is_stalled}  idle: {is_idle}", warn if (is_collision or is_stalled or is_idle) else normal),
        (f"cube disturbance: {info.get('cube_disturbance', 0.0):.3f} m/s", warn if info.get("cube_disturbance", 0.0) > 0 else normal),
        (f"reward: {reward:+.2f}", normal),
    ]
    line_h = 13
    panel_h = line_h * len(lines) + 8
    panel_w = 168
    draw.rectangle([0, 0, panel_w, panel_h], fill=(0, 0, 0, 160))
    for i, (line, color) in enumerate(lines):
        draw.text((6, 5 + i * line_h), line, fill=color)
    return np.asarray(img)


def notify_windows(title: str, message: str) -> None:
    """Fires a native Windows toast notification via a background PowerShell process, so a
    checkpoint that saves/evaluates/renders (~seconds) is announced without blocking the training
    loop while it runs. Uses System.Windows.Forms.NotifyIcon's balloon tip -- ships with every
    Windows .NET install, so no extra pip/PS-module dependency (e.g. BurntToast) is required.
    Best-effort: a notification failure (e.g. running headless/non-Windows) must never interrupt
    training, so exceptions are swallowed."""
    ps_script = f"""
Add-Type -AssemblyName System.Windows.Forms
$ni = New-Object System.Windows.Forms.NotifyIcon
$ni.Icon = [System.Drawing.SystemIcons]::Information
$ni.Visible = $true
$ni.BalloonTipTitle = {json.dumps(title)}
$ni.BalloonTipText = {json.dumps(message)}
$ni.ShowBalloonTip(10000)
Start-Sleep -Seconds 10
$ni.Dispose()
"""
    try:
        subprocess.Popen(
            ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps_script],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    except Exception as e:  # pragma: no cover -- notifications must never crash training
        print(f"[notify_windows] failed to send notification: {e}")


def evaluate_checkpoint(model: PPO, n_episodes: int) -> dict:
    """Deterministic eval over fixed seeds -- mirrors training/evaluate.py's pattern but adds
    pick_success_rate (attached at least once) alongside place_success_rate (info["success"],
    the task's actual terminal goal) so a regression in "can't even attach" vs. "attaches but
    can't place" is distinguishable at a glance, the same diagnostic granularity the bin-picking
    task's contact_rate/grasp_rate split has provided all along.

    eval_mode=True (SuctionPickPlaceEnv's constructor arg) forces every episode through the full
    task from scratch, disabling the training-time curriculum shortcut -- otherwise these numbers
    would be a mix of "genuinely solved it" and "started already past the hard part" (see
    SuctionPickPlaceEnv.__init__'s eval_mode docstring)."""
    env = SuctionPickPlaceEnv(eval_mode=True)
    rewards, lengths, place_success, pick_success, suction_cmd_rate, max_stage = [], [], [], [], [], []
    for ep in range(n_episodes):
        obs, info = env.reset(seed=2000 + ep)
        done = False
        ep_reward = 0.0
        ep_length = 0
        ep_suction = 0
        ep_stage = 0
        while not done:
            action, _ = model.predict(obs, deterministic=True)
            obs, reward, terminated, truncated, info = env.step(action)
            ep_reward += reward
            ep_length += 1
            ep_suction += int(bool(info.get("suction_cmd", 0.0)))
            ep_stage = max(ep_stage, int(info.get("stage", 0)))
            done = terminated or truncated
        rewards.append(ep_reward)
        lengths.append(ep_length)
        place_success.append(bool(info.get("success", False)))
        pick_success.append(bool(info.get("attached", False)))
        suction_cmd_rate.append(ep_suction / ep_length)
        max_stage.append(ep_stage)
    return {
        "mean_reward": float(np.mean(rewards)),
        "mean_episode_length": float(np.mean(lengths)),
        "success_rate": float(np.mean(place_success)),
        "pick_success_rate": float(np.mean(pick_success)),
        "place_success_rate": float(np.mean(place_success)),
        "mean_suction_cmd_rate": float(np.mean(suction_cmd_rate)),
        "mean_max_stage": float(np.mean(max_stage)),
        "n_episodes": n_episodes,
    }


def render_checkpoint_video(model: PPO, out_path: pathlib.Path, seed: int = 0, fps: int = 20) -> None:
    # eval_mode=True: same reasoning as evaluate_checkpoint -- the demo video should show genuine
    # from-scratch task performance, not a curriculum-assisted (already-attached) episode.
    env = SuctionPickPlaceEnv(eval_mode=True)
    mj_model, mj_data = env.unwrapped.model, env.unwrapped.data
    renderer = mujoco.Renderer(mj_model, height=480, width=640)
    cam = mujoco.MjvCamera()
    mujoco.mjv_defaultFreeCamera(mj_model, cam)
    cam.lookat = EXT_CAM_LOOKAT
    cam.distance = EXT_CAM_DISTANCE
    cam.azimuth = EXT_CAM_AZIMUTH
    cam.elevation = EXT_CAM_ELEVATION

    obs, info = env.reset(seed=seed)
    frames = []
    terminated = truncated = False
    step = 0
    reward = 0.0
    while not (terminated or truncated):
        action, _ = model.predict(obs, deterministic=True)
        obs, reward, terminated, truncated, info = env.step(action)
        step += 1
        renderer.update_scene(mj_data, camera=cam)
        frames.append(_draw_stats_overlay(renderer.render(), step, info, reward))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    imageio.mimsave(str(out_path), frames, fps=fps)


class PeriodicArtifactCallback(BaseCallback):
    # How often (timesteps) to push an updated start_attached_prob to the training env(s) --
    # frequent enough for a reasonably smooth anneal, infrequent enough that the env_method call
    # (cheap, but still a VecEnv round-trip) doesn't add meaningful overhead.
    ANNEAL_FREQ = 5000

    def __init__(
        self, run_dir: pathlib.Path, eval_freq: int, n_eval_episodes: int, total_timesteps: int,
        start_attached_prob_initial: float | None = None, start_attached_prob_final: float | None = None,
        log_freq: int = 5000, analysis_freq: int = 400000, stall_window_steps: int = 300000,
        verbose: int = 1,
    ):
        super().__init__(verbose)
        self.run_dir = run_dir
        self.eval_freq = eval_freq
        self.n_eval_episodes = n_eval_episodes
        self.total_timesteps = total_timesteps
        self.start_attached_prob_initial = start_attached_prob_initial
        self.start_attached_prob_final = start_attached_prob_final
        self.log_freq = log_freq
        self.analysis_freq = analysis_freq
        self.stall_window_steps = stall_window_steps
        self.checkpoints_dir = run_dir / "checkpoints"
        self.videos_dir = run_dir / "videos"
        self.manifest_path = run_dir / "manifest.json"
        self.checkpoints_dir.mkdir(parents=True, exist_ok=True)
        self.videos_dir.mkdir(parents=True, exist_ok=True)
        self._last_cycle_step = 0
        self._last_anneal_step = 0
        self._last_log_step = 0
        self._last_analysis_step = 0
        self.metrics_logger = self_monitor.MetricsLogger(run_dir / "metrics_log.csv")
        # Continuous bookkeeping the logger needs but SB3/Monitor don't expose directly --
        # Monitor injects info["episode"] = {"r":..., "l":..., "t":...} on the step an episode
        # ends (see stable_baselines3.common.monitor.Monitor.step); success isn't part of that,
        # so it's tracked separately from this env's own info["success"].
        self._episode_count = 0
        self._recent_rewards: deque[float] = deque(maxlen=100)
        self._recent_success: deque[bool] = deque(maxlen=100)
        self._last_ep_reward: float | None = None
        self._last_ep_length: int | None = None
        # Own wall-clock fps tracking, independent of SB3's logger -- self.model.logger.name_to_value
        # is cleared by Logger.dump() right after each rollout's metrics are written (see
        # stable_baselines3.common.logger.Logger.dump), so sampling "time/fps" from it on this
        # callback's own log_freq cadence (not aligned to SB3's rollout boundary) frequently landed
        # on an already-cleared dict -- confirmed empirically: fps/eta_seconds were blank in most
        # metrics_log.csv rows and analysis reports during pp_v8. This tracks steps-per-wall-second
        # directly, so it's always available regardless of SB3's internal logging cadence.
        self._fps_last_time = time.time()
        self._fps_last_step = 0
        self._current_fps: float | None = None

    def _on_step(self) -> bool:
        if self.start_attached_prob_initial is not None and (
            self.num_timesteps - self._last_anneal_step >= self.ANNEAL_FREQ
        ):
            self._last_anneal_step = self.num_timesteps
            frac = min(self.num_timesteps / self.total_timesteps, 1.0)
            prob = self.start_attached_prob_initial + frac * (
                self.start_attached_prob_final - self.start_attached_prob_initial
            )
            self.training_env.env_method("set_start_attached_prob", prob)

        infos = self.locals.get("infos") or []
        dones = self.locals.get("dones")
        for i, info in enumerate(infos):
            if dones is not None and dones[i] and "episode" in info:
                self._episode_count += 1
                self._recent_rewards.append(info["episode"]["r"])
                self._recent_success.append(bool(info.get("success", False)))
                self._last_ep_reward = info["episode"]["r"]
                self._last_ep_length = info["episode"]["l"]

        if self.num_timesteps - self._last_log_step >= self.log_freq:
            elapsed = time.time() - self._fps_last_time
            if elapsed > 0:
                self._current_fps = (self.num_timesteps - self._fps_last_step) / elapsed
            self._fps_last_time = time.time()
            self._fps_last_step = self.num_timesteps
            self._last_log_step = self.num_timesteps
            self._log_metrics_row(infos[0] if infos else {})

        if self.num_timesteps - self._last_analysis_step >= self.analysis_freq:
            self._last_analysis_step = self.num_timesteps
            stop = self._run_periodic_analysis()
            if stop:
                return False

        if self.num_timesteps - self._last_cycle_step >= self.eval_freq:
            self._last_cycle_step = self.num_timesteps
            self._run_cycle()
        return True

    def _log_metrics_row(self, latest_info: dict) -> None:
        name_to_value = self.model.logger.name_to_value
        fps = self._current_fps
        eta = (self.total_timesteps - self.num_timesteps) / fps if fps else None
        entropy_loss = name_to_value.get("train/entropy_loss")
        ee_pos = latest_info.get("ee_pos", (None, None, None))
        cube_pos = latest_info.get("cube_pos", (None, None, None))
        self.metrics_logger.log_row({
            "global_step": self.num_timesteps,
            "episode_num": self._episode_count,
            "episode_reward": self._last_ep_reward,
            "episode_length": self._last_ep_length,
            "success_rate": float(np.mean(self._recent_success)) if self._recent_success else "",
            "avg_reward_100": float(np.mean(self._recent_rewards)) if self._recent_rewards else "",
            "policy_loss": name_to_value.get("train/policy_gradient_loss"),
            "value_loss": name_to_value.get("train/value_loss"),
            "entropy": -entropy_loss if entropy_loss is not None else "",
            "learning_rate": name_to_value.get("train/learning_rate"),
            "fps": fps,
            "eta_seconds": eta,
            "ee_x": ee_pos[0], "ee_y": ee_pos[1], "ee_z": ee_pos[2],
            "cube_x": cube_pos[0], "cube_y": cube_pos[1], "cube_z": cube_pos[2],
            "ee_to_cube_dist": latest_info.get("ee_to_cube_dist"),
            "cube_to_goal_dist": latest_info.get("carry_dist"),
            "is_grasped": latest_info.get("is_attached"),
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        })

    def _run_periodic_analysis(self) -> bool:
        """Every analysis_freq steps: read back the metrics log, compute trend stats over the
        last stall_window_steps, run trajectory-based behavior classification, and write a report.
        Returns True if training should stop (stalled learning detected) -- does NOT interrupt
        training at any other cadence, per the "don't interrupt frequently" requirement."""
        step = self.num_timesteps
        if self.verbose:
            print(f"[PeriodicArtifactCallback] step {step}: running periodic self-monitoring analysis...")

        window = self_monitor.analyze_window(
            self.metrics_logger.csv_path, step, self.stall_window_steps
        )
        stalled = self_monitor.is_stalled(window)

        behavior = None
        try:
            record = self_monitor.record_trajectories(
                self.model, lambda: SuctionPickPlaceEnv(eval_mode=True), n_episodes=10, seed_start=5000 + step
            )
            behavior = self_monitor.classify_behavior(record)
        except Exception as e:  # pragma: no cover -- analysis must never crash training
            if self.verbose:
                print(f"[PeriodicArtifactCallback] behavior analysis failed: {e}")

        fps = self._current_fps
        report_path = self_monitor.write_analysis_report(
            self.run_dir, step, window, behavior, stalled, fps, self.total_timesteps
        )
        if self.verbose:
            print(f"[PeriodicArtifactCallback] analysis written to {report_path} (stalled={stalled})")

        reward_trend = "n/a" if window.get("insufficient_data") else f"{window.get('reward_relative_change', 0.0):+.0%}"
        behavior_summary = "n/a"
        if behavior and behavior.get("n_episodes"):
            failure_fractions = {
                "reached, no grasp": behavior.get("reached_no_grasp_fraction", 0.0),
                "grasped, no lift": behavior.get("grasped_no_lift_fraction", 0.0),
                "lifted, no transport": behavior.get("lifted_no_transport_fraction", 0.0),
                "stuck/collision": behavior.get("stuck_at_collision_fraction", 0.0),
            }
            dominant = max(failure_fractions, key=failure_fractions.get)
            behavior_summary = f"{dominant} ({failure_fractions[dominant]:.0%})"
        notify_windows(
            f"Analysis ready: {self.run_dir.name} @ {step:,}",
            f"{report_path.name} | reward trend {reward_trend} | stalled={stalled} | {behavior_summary}",
        )

        if stalled:
            # Capture a final checkpoint/eval/video AT the stall point before stopping, so the
            # dashboard and the video the agent visually reviews afterward both reflect exactly
            # the policy that triggered the stop, not a stale earlier checkpoint.
            self._last_cycle_step = step
            self._run_cycle(is_final=True)
            (self.run_dir / "STALL_DETECTED.flag").write_text(
                f"stalled at step {step}\nsee {report_path.name}\n", encoding="utf-8"
            )
            notify_windows(
                f"Training STALLED: {self.run_dir.name} @ {step:,}",
                f"Learning stalled -- training stopped automatically. See {report_path.name}",
            )
            return True
        return False

    def _on_training_end(self) -> None:
        # Always close out with a final checkpoint/eval/video even if total_timesteps isn't an
        # exact multiple of eval_freq -- otherwise the dashboard's last entry could be stale by
        # up to eval_freq-1 steps relative to the actually-saved final policy.
        if self._last_cycle_step != self.num_timesteps:
            self._last_cycle_step = self.num_timesteps
            self._run_cycle(is_final=True)

    def _run_cycle(self, is_final: bool = False) -> None:
        step = self.num_timesteps
        if self.verbose:
            print(f"[PeriodicArtifactCallback] step {step}: saving checkpoint, evaluating, rendering...")

        ckpt_path = self.checkpoints_dir / f"ckpt_{step}.zip"
        self.model.save(str(ckpt_path))

        metrics = evaluate_checkpoint(self.model, self.n_eval_episodes)

        video_path = self.videos_dir / f"ckpt_{step}.mp4"
        render_checkpoint_video(self.model, video_path)

        entry = {
            "step": step,
            "checkpoint": str(ckpt_path.relative_to(self.run_dir)).replace("\\", "/"),
            "video": str(video_path.relative_to(self.run_dir)).replace("\\", "/"),
            "is_final": is_final,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            **metrics,
        }

        manifest = {"checkpoints": [], "total_timesteps_target": self.total_timesteps}
        if self.manifest_path.exists():
            manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        manifest["checkpoints"] = [e for e in manifest.get("checkpoints", []) if e["step"] != step] + [entry]
        manifest["checkpoints"].sort(key=lambda e: e["step"])
        manifest["total_timesteps_target"] = self.total_timesteps
        manifest["last_updated"] = entry["timestamp"]
        self.manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

        dashboard_path = generate_dashboard(self.run_dir)
        if self.verbose:
            print(
                f"[PeriodicArtifactCallback] step {step}: success_rate={metrics['success_rate']:.2f} "
                f"pick_success_rate={metrics['pick_success_rate']:.2f} mean_reward={metrics['mean_reward']:.2f} "
                f"-> {dashboard_path}"
            )

        pct = f"{100 * step / self.total_timesteps:.0f}%" if self.total_timesteps else "?"
        notify_windows(
            f"Checkpoint {'(final) ' if is_final else ''}{self.run_dir.name} @ {step:,}",
            f"progress {pct} | success {metrics['success_rate']:.0%} | "
            f"pick {metrics['pick_success_rate']:.0%} | reward {metrics['mean_reward']:.1f}",
        )


def train(
    total_timesteps: int | None = None,
    run_name: str | None = None,
    eval_freq: int | None = None,
    n_eval_episodes: int | None = None,
    init_checkpoint: str | None = None,
) -> pathlib.Path:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    timesteps = total_timesteps if total_timesteps is not None else cfg["total_timesteps"]
    freq = eval_freq if eval_freq is not None else cfg["eval_freq"]
    n_eval = n_eval_episodes if n_eval_episodes is not None else cfg["n_eval_episodes"]
    name = run_name or f"pp_v1_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"

    run_dir = RUNS_ROOT / name
    run_dir.mkdir(parents=True, exist_ok=True)
    logs_dir = run_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    n_envs = cfg.get("n_envs", 1)
    if n_envs > 1:
        env = SubprocVecEnv([make_env for _ in range(n_envs)])
    else:
        env = DummyVecEnv([make_env])

    if init_checkpoint:
        # Continue from a previous run's weights instead of a fresh random init -- the policy
        # architecture is restored from the checkpoint itself (SB3 saves it alongside the
        # weights), so this only makes sense between runs that share the same observation/action
        # space (true for pp_v6/pp_v7/pp_v8 -- only the reward/scene/network-size config changed,
        # not the Dict obs or the 4-dim action). A run relaunched to fix a genuine exploit (e.g.
        # pp_v3->pp_v4 after the continuous lift_bonus_weight bug) should NOT continue from the
        # exploited checkpoint -- that's a judgment call made per-relaunch, not automatic here.
        print(f"Continuing from checkpoint: {init_checkpoint}")
        model = PPO.load(
            init_checkpoint, env=env, tensorboard_log=str(logs_dir),
            device=cfg.get("device", "auto"), print_system_info=False,
        )
        model.learning_rate = cfg["learning_rate"]
        model.ent_coef = cfg.get("ent_coef", 0.0)
    else:
        model = PPO(
            cfg["policy"], env,
            learning_rate=cfg["learning_rate"], n_steps=cfg["n_steps"], batch_size=cfg["batch_size"],
            ent_coef=cfg.get("ent_coef", 0.0), seed=cfg.get("seed", 0), device=cfg.get("device", "auto"),
            policy_kwargs=cfg.get("policy_kwargs", None),
            tensorboard_log=str(logs_dir), verbose=1,
        )

    with open(ENV_CONFIG_PATH, encoding="utf-8") as f:
        env_cfg = yaml.safe_load(f)
    curriculum_cfg = env_cfg.get("curriculum", {})
    anneal_initial = curriculum_cfg.get("start_attached_prob_initial")
    anneal_final = curriculum_cfg.get("start_attached_prob_final")

    callback = PeriodicArtifactCallback(
        run_dir, freq, n_eval, timesteps,
        start_attached_prob_initial=anneal_initial, start_attached_prob_final=anneal_final,
        log_freq=cfg.get("log_freq", 5000), analysis_freq=cfg.get("analysis_freq", 400000),
        stall_window_steps=cfg.get("stall_window_steps", 300000),
    )
    model.learn(total_timesteps=timesteps, callback=callback, tb_log_name=name)

    final_path = run_dir / "checkpoints" / "final.zip"
    model.save(str(final_path))
    print(f"Training complete. Final checkpoint: {final_path}")
    print(f"Dashboard: {run_dir / 'dashboard.html'}")
    return final_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--timesteps", type=int, default=None, help="override config total_timesteps")
    parser.add_argument("--run-name", default=None)
    parser.add_argument("--eval-freq", type=int, default=None, help="override config eval_freq (checkpoint/eval/video cadence)")
    parser.add_argument("--n-eval-episodes", type=int, default=None)
    parser.add_argument("--init-checkpoint", default=None, help="continue training from a previous run's checkpoint .zip instead of a fresh random init")
    args = parser.parse_args()
    train(
        total_timesteps=args.timesteps, run_name=args.run_name,
        eval_freq=args.eval_freq, n_eval_episodes=args.n_eval_episodes,
        init_checkpoint=args.init_checkpoint,
    )
