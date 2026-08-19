# Camera-based pick-place handoff

This folder holds two related but distinct tracks. Don't conflate them:

1. **Real-hardware imitation-learning track** (`WORKFLOW.md`, `prototype_pipeline.py`) — scripted
   grasp pipeline + IL, gated on physical hardware decisions (Phase 0). Still blocked/not started
   for real; see WORKFLOW.md for that plan. Untouched by the sim-RL work below.
2. **Sim RGB-D RL track** (`train_rgbd_pick_place.py`, `rgbd_automation.py`,
   `rgbd_feature_extractor.py`, `sim_env/rgbd_vision_wrapper.py`) — this is the active one as of
   2026-08-11. PPO trained directly in MuJoCo against a rendered head-camera RGB-D feed, no
   privileged cube/destination ground truth in the observation. This section covers that track.

## Sim RGB-D RL: current state (2026-08-11)

**Observation contract**: policy sees `rgb` (3xHxW uint8), `depth` (1xHxW float32, clipped to
`depth_max_m`), joint pos/vel, FK end-effector position, and suction state/command — i.e. only
signals a real robot would actually have. `RGBDVisionWrapper` (sim_env/rgbd_vision_wrapper.py)
strips `cube_pos`/`dest_pos`/etc. from `SuctionPickPlaceEnv`'s observation and adds `rgb`/`depth`
rendered from the same `head_camera` used at deployment (config/camera.yaml). Reward/curriculum/
physics are otherwise the exact `SuctionPickPlaceEnv` from `training/pick_place` — nothing
duplicated there.

**No YOLO yet, deliberately**: for one known cube, direct RGB-D PPO end-to-end is simpler and
trains on exactly the sim camera observation. `rgbd_point_cloud.py` (RGB-D projection +
outlier-filtered centroid) exists as a scripted-perception building block for later. YOLOv8-seg
becomes worth adding once there are multiple object types needing category-based target selection
— its mask would feed the point-cloud module. Don't add it before that need exists.

### rgbd_pp_v1 — what happened and why it's dead

Launched 2026-08-08 ~21:47, single env (`DummyVecEnv`, n_envs=1, no parallelism). Measured ~7-8
fps end to end (CPU-bound software MuJoCo rendering per step — no shared GPU render context). At
that rate, `eval_freq=200000` alone would've taken ~7 hours to produce the *first* checkpoint/video,
and the full `total_timesteps=2000000` run would have taken **~3 days of continuous uptime**.
The process was killed at step 24064/2000000 (1.2%) — log ends cleanly mid-PPO-iteration with no
traceback, `rgbd_pp_v1.error.log` is 0 bytes. Most likely cause: the launching session/machine
didn't stay up continuously (sleep, terminal closed, or session teardown) — **not** a code bug.
Consequence: zero checkpoints, zero videos, zero manifest entries ever got written — the artifact
pipeline itself (`RGBDArtifactCallback` in `rgbd_automation.py`) is correct and already writes to
the right per-run folder (`runs/<run_name>/{checkpoints,videos,trajectories,logs}/`, matching the
pick_place layout exactly) — it just never got to run once.

**Do not resume from rgbd_pp_v1** — no checkpoint exists to resume from.

### Fixes applied → rgbd_pp_v2 (2026-08-11, currently running)

1. **Parallelized rendering** (`train_rgbd_pick_place.py`): added `n_envs` (config-driven,
   `SubprocVecEnv` when >1, mirrors `train_ppo_pick_place.py`'s pattern exactly, including the
   `OMP_NUM_THREADS=1`/`MKL_NUM_THREADS=1`/`OPENBLAS_NUM_THREADS=1` BLAS-contention guard that
   must be set *before* numpy/mujoco import). `config/camera_rgbd_pick_place_train.yaml` now sets
   `n_envs: 6` (machine has 20 logical cores). Measured fps jumped to **~100-250** on relaunch —
   the 2M-step run should now take on the order of hours, not days.
2. **Lowered eval/video/analysis cadence** to match: `eval_freq`/`video_freq` 200000→20000,
   `analysis_freq` 400000→60000, `stall_window_steps` 300000→45000. This is purely so artifacts
   actually appear at a sane real-time cadence at this task's throughput — not a change to the
   automation contract itself (see AUTOMATED_TRAINING_GUIDE_MASTER.md §16-17, still normative).
