"""Build a self-contained HTML dashboard for an RGB-D camera pick-place training run: a dropdown
listing every checkpoint in manifest.json, plus a view toggle between the 3rd-person external
camera (default -- shows the whole robot/workspace) and the policy's own head-camera POV (exactly
what its RGB channel receives). Videos are embedded as base64 data URIs (no external file
references), matching training/pick_place's dashboard so both tasks work the same way.

Called automatically by training/camera_pick_place/rgbd_automation.py's RGBDArtifactCallback after
every checkpoint cycle, and can also be run standalone to regenerate a run's dashboard.
"""

from __future__ import annotations

import argparse
import base64
import html
import json
import pathlib


def _fmt_step(step: int) -> str:
    if step >= 1000:
        return f"{step / 1000:g}K"
    return str(step)


def _load_manifest(run_dir: pathlib.Path) -> dict:
    manifest_path = run_dir / "manifest.json"
    if not manifest_path.exists():
        return {"checkpoints": [], "total_timesteps_target": 0}
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def _b64_video(run_dir: pathlib.Path, rel_path: str) -> str:
    path = run_dir / rel_path
    if not path.exists():
        return ""
    return f"data:video/mp4;base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"


def generate_dashboard(run_dir: pathlib.Path) -> pathlib.Path:
    manifest = _load_manifest(run_dir)
    checkpoints = sorted(manifest.get("checkpoints", []), key=lambda e: e["step"])
    run_name = run_dir.name
    target = manifest.get("total_timesteps_target", 0)
    last_updated = manifest.get("last_updated", "")

    records = []
    for entry in checkpoints:
        records.append({
            "step": entry["step"],
            "label": _fmt_step(entry["step"]),
            "successRate": entry.get("success_rate", 0.0),
            "pickSuccessRate": entry.get("pick_success_rate", 0.0),
            "meanMaxStage": entry.get("mean_max_stage", 0.0),
            "meanReward": entry.get("mean_reward", 0.0),
            "nEpisodes": entry.get("n_episodes", 0),
            "isFinal": entry.get("final", False),
            "video": _b64_video(run_dir, entry["video"]) if entry.get("video") else "",
            "videoPov": _b64_video(run_dir, entry["video_pov"]) if entry.get("video_pov") else "",
        })

    latest = records[-1] if records else None
    progress_pct = (latest["step"] / target * 100.0) if (latest and target) else 0.0

    records_json = json.dumps(records)
    title = f"RGB-D Pick-Place — {html.escape(run_name)}"

    doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
  :root {{
    --bg: #0a0e14; --panel: #12171f; --panel-2: #0d1219; --border: #212836; --text: #e8ecf2; --muted: #7d879a;
    --accent: #4fa3e3; --accent-dim: #2c6a8a; --good: #34c98f; --warn: #e2a33d; --bad: #ef5b6a;
  }}
  @media (prefers-color-scheme: light) {{
    :root {{ --bg: #f3f4f7; --panel: #ffffff; --panel-2: #eef0f4; --border: #dde1e9; --text: #14171f; --muted: #5b6376;
      --accent: #1568a3; --accent-dim: #2c85c9; --good: #178a5f; --warn: #a86a12; --bad: #c8323f; }}
  }}
  :root[data-theme="dark"] {{ --bg: #0a0e14; --panel: #12171f; --panel-2: #0d1219; --border: #212836; --text: #e8ecf2; --muted: #7d879a;
    --accent: #4fa3e3; --accent-dim: #2c6a8a; --good: #34c98f; --warn: #e2a33d; --bad: #ef5b6a; }}
  :root[data-theme="light"] {{ --bg: #f3f4f7; --panel: #ffffff; --panel-2: #eef0f4; --border: #dde1e9; --text: #14171f; --muted: #5b6376;
    --accent: #1568a3; --accent-dim: #2c85c9; --good: #178a5f; --warn: #a86a12; --bad: #c8323f; }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; background: var(--bg); color: var(--text);
    font: 15px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
  main {{ max-width: 880px; margin: 0 auto; padding: 36px 20px 64px; }}
  h1 {{ font-size: 1.55rem; font-weight: 650; letter-spacing: -0.01em; margin: 0 0 4px; text-wrap: balance; }}
  .sub {{ color: var(--muted); font-size: 0.87rem; margin-bottom: 26px; font-variant-numeric: tabular-nums; }}
  .panel {{ background: var(--panel); border: 1px solid var(--border); border-radius: 10px; padding: 20px; margin-bottom: 18px; }}
  .row {{ display: flex; align-items: center; gap: 14px; flex-wrap: wrap; }}
  select {{ background: var(--panel-2); color: var(--text); border: 1px solid var(--border); border-radius: 7px;
    padding: 8px 12px; font-size: 0.92rem; font-family: ui-monospace, "SF Mono", Consolas, monospace; }}
  select:focus-visible {{ outline: 2px solid var(--accent); outline-offset: 1px; }}
  .progress-track {{ flex: 1; min-width: 160px; height: 6px; border-radius: 3px; background: var(--border); overflow: hidden; }}
  .progress-fill {{ height: 100%; background: var(--accent); transition: width 0.3s ease; }}
  .badge {{ font-size: 0.76rem; font-family: ui-monospace, "SF Mono", Consolas, monospace; padding: 3px 9px;
    border-radius: 999px; border: 1px solid var(--border); color: var(--muted); white-space: nowrap; cursor: default; }}
  .badge.live {{ color: var(--warn); border-color: var(--warn); }}
  .badge.done {{ color: var(--good); border-color: var(--good); }}
  .toggle {{ display: inline-flex; border: 1px solid var(--border); border-radius: 7px; overflow: hidden; }}
  .toggle button {{ background: var(--panel-2); color: var(--muted); border: none; padding: 7px 14px;
    font-size: 0.85rem; font-family: ui-monospace, "SF Mono", Consolas, monospace; cursor: pointer; }}
  .toggle button.active {{ background: var(--accent-dim); color: var(--text); }}
  video {{ width: 100%; display: block; background: #000; border-radius: 8px; }}
  video:focus-visible {{ outline: 2px solid var(--accent); }}
  .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 10px; margin-top: 16px; }}
  .stat {{ background: var(--panel-2); border: 1px solid var(--border); border-radius: 8px; padding: 12px 14px; }}
  .stat .label {{ color: var(--muted); font-size: 0.74rem; text-transform: uppercase; letter-spacing: 0.05em; }}
  .stat .value {{ font-size: 1.4rem; font-weight: 650; margin-top: 3px; font-variant-numeric: tabular-nums;
    font-family: ui-monospace, "SF Mono", Consolas, monospace; }}
  .stat .value.good {{ color: var(--good); }}
  .stat .value.warn {{ color: var(--warn); }}
  footer {{ color: var(--muted); font-size: 0.8rem; margin-top: 24px; }}
  code {{ background: var(--bg); border: 1px solid var(--border); border-radius: 4px; padding: 1px 5px; }}
  .empty {{ color: var(--muted); text-align: center; padding: 40px 0; }}
</style>
</head>
<body>
<main>
  <h1>RGB-D Pick-Place — Run Dashboard</h1>
  <div class="sub">run: <code>{html.escape(run_name)}</code> &middot; head-camera RGB-D + proprioception only, no privileged cube/goal position &middot; last updated: <code>{html.escape(last_updated)}</code></div>

  <div class="panel">
    <div class="row">
      <select id="ckpt-select"></select>
      <div class="toggle">
        <button id="view-ext" class="active">3rd person</button>
        <button id="view-pov">head-cam POV</button>
      </div>
      <span id="status-badge" class="badge"></span>
      <div class="progress-track"><div class="progress-fill" id="progress-fill" style="width:{progress_pct:.1f}%"></div></div>
      <span class="badge" id="progress-label">{progress_pct:.0f}% of {target:,} steps</span>
    </div>
  </div>

  <div class="panel" id="content-panel">
    <div class="empty" id="empty-state">No checkpoints recorded yet — the dashboard will populate after the first evaluation cycle.</div>
    <video id="video" controls muted loop playsinline style="display:none;"></video>
    <div class="stats" id="stats" style="display:none;"></div>
  </div>

  <footer>
    checkpoints dir: <code>{html.escape(run_name)}/checkpoints/</code> &middot;
    videos dir: <code>{html.escape(run_name)}/videos/</code> &middot;
    logs dir: <code>{html.escape(run_name)}/logs/</code> &middot;
    config: <code>config/camera_rgbd_pick_place_train.yaml</code>, <code>config/pick_place_env.yaml</code>
  </footer>
</main>
<script>
const RECORDS = {records_json};
const TARGET_STEPS = {target};

const select = document.getElementById('ckpt-select');
const video = document.getElementById('video');
const stats = document.getElementById('stats');
const emptyState = document.getElementById('empty-state');
const statusBadge = document.getElementById('status-badge');
const viewExtBtn = document.getElementById('view-ext');
const viewPovBtn = document.getElementById('view-pov');
let showPov = false;

function pctClass(v) {{ return v >= 0.5 ? 'good' : (v >= 0.15 ? 'warn' : ''); }}

function render(rec) {{
  if (!rec) {{
    emptyState.style.display = 'block';
    video.style.display = 'none';
    stats.style.display = 'none';
    return;
  }}
  emptyState.style.display = 'none';
  video.style.display = 'block';
  stats.style.display = 'grid';
  const src = showPov ? rec.videoPov : rec.video;
  if (src) video.src = src;
  stats.innerHTML = `
    <div class="stat"><div class="label">Training step</div><div class="value">${{rec.step.toLocaleString()}}</div></div>
    <div class="stat"><div class="label">Place success rate</div><div class="value ${{pctClass(rec.successRate)}}">${{(rec.successRate*100).toFixed(0)}}%</div></div>
    <div class="stat"><div class="label">Pick success rate</div><div class="value ${{pctClass(rec.pickSuccessRate)}}">${{(rec.pickSuccessRate*100).toFixed(0)}}%</div></div>
    <div class="stat"><div class="label">Mean max stage</div><div class="value">${{rec.meanMaxStage.toFixed(1)}}</div></div>
    <div class="stat"><div class="label">Mean reward</div><div class="value">${{rec.meanReward.toFixed(1)}}</div></div>
    <div class="stat"><div class="label">Eval episodes</div><div class="value">${{rec.nEpisodes}}</div></div>
  `;
}}

function currentRecord() {{
  return RECORDS[parseInt(select.value, 10)];
}}

viewExtBtn.addEventListener('click', () => {{
  showPov = false; viewExtBtn.classList.add('active'); viewPovBtn.classList.remove('active');
  render(currentRecord());
}});
viewPovBtn.addEventListener('click', () => {{
  showPov = true; viewPovBtn.classList.add('active'); viewExtBtn.classList.remove('active');
  render(currentRecord());
}});

RECORDS.forEach((rec, i) => {{
  const opt = document.createElement('option');
  opt.value = i;
  opt.textContent = `${{rec.label}} steps` + (rec.isFinal ? ' (final)' : '');
  select.appendChild(opt);
}});

select.addEventListener('change', () => render(currentRecord()));

if (RECORDS.length > 0) {{
  select.value = RECORDS.length - 1;
  render(RECORDS[RECORDS.length - 1]);
  const last = RECORDS[RECORDS.length - 1];
  if (TARGET_STEPS && last.step >= TARGET_STEPS) {{
    statusBadge.textContent = 'training complete';
    statusBadge.className = 'badge done';
  }} else {{
    statusBadge.textContent = 'training in progress';
    statusBadge.className = 'badge live';
  }}
}} else {{
  render(null);
  statusBadge.textContent = 'waiting for first checkpoint';
  statusBadge.className = 'badge';
}}
</script>
</body>
</html>
"""

    out_path = run_dir / "dashboard.html"
    out_path.write_text(doc, encoding="utf-8")
    return out_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=pathlib.Path)
    args = parser.parse_args()
    path = generate_dashboard(args.run_dir)
    print(f"Wrote {path} ({path.stat().st_size / 1e6:.2f} MB)")
