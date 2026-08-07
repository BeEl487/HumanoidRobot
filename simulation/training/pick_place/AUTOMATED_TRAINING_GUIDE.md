# Automating suction pick-place training: design + operating guide

This documents the self-monitoring training pipeline built for the suction pick-place task
(`sim_env/suction_pick_place_env.py`), against the 7-point spec the user asked for. For each point:
what's implemented, where the code lives, how to operate/extend it, and known gaps. Companion to
[`HANDOFF.md`](HANDOFF.md) (current project state) and [`EXPERIMENTS.md`](EXPERIMENTS.md) (the
experiment ledger this guide's §7 asks for).

**The goal, in the user's words:** "the training system [should] become largely self-monitoring:
it should detect stalled learning, analyze its own performance, and recommend targeted
improvements before wasting millions of additional environment steps."

## 1. Continuous logging -- IMPLEMENTED

`training/pick_place/self_monitor.py`'s `MetricsLogger` writes one CSV row (`<run_dir>/metrics_log.csv`)
every `log_freq` steps (config: `config/train_pick_place_ppo.yaml`, default 5000). Header is written
immediately on construction, so a run killed mid-training still leaves a readable partial log.

Columns (all requested fields, plus a timestamp): `global_step, episode_num, episode_reward,
episode_length, success_rate, avg_reward_100, policy_loss, value_loss, entropy, learning_rate,
fps, eta_seconds, ee_x, ee_y, ee_z, cube_x, cube_y, cube_z, ee_to_cube_dist, cube_to_goal_dist,
is_grasped, timestamp`.

Wired into `PeriodicArtifactCallback._on_step` (`train_ppo_pick_place.py`) -- episode
reward/length/success come from SB3's `Monitor` wrapper's `info["episode"]` (set the step an
episode ends) plus this env's own `info["success"]`; position/distance/grasp fields come directly
from `SuctionPickPlaceEnv.step`'s `info` dict (`ee_pos`, `cube_pos`, `ee_to_cube_dist`,
`carry_dist`, `is_attached` -- added specifically to support this logger); losses/entropy/LR come
from SB3's own `model.logger.name_to_value`; fps is tracked independently (see §5's note on why).

**To inspect a log:** it's a plain CSV, open in Excel/pandas/`self_monitor.analyze_window()`.

## 2. Periodic training analysis -- IMPLEMENTED

`PeriodicArtifactCallback._run_periodic_analysis`, triggered every `analysis_freq` steps (config,
default 400,000) -- does **not** interrupt training at any other cadence. Each run:
1. `self_monitor.analyze_window(csv_path, current_step, stall_window_steps)` -- reads the CSV rows
   in the trailing window (default 300,000 steps) and computes reward/success-rate trend slopes
   (least-squares fit) and whether entropy has collapsed relative to the run's own start.
2. `self_monitor.record_trajectories` + `classify_behavior` -- runs a batch of curriculum-free eval
   episodes recording full trajectories, then the behavior classification (§4).
3. `self_monitor.write_analysis_report` -- writes `<run_dir>/analysis_<step>.md`: metrics trend,
   simulation performance/ETA, behavior analysis, and the stall verdict.

**Real output exists** -- see `runs/pp_v8/analysis_400002.md`, `analysis_800004.md`,
`analysis_1200006.md` for actual examples, not synthetic ones.

## 3. Detect stalled learning -- IMPLEMENTED (partially -- see gaps)

`self_monitor.is_stalled(window)`: flags stalled when, over the analysis window, reward showed
less than `min_relative_improvement` (default 3%) relative change **AND** success-rate trend slope
is non-positive **AND** entropy has collapsed to under 25% of its run-start value. All three
together, not any one alone (each alone is normal PPO behavior at some point in a healthy run).

On stall: `_run_periodic_analysis` captures a final checkpoint/eval/video at the stall point
(`_run_cycle(is_final=True)`), writes `<run_dir>/STALL_DETECTED.flag`, and `_on_step` returns
`False` -- SB3's `model.learn()` stops immediately, no further steps spent.

**Per point 3.4 of the spec** ("if trajectory data alone is insufficient, ask me for a
recording... or yourself visually analyse the video"): the written report is deliberately
metrics-only and says so explicitly -- it does not attempt a final verdict from numbers alone. The
intended workflow (not yet automated end-to-end) is: the agent monitoring the run gets notified
the process stopped, reads `STALL_DETECTED.flag` + the analysis report, then **renders/inspects the
stall-point checkpoint's video frames itself** (it already has vision -- extract a handful of PNG
frames via `imageio`, `Read` them) rather than asking the user for the recording, and writes an
updated diagnosis combining metrics + visual read before proposing the next experiment.

