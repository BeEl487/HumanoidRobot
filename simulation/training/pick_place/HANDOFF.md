# Handoff: suction pick-place RL task

Written for another Claude agent (or a human) to pick up this work with no prior context. Read
this first, then [`AUTOMATED_TRAINING_GUIDE.md`](AUTOMATED_TRAINING_GUIDE.md) (how the
self-monitoring pipeline works) and [`EXPERIMENTS.md`](EXPERIMENTS.md) (every run's history) as
needed. [`TRAINING_LOG.md`](TRAINING_LOG.md) has the full narrative detail behind every fix
mentioned here in one line.

## What this task is

A MuJoCo + Gymnasium + SB3 PPO task: a single robot arm with a suction-cup end effector picks a
cube up from a source box and places it in a destination box on a table. Independent of, and
built after, an earlier "bin-picking" finger-grasp task in the same repo (`sim_env/bin_picking_env.py`,
its own log at `../TRAINING_LOG.md`) -- don't confuse the two; they have separate scenes, configs,
reward files, and training scripts. This doc is about the suction pick-place task only.

**Current state, as of this handoff:** `pp_v8` (continued from `pp_v7`'s 60%-pick-success
checkpoint) **completed its full 2,000,000-step budget cleanly** -- no stall, no crash. Final:
70% pick success, 0% place success, but the trajectory analysis narrowed the bottleneck sharply:
90% of episodes now reach and grasp the cube, and 80% of those grasp-but-never-lift. That's the
next target. **No further run has been launched -- do not start one without the user's explicit
go-ahead.** Monitoring/analysis/documentation work is fine; launching training is not, until told
otherwise.

## Where things stand right now

- No training process running. `pp_v8`'s log (`train_pp_v8.log`) ends with "Training complete."
- TensorBoard: `python -m tensorboard.main --logdir training/pick_place/runs --port 6006` (covers
  every run under `runs/`) -- check if it's still alive before assuming it needs restarting.
- Cross-run browser: `training/serve_runs.py --port 8200` (built by another session; read-only,
  auto-discovers any `training/<task>/runs/<name>/manifest.json`, no maintenance needed).
- Final state: `runs/pp_v8/checkpoints/final.zip` (2,002,944 steps), `runs/pp_v8/dashboard.html`.
  Check `runs/pp_v8/manifest.json` for the exact final numbers -- don't trust this document's
  numbers as current by the time you're reading it, always re-check the live files.
- Self-monitoring analysis reports: `runs/pp_v8/analysis_{400002,800004,1200006,1600008,2000010}.md`
  -- five ran automatically across the full run, none flagged a stall. Read `analysis_2000010.md`
  (the final one) first -- it has the most specific behavior breakdown to date (see
  `EXPERIMENTS.md`'s pp_v8 row).
- No `runs/pp_v8/STALL_DETECTED.flag` -- this run ended by completing its budget, not by the
  self-monitoring stop mechanism. The "if stalled" procedure below is for the NEXT run, should one
  hit that condition.

## How to check status right now (read-only, always safe)

```bash
cd simulation/training/pick_place
tail -n 20 train_pp_v8.log                          # is it still running / any errors
cat runs/pp_v8/manifest.json                         # latest checkpoint's real metrics
tail -n 10 runs/pp_v8/metrics_log.csv                 # most recent continuous-log rows
ls runs/pp_v8/analysis_*.md                           # which periodic analyses have run
ls runs/pp_v8/STALL_DETECTED.flag 2>/dev/null          # did it stop itself?
```
On Windows, check the process is actually alive with:
```powershell
Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Select ProcessId, CommandLine
```
(look for `train_ppo_pick_place.py --run-name pp_v8` plus several `--multiprocessing-fork` children
-- `n_envs: 6` in `config/train_pick_place_ppo.yaml` means SubprocVecEnv spawns 6 worker processes).

## If pp_v8 has stalled (STALL_DETECTED.flag exists)

1. Read `runs/pp_v8/analysis_<step>.md` for the metrics-based diagnosis and behavior-classification
   breakdown (which failure mode: never enters the box, never approaches the cube, reaches-but-
   no-grasp, grasps-but-no-lift, lifts-but-no-transport, oscillating, stuck-at-collision, lateral
   bias).
2. The report is deliberately metrics-only -- render/inspect the stall-point checkpoint's video
   yourself before concluding anything (you have vision; extract a few frames from
   `runs/pp_v8/videos/ckpt_<step>.mp4` -- e.g. via a short `imageio` script saving PNGs -- and Read
   them). Don't ask the user for the recording; it's already on disk and you can look at it
   directly, same as this whole session's established pattern of watching rollouts before deciding
   a fix.
3. Write an updated diagnosis combining both, propose a concrete fix (reward shaping, curriculum,
   observations, actions, hyperparameters, or env design -- whichever the evidence actually points
   at, not a generic guess), and **add a row to `EXPERIMENTS.md` explaining what's changing, why,
   and which failure mode it targets** before proposing to launch anything.
4. Still don't launch without asking, per the standing instruction above, unless that's since been
   superseded by a more recent user message.

## Key files map

```
simulation/
  sim_env/
    suction_pick_place_env.py   # the Gymnasium env -- action/obs spaces, reward call, info dict,
                                 # suction weld mechanics, stall detection, curriculum, eval_mode
    pick_place_rewards.py       # pure reward function, called from the env
  config/
    pick_place_env.yaml         # task config: episode length, curriculum, suction thresholds,
                                 # ALL reward weights (read this before touching rewards.py)
    pick_place_scene.yaml       # table/box geometry
    train_pick_place_ppo.yaml   # PPO hyperparameters, n_envs, policy_kwargs (network size),
                                 # log_freq/analysis_freq/stall_window_steps
  scripts/
    build_model.py              # MuJoCo model composition (task="suction_pick_place" branch)
    check_pickplace_reach.py    # ikpy reachability gate -- re-run after ANY box/table position
                                 # or size change, before trusting new geometry
    generate_pick_place_dashboard.py  # builds the per-run dashboard.html
  training/pick_place/
    train_ppo_pick_place.py     # the trainer: PeriodicArtifactCallback, evaluate_checkpoint,
                                 # render_checkpoint_video (+ stats overlay), self-monitoring wiring
    self_monitor.py             # CSV logging, trend analysis, stall detection, trajectory
                                 # behavior classification -- see AUTOMATED_TRAINING_GUIDE.md
    TRAINING_LOG.md             # narrative history, one section per run
    EXPERIMENTS.md              # structured ledger, one row per run
    AUTOMATED_TRAINING_GUIDE.md # this pipeline's design doc, spec-point-by-point
    HANDOFF.md                  # this file
    serve_runs.py                # cross-run dashboard browser (not written by this session)
    runs/<run_name>/            # per-run: checkpoints/, videos/, logs/ (TensorBoard),
                                 # manifest.json, dashboard.html, metrics_log.csv, analysis_*.md
```

## Standing conventions (don't relitigate, follow them)

- **Verify before spending compute.** Every geometry/reward/curriculum change in this task's
  history was checked with a real, targeted test (reachability via `ikpy`, a scripted rollout, a
  direct unit test of counter/threshold logic, a rendered frame) before being trusted, not assumed
  correct from reading the diff. Several real bugs were caught exactly this way (a curriculum
  attach-point 1cm above the knockout threshold; a JS template-literal escaping bug that crashed
  every checkpoint cycle; a reward-hacking exploit).
- **Curriculum-free eval only.** `evaluate_checkpoint`/`render_checkpoint_video` always construct
  `SuctionPickPlaceEnv(eval_mode=True)` -- never remove this. Without it, every reported
  success-rate number silently mixes genuine solves with curriculum-assisted (already-attached)
  episodes.
- **Document every iteration, before moving to the next one.** `TRAINING_LOG.md` gets a new section
  per run, `EXPERIMENTS.md` gets a new row, `docs/ASSUMPTIONS.md` gets a condensed cross-reference
  entry. Do this as part of finishing an iteration, not as an afterthought.
- **No continuous farmable reward bonuses.** This project's single most expensive lesson (twice --
  once in the bin-picking task's v2, once in this task's pp_v3/v4). Every reward term is either a
  one-time milestone bonus or tied to a quantity that can't be held fixed for free (progress-gated
  penalties, not raw state-based bonuses). If you add a new reward term, ask whether a policy could
  camp in some state and collect it indefinitely -- if yes, redesign before training on it.