3. **Versioned run folders, like pick_place's `pp_vN`**: each run gets its own
   `runs/rgbd_pp_vN/` (checkpoints/videos/logs never shared across versions). Current run:
   `runs/rgbd_pp_v2/`. Next run should be `rgbd_pp_v3`, etc. — don't overwrite/reuse a version dir.
4. **Dedicated TensorBoard instance, separate port**: the existing tensorboard on :6006 points at
   `training/pick_place/runs` (state-based task) — that's why camera runs never showed up there,
   it was never pointed at this folder. A second tensorboard instance now runs on **port 6007**,
   `--logdir training/camera_pick_place/runs` — only camera/RGB-D runs appear there. Relaunch with:
   ```
   <python> -m tensorboard.main --logdir simulation/training/camera_pick_place/runs --port 6007
   ```
5. **Launched detached from the interactive session** (via `wmic process call create` wrapping a
   `cmd.exe /c ... > log 2>&1`, not a plain backgrounded shell `&`), specifically because rgbd_pp_v1's
   death looked exactly like "died when the parent session went away." This makes the process
   survive this conversation/session ending — it does **not** make it survive the machine sleeping
   or shutting down. For a multi-hour unattended run to actually finish, keep the machine awake
   (disable sleep / stay plugged in) for the duration.

### How to check on it

- Live logs: `simulation/training/camera_pick_place/runs/rgbd_pp_v3.log` /
  `rgbd_pp_v3.error.log` (external, next to the run folder — same convention as `rgbd_pp_v1.log` was).
- Metrics: `runs/rgbd_pp_v3/metrics_log.csv`, `runs/rgbd_pp_v3/task_logs/rgbd_pick_place.csv`.
- TensorBoard: http://localhost:6007
- Checkpoints/videos/manifest: `runs/rgbd_pp_v3/{checkpoints,videos,manifest.json}` — first
  artifacts expected around step 20000 (few minutes at current fps), not step 200000.
- A stall triggers `runs/rgbd_pp_v3/STALL_DETECTED.flag` per the automation contract.

## rgbd_pp_v12 → rgbd_pp_v13: switched to gSDE + squashed policy (2026-08-20)

User reported the arm getting close to the cube, then settling short and staying away instead of
closing the gap -- traced with the same technique as the earlier saturation bug: stepped
`ckpt_100020.zip` (v12, a genuinely fresh init, not a continuation) to its settled state (closest
approach 7.5cm at step 24, drifted back out and stuck at ~9.7cm from step ~45 onward, suction
commanded on the whole time but never close enough to attach) and inspected
`model.policy.get_distribution(obs).distribution.mean` directly: `shoulder_roll`'s raw mean was
**-2.13**, past the [-1,1] boundary, while the IK-correct angle for that exact cube position maps
to a normalized target of **-0.78** -- comfortably inside the valid range. So the policy has the
right *direction* but overshoots past where it needs to stop; once execution-clipped to -1, there's
no way to fine-tune the last bit of precision needed to actually close the final few cm, so it gets
stuck wherever the clipped combination of joints happens to land.

**This is the same boundary-saturation pathology as v6-v8, recurring on v12's genuinely fresh
init** -- ruling out "just inherited optimizer momentum" as the whole story from the earlier
diagnosis. This task/reward combination has a structural tendency to push the policy toward this
failure, so another restart alone was not going to fix it.

**Real fix this time, not another coefficient/restart cycle**: switched `train_rgbd_pick_place.py`'s
`build_model()` to `use_sde=True` + `policy_kwargs={"squash_output": True}`. SB3's `squash_output`
only takes effect combined with `use_sde` (gSDE, State-Dependent Exploration) -- together they
replace the vanilla hard-clipped `DiagGaussianDistribution` (loss computed on the unclipped
continuous mean, environment only ever executes the clipped value, zero gradient once saturated)
with a tanh-bounded action that has a real, non-zero gradient everywhere, including near the
boundary. Also changes exploration from step-independent Gaussian noise to gSDE's state-dependent
noise (`sde_sample_freq=4`) -- smoother, more physically plausible exploration for continuous robot
control, which is what gSDE was designed for. This is an architecture change (invalidates old
checkpoints), verified with a standalone 200-step build+train smoke test before touching the live
run. `rgbd_pp_v13` launched as a fresh init. Watch whether `ee_to_cube_dist` actually reaches
near-zero and attaches this time, not just whether `std`/entropy metrics look reasonable -- those
were never the actual problem, the clipped-execution gradient dead-zone was.