**Gaps vs. the spec's indicator list** (§3's bullets) not yet wired into `is_stalled`, only
available via the separate behavior-analysis report:
- "End effector repeatedly visiting similar locations" -- not implemented as a stall trigger.
  `classify_behavior`'s `oscillating_fraction` is related but measures sign-flips in Y velocity,
  not spatial coverage/revisitation. A proper fix: track EE position variance (or a coarse
  occupancy grid) over the analysis window and flag if it's below a threshold.
- "Cube never being approached or grasped" -- computed (`classify_behavior`'s
  `approached_cube_fraction`) but not currently part of the `is_stalled` boolean itself; it's
  reported alongside the verdict, not folded into it. Easy extension: add
  `approached_cube_fraction < threshold` as an additional stall condition.

## 4. Behavior analysis -- IMPLEMENTED

`self_monitor.record_trajectories` runs N curriculum-free eval episodes recording the full
per-step EE/cube trajectory (not just the aggregate reward `evaluate_checkpoint` computes).
`self_monitor.classify_behavior` answers, per the spec's exact question list:

| Question | Field |
|---|---|
| Is the robot entering the bin/box? | `entered_box_fraction` |
| Does it ever approach the cube? | `approached_cube_fraction`, `mean_min_ee_to_cube_dist` |
| Does it reach but fail to grasp? | `reached_no_grasp_fraction` |
| Does it grasp but fail to lift? | `grasped_no_lift_fraction` |
| Does it lift but fail to transport? | `lifted_no_transport_fraction` |
| Is it oscillating? | `oscillating_fraction` (sign-flip rate in EE Y-velocity) |
| Is it stuck against collisions? | `stuck_at_collision_fraction` (uses the stall flag, §"gentleness"/stall work) |
| Does it always move toward one side? | `lateral_bias` (mean net Y drift across episodes, signed) |

"Avoiding the bin" isn't a separate field -- it's the complement of `entered_box_fraction` (low
value = avoiding).

## 5. Simulation performance (FPS/ETA) -- IMPLEMENTED, with one bug found+fixed

`PeriodicArtifactCallback` tracks fps via its own wall-clock delta (`self._fps_last_time`/
`_fps_last_step`, updated at each `log_freq` tick) rather than reading SB3's
`model.logger.name_to_value.get("time/fps")`.

**Bug found (during pp_v8, fixed for future runs, does not affect pp_v8's already-running
process):** SB3's `Logger.dump()` (`stable_baselines3/common/logger.py`) calls
`self.name_to_value.clear()` immediately after writing each rollout's metrics. Since this
callback's `log_freq` (5000 steps) isn't aligned to SB3's own rollout-boundary logging cadence
(`n_steps * n_envs` = 3072 here), most `_on_step` calls sampled `name_to_value` *after* it had
already been cleared -- confirmed empirically: `fps`/`eta_seconds` were blank in most of pp_v8's
`metrics_log.csv` rows and in its `analysis_*.md` reports (`fps: n/a`). Fixed by tracking fps
independently of SB3's internal logger state. **This fix is in the code but pp_v8 (already
running when it was found) has it in memory as the old, buggy version -- it will take effect
starting with the next launched run, not retroactively.**

`self_monitor.write_analysis_report` uses fps to compute `eta = (total_timesteps - step) / fps`
and reports it in hours/minutes in every periodic analysis. "Whether performance is degrading
over time" isn't a separate computed field yet -- read it by eye from the `fps` column trend in
`metrics_log.csv`, or extend `analyze_window` to fit a trend slope on fps the same way it does for
reward (straightforward, not yet done).

## 6. "Front outside edge of the bin" diagnosis