- **Concurrent editing happens.** Other sessions/agents (referred to as "Copilot" in recent commits)
  edit these files too. If a file looks different from what you last read, re-read it -- don't
  assume your edit is the only one in flight. System reminders will tell you when a file changed
  underneath you; treat that as informational, not an error, and build on top of it rather than
  reverting.
- **The user watches rendered rollouts closely and catches real bugs from them** (the claw geometry,
  the wall jamming, the wall tunneling, the bulldozing-the-cube behavior were all caught this way,
  not from metrics alone). Take visual reports as seriously as metrics, and when you have the
  ability to look at the video yourself (you do -- it's an mp4 with an overlay, and you can extract
  frames), do that before theorizing.

## Immediate next steps (as of this handoff)

pp_v8 has already completed -- there's nothing to monitor right now. When the user asks for a next
iteration (their call, not yours to initiate):

1. Read `runs/pp_v8/analysis_2000010.md` and `EXPERIMENTS.md`'s pp_v8 row -- the diagnosis is
   already done: reach and grasp are essentially solved (90%), grasp-without-lift is the isolated
   bottleneck (80% of grasps). A next experiment should target lifting specifically -- candidates
   worth considering (not decided, just the obvious places to look): is `lift_threshold_m` too
   strict relative to how the weld constraint actually behaves under the arm's own motion; is there
   enough reward gradient between "just attached" and "lifted" for the policy to discover the
   motion; is the arm's own vertical reach/control precision the limiting factor near the box floor
   (worth a rendered-video look, not just metrics).
2. Consult `AUTOMATED_TRAINING_GUIDE.md`'s §7 checklist (what's changing / why / which failure mode
   / continue-vs-restart, with justification) before proposing a `pp_v9`. Given pp_v8's real,
   sustained improvement and clean completion, continuing from `runs/pp_v8/checkpoints/final.zip`
   is very likely the right call over a fresh restart -- but state that reasoning explicitly rather
   than assuming it.
3. Add the new row to `EXPERIMENTS.md` (with the rationale filled in) before launching, and only
   launch with the user's explicit go-ahead.