## rgbd_pp_v9 → v10 → v11 → v12: reverting ent_coef didn't recover the run (2026-08-19/20)

User reported the current checkpoint looked much worse than the previous run's checkpoint at the
same point. `success_rate`/`pick_success_rate` have been **0.00 at every single checkpoint across
the entire v9-v11 lineage** (16 checkpoints in v9, 5 in v10, 4 in v11 -- never once succeeded since
the fresh init), so there's no clean numeric success comparison, but `std` is hard evidence: v11
was at **1.86**, higher than the 1.6 it inherited from v10, despite `ent_coef` having already been
reverted to 0.003 (see the entry below). Plotted the full `std` trend within v11: not a runaway
climb, but a **stuck plateau in the 1.7-1.87 band** for its entire duration, never settling back
toward the ~0.4-0.6 range policies that actually learn something show elsewhere in this project.

Diagnosis: `--init-checkpoint` restores full optimizer state (Adam momentum/variance), not just
network weights. v9 spent its whole run at the wrong (too-high) `ent_coef`, building up optimizer
momentum consistent with high entropy being "correct". Continuing from that checkpoint with the
corrected `ent_coef=0.003` gives the *loss function* a smaller entropy bonus, but the *optimizer's
inherited momentum* was still primed to keep pushing std up/sideways -- v10 and v11 were fighting
that inherited state rather than getting a clean shot at the corrected hyperparameter. This is a
different mechanism from the earlier boundary-saturation issue but the same practical lesson:
**some kinds of policy damage live in the optimizer state, not just the weights, and only a true
fresh init clears both.**

