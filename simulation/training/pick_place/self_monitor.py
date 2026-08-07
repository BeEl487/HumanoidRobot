"""Self-monitoring utilities for the suction pick-place training pipeline: a continuous CSV
metrics log (survives an early-terminated run, unlike TensorBoard's own event files which need the
TB UI to inspect), periodic (every `analysis_freq` steps) trend analysis, stalled-learning
detection, and trajectory-based behavior classification (is the policy entering the box at all,
approaching the cube, grasping-but-not-lifting, etc. -- not just aggregate reward).

Used by training/pick_place/train_ppo_pick_place.py's PeriodicArtifactCallback. Kept in its own
module rather than folded into the callback so the analysis/classification logic (pure functions
over logged data) stays testable independent of SB3's callback machinery.
"""

from __future__ import annotations

import csv
import datetime
import pathlib

import numpy as np

CSV_COLUMNS = [
    "global_step", "episode_num", "episode_reward", "episode_length", "success_rate",
    "avg_reward_100", "policy_loss", "value_loss", "entropy", "learning_rate", "fps",
    "eta_seconds", "ee_x", "ee_y", "ee_z", "cube_x", "cube_y", "cube_z",
    "ee_to_cube_dist", "cube_to_goal_dist", "is_grasped", "timestamp",
]