This was the state at the time the user raised it (before pp_v7/pp_v8's fixes). Per the spec,
basing this on logged metrics + trajectories, not reward values alone:

- **Not insufficient training time alone** -- pp_v6 had run to 1M steps and was still exhibiting
  this.
- **Real contributing causes, since fixed**: (a) the leftover "claw" finger-grasp collision geoms
  (pp_v1→pp_v2) could physically snag the arm on box walls before the suction cup itself ever got
  close -- a motion-constraint/collision-penalty-adjacent cause, not a reward-shaping one; (b) no
  stall/collision penalty distinguished "brushing past" from "rammed and stuck" (pp_v6→pp_v7's
  `stall_penalty`); (c) box wall tunneling could let the cube (and by extension the reward signal
  around it) behave unpredictably near the box boundary (pp_v6→pp_v7's `wall_thickness` fix).
- **`entered_box_fraction`** (§4) is the direct, ongoing instrument for this exact question going
  forward -- pp_v8's own analysis reports already show 100% entry by 1.2M steps (see
  `runs/pp_v8/analysis_1200006.md`), i.e. this specific failure mode looks resolved as of pp_v7/v8,
  though `reached_no_grasp_fraction: 50%` and `oscillating_fraction: 80%` in that same report show
  the frontier moved, not disappeared -- worth reading the actual current report rather than
  assuming this section's diagnosis still holds by the time this doc is read.
- Action scaling / observation deficiencies / exploration failure / curriculum design were all
  considered as candidate causes across pp_v2 through pp_v8's fixes (see `EXPERIMENTS.md`) --
  curriculum design (no curriculum at all, pp_v2→pp_v3) and exploration collapse (pp_v3-v5's
  reward-hacking/overcorrection cycle) turned out to be the dominant ones, not action scaling or
  observation gaps, which were never identified as contributing.

## 7. Iterative model improvement -- IMPLEMENTED (process + tooling, partially manual)

- **`train_ppo_pick_place.py --init-checkpoint <path>`**: `PPO.load(path, env=env, ...)` instead of
  a fresh random init. Only valid between runs sharing the same observation/action space (true for
  pp_v6 onward -- verify with a quick `PPO.load(...).predict()` smoke test against the *current*
  env before trusting it, the way pp_v8's launch did, since a silent shape mismatch would fail
  ugly).
- **`EXPERIMENTS.md`**: the requested per-experiment record (experiment #, parent checkpoint,
  hyperparameter/reward/env/curriculum changes, final metrics, success rate, best checkpoint,
  reason ended). Currently maintained **by hand** -- there is no code that auto-appends a row when
  a run starts/ends. A real automation gap: consider having `PeriodicArtifactCallback` or `train()`
  write/update an `EXPERIMENTS.md` (or a machine-readable `experiments.json` this doc's table is
  generated from) row automatically at launch and at `_on_training_end`.
- **The "explain before launching" step** (what's changing, why it should help, which failure mode
  it targets, continue-vs-restart with justification) is currently a human/agent judgment call made
  in the conversation before each launch (see `EXPERIMENTS.md`'s per-row rationale, written this
  way retroactively) -- not a structured pre-flight check the code enforces. Worth formalizing if
  experiments keep multiplying: e.g. a small script that diffs the current configs against the
  parent experiment's saved configs and requires a `--rationale` string before `train()` will start.
- **"Select the checkpoint with the best exploration/learned-behavior balance, not just highest
  reward"**: not automated. pp_v8's own launch already exercised this judgment manually --
  `ckpt_1200024` was chosen for its genuine 60% pick-success trend, not for whichever checkpoint
  happened to have the single highest logged reward (which, given the reward-hacking history in
  this project, is exactly the metric most likely to mislead). A future automation could rank
  checkpoints by `place_success_rate` first, `pick_success_rate` second, raw reward last, rather
  than leaving this entirely to manual review each time.

## Known limitations / TODO for the next iteration

1. Checkpoint continuation (`--init-checkpoint`) restores network weights/optimizer state only --
   NOT environment/curriculum runtime state (e.g. `start_attached_prob`'s anneal position resets
   to the config's initial value on every run). See `EXPERIMENTS.md`'s note on pp_v8.
2. `is_stalled` doesn't yet fold in "EE revisiting similar locations" or "cube never approached" as
   direct triggers (§3's gaps above) -- currently visible in the report but not decision-driving.
3. `EXPERIMENTS.md` is hand-maintained, not auto-generated (§7 above).
4. No trend-of-fps-over-time degradation check yet (§5 above) -- only the reward/success trend gets
   a fitted slope.
5. The "visually inspect the stall video" step (§3) is a manual agent action when a stall fires, not
   code -- there is no automated frame-extraction-and-vision-pass built into
   `_run_periodic_analysis` itself. Given the agent already has vision, this is a reasonable
   division of labor (code does data crunching, agent does the visual judgment call) rather than a
   gap that needs closing, but it's worth stating explicitly so a future agent doesn't assume the
   stall report already contains a visual verdict.