`rgbd_pp_v12` launched as a genuine fresh init (no `--init-checkpoint`) with `ent_coef=0.003`
already in place from the start, so this is the first clean test of that value on this task.
Watch its `std` trend specifically -- if it also drifts high with no continuation-inherited excuse
this time, 0.003 itself (not just "which checkpoint it started from") is the problem, and the next
experiment should look elsewhere (reward scale/clipping, value_loss magnitude also feeding large
policy updates, or the image observation itself making this a harder credit-assignment problem
than pick_place's state observation).

## rgbd_pp_v8 → rgbd_pp_v9: policy action saturation, fresh init required (2026-08-13)

User reported v6/v7/v8 all converging on an identical stuck pose, close to but not touching the
cube, reward flat, no further movement. Root-caused by inspecting the policy's raw internals
directly (not guessing): `model.policy.get_distribution(obs).distribution.mean` at the stuck state
showed shoulder_roll's pre-clip Gaussian mean at **-3.02**, over 3 std devs past the valid [-1,1]
action range -- essentially 100% of stochastic samples clip to the same value, so there's zero
executed-action variance and zero policy-gradient signal on that dimension. IK confirmed the actual
cube position (from the stuck episode, seed=0) is reachable with a solution needing roll=+40 deg --
the *opposite sign* from where the saturated policy's mean points, so it can never discover it via
local gradient exploration.

This is vanilla PPO's known Box-action boundary-saturation pathology: SB3's `DiagGaussianDistribution`
computes the loss on the *unclipped* continuous mean, but the environment only ever executes the
clipped value -- so reward pressure that keeps rewarding "more negative" keeps pushing the mean
further past the boundary with no feedback that it stopped changing anything. Once saturated,
it's baked into network weights and **carries forward through every checkpoint continuation** --
confirmed exactly why v6, v7, v8 all showed the identical pose despite three different environment
changes in between (occlusion penalty, machine-restart resume, camera reposition): they were never
three independent failures, just the same saturated policy continued three times.

**Fix**: no environment/reward change could have fixed this (it's a network-weights problem, not an
environment problem). `rgbd_pp_v9` launched as a **fresh init** (not `--init-checkpoint` -- the
v6-v8 lineage cannot self-recover) with `ent_coef` raised 0.003 -> 0.015 in
`config/camera_rgbd_pick_place_train.yaml` (higher entropy pressure -> higher std -> boundary is
fewer std-devs away -> more samples escape and provide gradient signal; a mitigation against this
recurring, not a complete fix -- entropy only affects std, not mean location). If this saturates
again even at the higher ent_coef, the real fix is a squashed/tanh-bounded policy distribution
instead of vanilla clipped Gaussian, not another ent_coef bump -- worth remembering before spending
another few continuations on it. Also watch for the *opposite* failure: pick_place's own history
(TRAINING_LOG.md) found ent_coef=0.01 caused entropy runaway on a simpler state-only observation --
0.015 on this image-based task is untested territory, monitor early checkpoints for noisy
non-convergence and revert toward 0.003-0.01 if that's what's happening instead.

## rgbd_pp_v7 → rgbd_pp_v8: camera moved to the opposite side of the table (2026-08-13)

User observed the policy oscillating close-to-but-not-touching the cube. Two things checked before
changing anything: (1) **reachability** -- random-restart IK across the full source-box spawn grid
(7x7, including margin edges) converges to ~0 residual everywhere; an earlier "unreachable" reading
at one column was a local-minimum artifact of the default midrange initial guess, not a real
kinematic gap, so the joints were never the problem. (2) **reward conflict** -- the
`camera_occlusion_penalty` added in rgbd_pp_v6 (see pick_place/TRAINING_LOG.md) fights
`close_approach_weight` whenever the only reachable path to the cube crosses the robot-mounted
camera's own sightline, which a policy this early in learning the new penalty hadn't learned to
route around -- exactly the oscillation observed.

**Fix**: moved the camera itself, not just the reward. `config/camera.yaml` now places it on the
far side of the table (`mount_pos: [0.45,-0.12,0.15]`, `yaw_deg: 180`, `pitch_down_deg: 42`),
looking back across both boxes at the robot, instead of on the robot looking forward at the boxes.
Verified before restarting: (a) `build_model.py` rebuilds cleanly, all smoke tests
(`rollout_smoke_test.py`, `contact_smoke_test.py`, `camera_smoke_test.py`, `reachability_check.py`)
still pass unmodified; (b) 100% frustum coverage of the full source-box spawn range (7x7 grid) plus
the destination box center, using the camera's real fovy/pose, not a visual guess; (c) the
occlusion penalty no longer fires for a scripted "approach from the robot's own side" case, since
the cube is now structurally in the foreground for nearly the whole approach instead of the arm
being between camera and cube. Full writeup: `simulation/docs/ASSUMPTIONS.md` "Camera" table
(flagged **Yes, critical** for real-hardware confirmation -- this is no longer "a head camera").
`rgbd_pp_v8` resumed from `rgbd_pp_v7/checkpoints/ckpt_80016.zip` -- note the visual encoder is
seeing a completely different viewing angle now, so treat early-v8 behavior as relearning vision,
not a fair comparison to v4-v7's numbers. `pick_place`'s own training (`pp_v29`) was **not**
restarted for this -- it doesn't use camera pixels at all, so the change is inert for that task.

## rgbd_pp_v6 → rgbd_pp_v7: machine actually shut down, not slept (2026-08-13)

Both `rgbd_pp_v6` and `pick_place`'s `pp_v28`-successor died again overnight -- this time confirmed
via `Get-WinEvent`/`LastBootUpTime` to be a genuine **shutdown** (`winlogon.exe` power-off at
9:31 PM 2026-08-12 on behalf of `NT AUTHORITY\SYSTEM`, machine off ~22h until 7:48 PM 2026-08-13),
not sleep -- the earlier `powercfg` sleep-timeout fix doesn't prevent this. Recurred at similar
evening times on 2026-08-09/10/12 too, consistent with an automatic Windows Update restart (active
hours registry read back inconclusive; a `NoAutoRebootWithLoggedOnUsers` policy fix was attempted
but blocked by the harness's permission classifier as a system-level change -- left as a manual
step for the user, see chat). Resumed `rgbd_pp_v7` from `rgbd_pp_v6/checkpoints/ckpt_40008.zip` and
pick_place's `pp_v29` from `pp_v28/checkpoints/final.zip`. **If this keeps recurring, the real fix
is a login/startup-triggered watchdog task that detects a missing training process and
auto-resumes from the latest checkpoint, rather than relying on the session to notice and restart
manually** -- not yet built, worth doing if this happens again.

## rgbd_pp_v4 → rgbd_pp_v5: machine sleep killed v4 mid-run (2026-08-12)

`rgbd_pp_v4` (the 3rd-person + head-cam POV video fix, see below) died silently overnight at step
253440/2000000 -- not a bug, the machine went to sleep (default Windows "Balanced" plan, 5h AC
timeout) and killed the whole process tree, exactly the failure mode `rgbd_pp_v1` hit originally.
The concurrent `pp_v27` (pick_place task) happened to finish its full budget before the machine
slept and was unaffected. **Fixed at the root**: `powercfg /change standby-timeout-ac 0` (and
hibernate) disables sleep while on AC power -- shouldn't recur as long as the machine stays plugged
in, which is the normal state for a desktop. `rgbd_pp_v5` resumed from `rgbd_pp_v4`'s
`checkpoints/ckpt_240048.zip` (`--init-checkpoint`, not a fresh init -- no action-space change this
time, just recovering lost wall-clock time). If checking on this later and wondering why videos
stopped appearing partway through v4's run, this is why -- check `tasklist` / whether a training
process is even alive before assuming a code problem.

## rgbd_pp_v2 → rgbd_pp_v3: shoulder_yaw DOF restart (2026-08-11)

`rgbd_pp_v2` was superseded, **not** because of a bug in the run itself (it was healthy, ~60 fps,
producing checkpoints/videos on schedule) but because the robot's arm model changed underneath it:
a 4th joint (`shoulder_yaw`, rotation about vertical) was added to `humanoid.urdf` so the arm can
pivot out of the head camera's field of view (user-requested — the arm couldn't rotate out of
frame with only pitch/roll/elbow). Action space grew from 4 (3 arm + suction) to 5 (4 arm +
suction), so `rgbd_pp_v2`'s checkpoints are **not compatible** and there's nothing to resume from —
`rgbd_pp_v3` started fresh. Full rationale, the exact joint spec, and a self-collision bug this
surfaced and fixed (`build_model.py` now excludes `shoulder_yaw_link`↔`upper_arm_link` contact) are
documented in `simulation/docs/ASSUMPTIONS.md` "Arms" table and `docs/ARCHITECTURE.md` "Arms"
section (the real robot's hardware is explicitly **not** changed — this is sim-only). The
state-based `pick_place` task was restarted the same way, as `pp_v27` (superseding `pp_v26`, which
had reached a stable ~60% place-success rate under the old 3-DOF arm — not lost, just superseded by
the arm-model change; see `training/pick_place/TRAINING_LOG.md`).

### Legacy state (superseded by the above, kept for context only)

- A new experiment folder has been created at [simulation/training/camera_pick_place](simulation/training/camera_pick_place)
- The folder includes a basic guide, an experiment ledger, and a runs directory
- A first prototype pipeline now exists for synthetic RGB-D grasping, including:
  - a simple object-mask-to-grasp estimator,
  - a hand-eye transform estimator,
  - a scripted grasp-motion planner,
  - and a grasp-feedback gate driven by Iq telemetry
- The prototype is verified by an automated smoke-test suite

## Immediate next steps

See [WORKFLOW.md](WORKFLOW.md) for the full ordered plan (20 steps across 7 phases, from current
hardware decisions through imitation-learning policy training), with an explicit test to pass at
each step before moving to the next. Summary of the first few steps:

1. Lock in the exact object and workspace setup
2. Use the RealSense D435i as the first camera choice for the head-like mount position
3. Keep the first grasp strategy conservative: a side or slightly elevated approach rather than a direct forward-and-down motion
4. Add a hand-eye calibration step before any camera-to-robot grasp execution
5. Use ODrive Iq telemetry as an in-grasp contact signal, not just a post-hoc verification signal
6. Define the initial perception stack for segmentation and depth alignment with a fallback for short-range depth limits
7. Define the first experiment script or config around this reachability-aware grasp policy
8. Replace the synthetic prototype with a real camera feed and real Iq stream once hardware access is available

## Important constraint

Because the arm appears to block the camera when approaching straight forward and down, the first experiments should favor a side or slightly elevated approach that keeps the object visible and the arm motion feasible under the current joint limits. That is the meaning of the earlier question 5: yes, use a conservative side-approach policy for the first experiments.
