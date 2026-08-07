# MuJoCo RL Simulation — Bin-Picking & Sorting

A MuJoCo digital twin of the robot described in [`../docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md),
built to train reinforcement-learning policies (Gymnasium + Stable-Baselines3, PPO/SAC) for
vision-based bin-picking and sorting.

## Relationship to the real robot's plan

This is an **independent research track**, not a replacement for the real robot's own roadmap.
`docs/ARCHITECTURE.md` §8 already committed to teleoperation + imitation learning for the real
robot's manipulation learning, and explicitly considered and rejected sim-to-real RL for that
hardware. That decision stands. This folder exists to explore whether RL works for grasping in
parallel, kept deliberately separate so it never has to agree with or block the real robot's plan.

Two consequences of that separation, worth keeping in mind while reading the code:
- **No gripper and no camera exist on the real robot yet.** Every gripper and camera spec used here
  is a placeholder engineering estimate, not a confirmed hardware design — see
  [`docs/ASSUMPTIONS.md`](docs/ASSUMPTIONS.md).
- **Most physical dimensions are estimates**, because the real robot has no measured link lengths,
  joint limits, mounting offsets, or masses recorded anywhere yet (see `ARCHITECTURE.md` §9's own
  open-questions checklist). Every one of those estimates is logged with its rationale in
  `docs/ASSUMPTIONS.md`, flagged for confirmation before it informs any real hardware decision.

## Current scope

The robot's torso is modeled as a **rigid, non-actuated mount** — the real robot's 2-motor gimbal is
intentionally **out of scope for this simulation** (see `docs/ASSUMPTIONS.md`), so the two 3-DOF arms
are the only moving part of the robot. This is a permanent scope decision, not a temporary
simplification — it remains a documented sim-to-real gap (a policy trained here assumes a fixed
torso and would need retraining to transfer to a robot whose torso can tilt), but reintroducing the
gimbal is not on this project's roadmap.

## Structure

```
simulation/
  docs/ASSUMPTIONS.md      every estimated numeric value, its rationale, and a hardware-confirm flag
  config/                  all tunable parameters (dimensions, limits, camera, scene, env, training)
  models/urdf/             canonical robot kinematic description (links, joints, limits)
  models/mjcf/             MuJoCo scene: robot + table/bin/objects + actuators/camera/sensors
  scripts/                 model-building + verification scripts, run after every milestone
  sim_env/                 Gymnasium environment (once built — Milestone 6+)
  training/                RL training/eval scripts (once built — Milestone 8+)
```

## Setup

```
python -m venv simulation/.venv
simulation/.venv/Scripts/activate
pip install -r simulation/requirements.txt
```

## Build status

Built iteratively, one milestone at a time, each verified before the next starts. See
`../.claude/plans/i-want-you-to-steady-blanket.md` for the full milestone plan (repo-external —
ask if you need the current status restated here instead).

- [x] Milestone 0 — docs & project scaffolding
- [x] Milestone 1 — static torso only (rigid mount, no gimbal, no arms)
- [x] Milestone 2 — both 3-DOF arms (first moving subsystem)
- [x] Milestone 3 — placeholder parallel-jaw gripper
- [x] Milestone 4 — head-equivalent camera
- [x] Milestone 5 — table + bin + randomized objects
- [x] Milestone 6 — Gymnasium env, state-based observations
- [x] Milestone 7 — vision observations
- [x] Milestone 8 — RL training smoke test (SB3 PPO)

Gimbal reintroduction is **not planned** — see `docs/ASSUMPTIONS.md` meta-assumption M1.

## Watching a trained policy

```
# Interactive, live MuJoCo window:
python scripts/watch_policy.py --checkpoint training/checkpoints/ppo_state_full.zip --profile state

# Render to GIF instead (external view + the robot's own head-camera POV, synced):
python scripts/render_policy_rollout.py --checkpoint training/checkpoints/ppo_state_full.zip \
  --profile state --out docs/policy_rollout.gif --pov-out docs/policy_rollout_pov.gif
```

`ppo_state_full.zip` was the first full 500,000-timestep run beyond Milestone 8's smoke-test
budget. Eleven iterations have followed since (`ppo_state_v2.zip` through `ppo_state_v11.zip`),
chasing an actual successful grasp — reach is now solved (v11), grasping is the open problem.
**[`training/TRAINING_LOG.md`](training/TRAINING_LOG.md) is the readable summary of every
run** — what changed each time, what happened, and the options on the table for what to try
next. `docs/ASSUMPTIONS.md`'s "Task / RL" section has the full engineering detail behind it.

## Automated training dashboard

`train_ppo.py` runs a self-updating progress dashboard by default (every 200,000 steps: saves a
checkpoint, evaluates it, renders a video, updates a JSON manifest) — no need to babysit a run or
manually re-render anything to see how it's doing partway through:

```
python training/train_ppo.py --profile state --timesteps 500000 --run-name v12
# in another terminal, once it's running:
python training/serve_dashboard.py training/runs/v12
# open http://localhost:8000/dashboard.html -- pick any checkpoint from the dropdown,
# it keeps polling and jumps to new checkpoints as they land
```

`--artifact-interval` changes the cadence (0 disables it), `--artifact-episodes` changes how many
eval episodes each update runs. See `training/progress_artifacts.py`'s module docstring for the
directory layout and design notes.

### Viewing every run on this machine, any task, any time

`training/runs_browser.html` + `training/serve_runs.py` is a second, unified dashboard that
browses **every run this machine has ever produced**, across every task, whether or not anything
is training right now -- it just reads whatever `manifest.json`/video files each task's own
training pipeline has already written (currently bin-picking's `training/runs/` and the suction
pick-place task's `training/pick_place/runs/`; a future task's `training/<new_task>/runs/`
appears automatically, no code change needed):

```
python training/serve_runs.py
# open http://localhost:8000/
```

Two tabs: **Current Run** shows whichever run was most recently updated (i.e. is actively
training, if anything is), no selection needed. **All Runs** has a task-type dropdown and a
model/version dropdown listing every checkpoint of every run under that task, newest first --
picking one loads its video(s) and stats. Both tabs poll every 5s.