class MetricsLogger:
    """Appends one CSV row per call to `log_row`. Writes the header once, on first use, so a run
    that dies mid-training still leaves a readable partial log (no buffering across the whole run
    that could be lost)."""

    def __init__(self, csv_path: pathlib.Path):
        self.csv_path = csv_path
        if not self.csv_path.exists():
            self.csv_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.csv_path, "w", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow(CSV_COLUMNS)

    def log_row(self, row: dict) -> None:
        with open(self.csv_path, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([row.get(col, "") for col in CSV_COLUMNS])


def _read_rows_since(csv_path: pathlib.Path, since_step: int) -> list[dict]:
    if not csv_path.exists():
        return []
    with open(csv_path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    out = []
    for row in rows:
        try:
            if int(row["global_step"]) >= since_step:
                out.append(row)
        except (ValueError, KeyError):
            continue
    return out


def _trend_slope(values: list[float]) -> float:
    """Least-squares slope of values against their index -- positive means improving. Returns 0.0
    for fewer than 2 points (can't fit a trend)."""
    if len(values) < 2:
        return 0.0
    x = np.arange(len(values), dtype=np.float64)
    y = np.asarray(values, dtype=np.float64)
    slope, _ = np.polyfit(x, y, 1)
    return float(slope)


def analyze_window(csv_path: pathlib.Path, current_step: int, window_steps: int) -> dict:
    """Trend stats over the last `window_steps` of logged data: reward/success-rate trend,
    whether entropy has collapsed early relative to the run's own start, loss stability."""
    rows = _read_rows_since(csv_path, max(current_step - window_steps, 0))
    if len(rows) < 3:
        return {"n_rows": len(rows), "insufficient_data": True}

    def col(name: str) -> list[float]:
        out = []
        for r in rows:
            try:
                out.append(float(r[name]))
            except (ValueError, KeyError):
                pass
        return out

    rewards = col("avg_reward_100")
    success = col("success_rate")
    entropy = col("entropy")
    value_loss = col("value_loss")
    policy_loss = col("policy_loss")

    all_rows = _read_rows_since(csv_path, 0)
    entropy_all = []
    for r in all_rows[: max(len(all_rows) // 10, 5)]:
        try:
            entropy_all.append(float(r["entropy"]))
        except (ValueError, KeyError):
            pass
    entropy_start = float(np.mean(entropy_all)) if entropy_all else None

    reward_slope = _trend_slope(rewards)
    reward_span = (max(rewards) - min(rewards)) if rewards else 0.0
    reward_now = rewards[-1] if rewards else None
    reward_relative_change = (reward_slope * len(rewards)) / (abs(reward_now) + 1e-6) if reward_now is not None else 0.0

    entropy_now = float(np.mean(entropy[-5:])) if entropy else None
    entropy_collapsed = (
        entropy_start is not None and entropy_now is not None and abs(entropy_start) > 1e-6
        and (entropy_now / entropy_start) < 0.25
    )

    return {
        "n_rows": len(rows),
        "insufficient_data": False,
        "reward_trend_slope": reward_slope,
        "reward_relative_change": reward_relative_change,
        "reward_span": reward_span,
        "reward_now": reward_now,
        "success_rate_now": success[-1] if success else None,
        "success_rate_trend_slope": _trend_slope(success),
        "entropy_start": entropy_start,
        "entropy_now": entropy_now,
        "entropy_collapsed_early": entropy_collapsed,
        "value_loss_std": float(np.std(value_loss)) if value_loss else None,
        "policy_loss_std": float(np.std(policy_loss)) if policy_loss else None,
    }


def is_stalled(window: dict, min_relative_improvement: float = 0.03) -> bool:
    """Flat/no-improving reward over the window AND (exploration already collapsed OR losses have
    gone flat) -- either symptom alone is normal PPO behavior at some point in training; both
    together, sustained over the window, is the "stuck" signature this is meant to catch."""
    if window.get("insufficient_data"):
        return False
    flat_reward = abs(window["reward_relative_change"]) < min_relative_improvement
    stalled_success = (window.get("success_rate_trend_slope") or 0.0) <= 0.0
    return bool(flat_reward and stalled_success and window.get("entropy_collapsed_early"))


def record_trajectories(model, env_factory, n_episodes: int = 10, seed_start: int = 5000) -> dict:
    """Runs n_episodes deterministic eval_mode episodes, recording the full per-step trajectory
    (not just the aggregate metrics evaluate_checkpoint computes) -- needed for behavior
    classification (is the policy entering the box at all, approaching the cube, grasping but not
    lifting, etc.), which can't be read off a single scalar reward number."""
    env = env_factory()
    u = env.unwrapped
    geometry = {
        "src_xy": (u._src_x, u._src_y), "dst_xy": (u._dst_x, u._dst_y),
        "box_half_w": u._box_half_w, "box_half_d": u._box_half_d,
        "floor_top_z": u._floor_top_z, "lift_threshold_m": u.cfg["reward"]["lift_threshold_m"],
    }

    episodes = []
    for ep in range(n_episodes):
        obs, info = env.reset(seed=seed_start + ep)
        traj = {"ee_pos": [], "cube_pos": [], "is_attached": [], "is_arm_collision": [], "is_stalled": [], "stage": []}
        done = False
        while not done:
            action, _ = model.predict(obs, deterministic=True)
            obs, reward, terminated, truncated, info = env.step(action)
            traj["ee_pos"].append(info["ee_pos"])
            traj["cube_pos"].append(info["cube_pos"])
            traj["is_attached"].append(info["is_attached"])
            traj["is_arm_collision"].append(info["is_arm_collision"])
            traj["is_stalled"].append(info["is_stalled"])
            traj["stage"].append(info.get("stage", 0))
            done = terminated or truncated
        for key in ("ee_pos", "cube_pos"):
            traj[key] = np.array(traj[key])
        episodes.append(traj)
    return {"geometry": geometry, "episodes": episodes}


def classify_behavior(record: dict) -> dict:
    """Heuristic conclusions from recorded trajectories -- the automatic version of "watch the
    rollout and see what it's actually doing" this project has relied on by hand all session."""
    geo = record["geometry"]
    episodes = record["episodes"]
    n = len(episodes)
    if n == 0:
        return {"n_episodes": 0}

    src_x, src_y = geo["src_xy"]
    half_w, half_d = geo["box_half_w"], geo["box_half_d"]

    def in_box_xy(pos_xy, center_xy):
        return abs(pos_xy[0] - center_xy[0]) <= half_w and abs(pos_xy[1] - center_xy[1]) <= half_d

    entered_box = 0
    approached_cube = 0
    reached_no_grasp = 0
    grasped_no_lift = 0
    lifted_no_transport = 0
    oscillating = 0
    stuck_at_collision = 0
    net_y_drift = []
    min_dists = []

    for traj in episodes:
        ee = traj["ee_pos"]
        cube = traj["cube_pos"]
        attached = np.array(traj["is_attached"])
        collision = np.array(traj["is_arm_collision"])
        stalled = np.array(traj["is_stalled"])

        ever_in_box = any(in_box_xy(p[:2], (src_x, src_y)) for p in ee)
        entered_box += int(ever_in_box)

        dists = np.linalg.norm(ee - cube, axis=1)
        min_dist = float(np.min(dists))
        min_dists.append(min_dist)
        close = min_dist < 0.05
        approached_cube += int(close)

        ever_attached = bool(np.any(attached))
        if close and not ever_attached:
            reached_no_grasp += 1

        max_height = float(np.max(cube[:, 2])) - geo["floor_top_z"] if len(cube) else 0.0
        ever_lifted = ever_attached and max_height > geo["lift_threshold_m"]
        if ever_attached and not ever_lifted:
            grasped_no_lift += 1

        if ever_lifted:
            dest_dist = np.linalg.norm(cube[:, :2] - np.array(geo["dst_xy"]), axis=1)
            improved = bool(dest_dist[-1] < dest_dist[np.argmax(attached)] - 0.02) if np.any(attached) else False
            if not improved:
                lifted_no_transport += 1

        if len(ee) > 5:
            y_vel = np.diff(ee[:, 1])
            sign_changes = int(np.sum(np.diff(np.sign(y_vel)) != 0))
            if sign_changes > len(y_vel) * 0.3:
                oscillating += 1
            net_y_drift.append(float(ee[-1, 1] - ee[0, 1]))

        if np.any(stalled):
            stuck_at_collision += 1

    lateral_bias = None
    if net_y_drift:
        mean_drift = float(np.mean(net_y_drift))
        if abs(mean_drift) > 0.02:
            lateral_bias = "toward +Y (source/left side)" if mean_drift > 0 else "toward -Y (destination/right side)"

    return {
        "n_episodes": n,
        "entered_box_fraction": entered_box / n,
        "approached_cube_fraction": approached_cube / n,
        "reached_no_grasp_fraction": reached_no_grasp / n,
        "grasped_no_lift_fraction": grasped_no_lift / n,
        "lifted_no_transport_fraction": lifted_no_transport / n,
        "oscillating_fraction": oscillating / n,
        "stuck_at_collision_fraction": stuck_at_collision / n,
        "lateral_bias": lateral_bias,
        "mean_min_ee_to_cube_dist": float(np.mean(min_dists)) if min_dists else None,
    }


def write_analysis_report(
    run_dir: pathlib.Path, step: int, window: dict, behavior: dict | None, stalled: bool,
    fps: float | None, total_timesteps: int,
) -> pathlib.Path:
    eta = None
    if fps and fps > 0:
        eta = max(total_timesteps - step, 0) / fps

    lines = [
        f"# Self-monitoring analysis @ step {step:,}",
        f"generated: {datetime.datetime.now(datetime.timezone.utc).isoformat()}",
        "",
        "## Metrics trend (this window)",
    ]
    if window.get("insufficient_data"):
        lines.append("Not enough logged rows yet to compute a trend.")
    else:
        lines += [
            f"- reward now: {window['reward_now']:.2f}" if window["reward_now"] is not None else "- reward now: n/a",
            f"- reward trend slope: {window['reward_trend_slope']:+.4f} /log-tick "
            f"(relative change over window: {window['reward_relative_change']*100:+.1f}%)",
            f"- success rate now: {window['success_rate_now']}",
            f"- success rate trend slope: {window['success_rate_trend_slope']:+.5f}",
            f"- entropy: {window['entropy_start']:.3f} (run start) -> {window['entropy_now']:.3f} (now)"
            + (" -- COLLAPSED EARLY" if window["entropy_collapsed_early"] else ""),
            f"- value_loss std: {window['value_loss_std']:.3f}, policy_loss std: {window['policy_loss_std']:.4f}",
        ]
    lines += ["", f"## Simulation performance", f"- fps: {fps:.1f}" if fps else "- fps: n/a"]
    if eta is not None:
        lines.append(f"- estimated remaining time: {eta/3600:.2f} hours ({eta/60:.0f} min)")

    if behavior is not None:
        lines += ["", "## Behavior analysis (trajectory-based)"]
        if behavior.get("n_episodes", 0) == 0:
            lines.append("No trajectories recorded.")
        else:
            lines += [
                f"- entered the source box: {behavior['entered_box_fraction']*100:.0f}% of episodes",
                f"- approached the cube (<5cm): {behavior['approached_cube_fraction']*100:.0f}% of episodes",
                f"- reached the cube but never grasped: {behavior['reached_no_grasp_fraction']*100:.0f}% of episodes",
                f"- grasped but never lifted: {behavior['grasped_no_lift_fraction']*100:.0f}% of episodes",
                f"- lifted but never transported toward the goal: {behavior['lifted_no_transport_fraction']*100:.0f}% of episodes",
                f"- oscillating end-effector motion: {behavior['oscillating_fraction']*100:.0f}% of episodes",
                f"- stuck at a collision (stalled): {behavior['stuck_at_collision_fraction']*100:.0f}% of episodes",
                f"- lateral bias: {behavior['lateral_bias'] or 'none detected'}",
                f"- mean closest EE-to-cube approach: {behavior['mean_min_ee_to_cube_dist']:.3f} m" if behavior.get("mean_min_ee_to_cube_dist") is not None else "",
            ]

    lines += ["", "## Stall verdict", "STALLED -- see below." if stalled else "Not stalled -- training continues."]

    if stalled:
        lines += [
            "",
            "## Diagnosis (metrics-based, preliminary)",
            "Training was stopped automatically: reward and success rate showed no meaningful "
            "improvement over the analysis window, and policy entropy had already collapsed "
            "early relative to the run's own start -- the combination this project treats as "
            "'stuck', not just normal PPO noise.",
            "",
            "This report is metrics-only. A visual review of the rendered rollout video "
            "(checkpoints/videos in this run directory) is needed to confirm which failure mode "
            "the behavior-analysis fractions above point to before deciding the next fix -- see "
            "the agent's follow-up message/log for that visual pass.",
        ]

    report_path = run_dir / f"analysis_{step}.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path
