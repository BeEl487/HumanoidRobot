# Automated Self-Monitoring RL Training System

Build the reinforcement-learning training system so that training is largely autonomous rather than requiring constant manual monitoring. The system should continuously train the model, record detailed metrics, periodically evaluate the learned behaviour, detect when learning has stalled or degraded, save useful checkpoints, and produce an analysis of what is happening. The goal is to avoid wasting millions of environment steps on a model that is no longer improving.

## 1. Continuous Training and Logging

During training, continuously log important information to a machine-readable file such as `metrics_log.csv`.

Log at regular intervals rather than only at the end of training. The logging interval should be configurable.

The log should contain, where applicable:

* Global training step
* Episode number
* Episode reward
* Episode length
* Success rate
* Rolling average reward
* Policy loss
* Value loss
* Entropy
* Learning rate
* Simulation FPS
* Estimated remaining training time
* End-effector position
* Object position
* Distance between end effector and object
* Distance between object and goal
* Whether the object is currently grasped/attached
* Other task-specific state variables that are useful for diagnosing behaviour
* Timestamp

The logging system must write the CSV header immediately when training begins so that useful data remains available even if the training process crashes or is manually stopped.

The logging system should not rely on temporary internal logger values that may be cleared by the RL framework. Metrics such as FPS should be measured independently when necessary.

## 2. Checkpointing

Automatically save checkpoints throughout training.

Checkpoints should be saved at configurable intervals, for example every 200,000–400,000 environment steps.

At minimum, maintain:

* Regular periodic checkpoints
* The current/latest checkpoint
* The best-performing checkpoint
* A checkpoint captured when training is detected to have stalled
* A final checkpoint when training terminates

Do not define "best" using raw reward alone. For tasks where reward hacking is possible, rank models primarily using actual task performance and learned behaviour, for example:

1. Task success rate
2. Pick/grasp success rate
3. Place/goal success rate
4. Behavioural consistency
5. Raw reward

Keep enough information with each checkpoint to identify exactly which training run and configuration produced it.

## 3. Periodic Automatic Analysis

Every configurable number of training steps, pause normal training long enough to perform an evaluation/analysis cycle.

For example, every 400,000 steps:

1. Read the recent training log.
2. Analyse the latest training window.
3. Compare performance against previous windows.
4. Evaluate the current checkpoint.
5. Run several evaluation episodes.
6. Record complete trajectories.
7. Analyse the model's behaviour.
8. Generate an analysis report.
9. Determine whether training is improving, plateauing, degrading, or behaving abnormally.
10. Continue training or stop if a stall condition has been met.

The analysis window should also be configurable, for example the previous 300,000 steps.

The analysis should calculate trends rather than relying only on individual measurements. Use statistical trends such as least-squares slopes for reward and success rate.

## 4. Behavioural Evaluation

Do not judge the model using reward alone.

At each analysis checkpoint, run multiple evaluation episodes without curriculum modifications and record the full trajectory.

The evaluation should determine things such as:

* Does the agent enter the relevant workspace?
* Does it approach the target?
* How close does it get?
* Does it successfully interact with/grasp the target?
* Does it successfully lift or manipulate the target?
* Does it successfully transport the target?
* Does it reach the final goal?
* Does it repeatedly move toward the same region?
* Does it oscillate?
* Does it become stuck against obstacles?
* Does it repeatedly collide with boundaries?
* Does it avoid the task area entirely?
* Does it demonstrate meaningful progress even when the final task is not yet successful?

Record these behaviours quantitatively where possible.

For example:

```text
entered_workspace_fraction
approached_target_fraction
mean_min_distance_to_target
grasp_success_fraction
lift_success_fraction
transport_success_fraction
goal_success_fraction
oscillation_fraction
collision_stuck_fraction
directional_bias
```

This allows the system to determine *where in the task pipeline the model is failing* instead of simply reporting that the reward is low.

## 5. Detecting Stalled Learning

The system should automatically determine whether training has stopped making meaningful progress.

Do not stop training because of a single bad evaluation.

Instead, analyse multiple indicators over a configurable window.

A stall could be detected when several conditions occur simultaneously, such as:

* Reward improvement is below a minimum percentage.
* Success-rate trend is flat or negative.
* Entropy has collapsed significantly compared with the beginning of training.
* The agent repeatedly visits the same locations.
* The agent consistently fails to approach the target.
* The agent approaches the target but consistently fails at the same stage.
* The agent repeatedly gets stuck against obstacles.
* The model's behaviour has remained effectively unchanged over multiple evaluations.

Use multiple conditions together to reduce false positives.

For example:

```text
stall =
    insufficient_reward_improvement
    AND non_positive_success_trend
    AND exploration_collapse
```

Task-specific behavioural indicators can then provide additional evidence.

## 6. Automatic Stall Response

When a genuine training stall is detected:

1. Save the current model.
2. Save a final evaluation checkpoint.
3. Record the exact training step.
4. Save evaluation trajectories.
5. Generate an analysis report.
6. Save a stall flag such as `STALL_DETECTED.flag`.
7. Save a video/evaluation recording if available.
8. Stop the current training run cleanly.

Do not continue consuming environment steps after the system has determined that the current training configuration is no longer producing useful progress.

The training process should exit in a way that allows an external training manager/agent to detect that the run stopped because of a stall rather than because of a crash.

## 7. Visual Analysis

Metrics should be the first layer of diagnosis, but numerical metrics should not be the only source of truth.

When a run stalls, automatically generate an evaluation video and/or image frames from the stall-point checkpoint.

The monitoring system should make these available for visual inspection.

The visual analysis should answer questions such as:

* What is the robot actually doing?
* Is it physically capable of reaching the target?
* Is it avoiding the workspace?
* Is it repeatedly hitting an obstacle?
* Is it oscillating?
* Is the reward encouraging an unintended behaviour?
* Is the agent making meaningful progress that the numerical metrics fail to capture?

The final diagnosis should combine:

```text
training metrics
+
trajectory analysis
+
task-specific success metrics
+
visual behaviour
```

rather than assuming that reward alone explains the failure.

## 8. Training Run Management

Every training run should have its own directory containing all relevant artifacts.

For example:

```text
runs/
    experiment_001/
        config.yaml
        metrics_log.csv
        analysis_200000.md
        analysis_400000.md
        checkpoint_200000.zip
        checkpoint_400000.zip
        best_model.zip
        final_model.zip
        evaluation/
        videos/
        trajectories/
        experiment.json
```

The configuration used for the run must be saved so the experiment can be reproduced.

The system should also record:

* Experiment ID
* Parent checkpoint
* Starting checkpoint
* Environment version/configuration
* Reward configuration
* Curriculum configuration
* Hyperparameters
* Changes from the previous experiment
* Reason for starting the experiment
* Final result
* Best checkpoint
* Reason training ended

## 9. Continuing From Previous Models

The system should support continuing training from a previous checkpoint.

A new experiment should be able to specify:

```text
--init-checkpoint <path>
```

The system should load the previous model and continue training instead of always starting from random initialization.

Before doing so, automatically verify that the checkpoint is compatible with the current environment, observation space, and action space.

A quick prediction/smoke test should be performed before committing to a long training run.

## 10. Experiment History

Maintain a machine-readable experiment ledger such as:

```text
experiments.json
```

or:

```text
EXPERIMENTS.md
```

Each experiment should contain:

```text
experiment_id
parent_checkpoint
configuration_changes
reward_changes
environment_changes
curriculum_changes
training_steps
best_checkpoint
best_success_rate
best_task_performance
final_success_rate
reason_training_ended
analysis_summary
```

Ideally, this should be generated automatically when a run starts and updated when the run ends rather than requiring manual documentation.

## 11. Automatic Model Selection

When deciding which checkpoint should be used for the next experiment, do not automatically select the checkpoint with the highest reward.

Instead, rank checkpoints according to actual learned behaviour.

A suitable priority could be:

```text
1. Overall task success
2. Successful completion of important intermediate stages
3. Consistency across evaluation episodes
4. Exploration/behaviour quality
5. Reward
```

For example, a model with slightly lower reward but a genuine 60% pick success rate may be preferable to a model with higher reward that has learned to exploit the reward function without completing the task.

## 12. Automatic Improvement Loop

The overall system should operate as an iterative loop:

```text
START
  ↓
Load previous best checkpoint or start new model
  ↓
Validate environment/model compatibility
  ↓
Train
  ↓
Continuously log metrics
  ↓
Save periodic checkpoints
  ↓
Periodic evaluation
  ↓
Analyse metrics + trajectories + behaviour
  ↓
Is the model improving?
  ├── YES → continue training
  │
  └── NO
       ↓
   Has it genuinely stalled?
       ├── NO → continue monitoring
       │
       └── YES
            ↓
       Save stall checkpoint
            ↓
       Generate report/video
            ↓
       Diagnose failure mode
            ↓
       Select best previous checkpoint
            ↓
       Identify targeted change
            ↓
       Start next experiment
```

The key principle is that **each new experiment should have a specific reason for existing**.

For example:

```text
Experiment 12
Parent: Experiment 11 / checkpoint_2400000

Observed failure:
Robot approaches the object but repeatedly fails to grasp it.

Evidence:
- 82% of episodes approach target
- 64% reach grasp distance
- 8% successfully grasp
- reward has plateaued for 500k steps
- trajectory analysis shows repeated lateral oscillation

Change:
Modify grasp reward and reduce oscillatory action behaviour.

Expected effect:
Increase successful grasping without changing the already-learned approach behaviour.

Training strategy:
Continue from Experiment 11 checkpoint rather than restarting.
```

This prevents random hyperparameter experimentation and makes every training run a controlled experiment.

## 13. Training Manager / Autonomous Controller

The final system should have an external training manager responsible for orchestrating the entire process.

The manager should:

1. Launch training.
2. Monitor the process.
3. Detect crashes.
4. Detect normal completion.
5. Detect `STALL_DETECTED.flag`.
6. Read the latest analysis report.
7. Identify the current failure mode.
8. Review the available checkpoints.
9. Select the most useful checkpoint.
10. Apply a targeted experiment change.
11. Record the reason for the change.
12. Start the next training run.
13. Repeat until the task reaches the desired performance threshold.

The manager should never blindly restart training with different random parameters.

Every iteration should be based on evidence from the previous run.

## 14. Success / Termination Criteria

Training should have explicit termination criteria.

For example:

```text
Stop successfully when:

task_success_rate >= target_success_rate
AND
performance remains stable across multiple evaluation windows
AND
behaviour is consistent across randomized environments
```

This prevents the system from continuing to train indefinitely after the model has already reached the desired performance.

Likewise, repeated stalled experiments should trigger a higher-level review instead of endlessly changing parameters.

## 15. Core Design Principle

The training system should behave more like an autonomous scientific experiment than a simple training script.

It should continuously answer:

```text
What is the model doing?
Is it improving?
Where is it failing?
Why is it failing?
Is training still worth continuing?
Which checkpoint is actually useful?
What should be changed next?
Did the change work?
```

The system should preserve enough logs, checkpoints, trajectories, videos, configurations, and experiment history that every decision can be traced back to evidence.

The objective is not simply to train for a large number of steps.

The objective is to **automatically spend training compute where it is producing meaningful improvement, stop when learning has stalled, diagnose the failure mode, and use the best previous model as the starting point for a targeted next experiment.**

## 16. Reference implementation contract (verified against `training/pick_place`)

This section is normative for new humanoid tasks. It records what the reference system actually
implements, why, and what remains to be generalized; it is not a wish list.

### 16.1 Artifact contract

Each run owns a directory under its task's `runs/` directory. Create `checkpoints/`, `videos/`,
`logs/`, `metrics_log.csv`, `manifest.json`, `analysis_<step>.md`, and an experiment record at
run creation. The CSV header is written immediately, so a crash leaves a readable partial log.
Periodic artifacts use the same step in their names: `checkpoints/ckpt_<step>.zip`,
`videos/ckpt_<step>.mp4`, and `analysis_<step>.md`. The manifest entry links checkpoint, video,
timestamp, evaluation metrics, and whether the cycle was final. A final checkpoint is always
created even when the last step is not an evaluation boundary; a stall additionally creates
`STALL_DETECTED.flag` and a stall-point checkpoint/video/report.

The reference run layout currently also has `dashboard.html`, generated after every artifact
cycle. New tasks must either generate an equivalent dashboard or document the replacement in the
run manifest; artifacts must never be discoverable only from console output.

### 16.2 Continuous metrics and their rationale

At configurable `log_freq` (reference: 5,000 steps), record exactly: global step, episode
number/reward/length, rolling 100-episode reward, rolling success rate, policy loss, value loss,
entropy, learning rate, independently measured FPS, ETA seconds, end-effector XYZ, object XYZ,
end-effector-to-object distance, object-to-goal distance, grasp/attachment state, and UTC
timestamp. Task-specific state is added only when it has a diagnostic purpose.

FPS must be calculated from this callback's own wall-clock step deltas. The reference found that
SB3 clears `model.logger.name_to_value` after logger dumps, leaving intermittent blank framework
FPS values. Loss/entropy may still be read when present, but FPS/ETA must not depend on them.

### 16.3 Evaluation, trajectories, and video

At `eval_freq` (reference: 200,000 steps), save a checkpoint, run deterministic curriculum-free
evaluation, record full per-step trajectories, render a matching video, write evaluation metrics,
and refresh the manifest/dashboard. Video overlays must come from the same `info` fields used by
metrics—not a second calculation—and identify at least task step, reward, stage, attachment,
distance-to-object, distance-to-goal, collision/stall state, and task-specific safety signals.

For the source-to-destination cube task, the stages are approach, attach/grasp, lift, transport,
and place. Generic trajectory classification measures workspace entry, target approach, closest
distance, reached-without-grasp, grasped-without-lift, lifted-without-transport, oscillation,
collision-stall, and directional bias. These rates locate the failing stage; reward never replaces
them. Evaluation must disable curriculum shortcuts, otherwise success rates are invalid.

### 16.4 Trend analysis and stalls

At `analysis_freq` (reference: 400,000 steps), analyse the trailing `stall_window_steps`
(reference: 300,000). Fit least-squares trends for rolling reward and success rate; capture loss
standard deviations and entropy versus its early-run baseline. The reference stops only when all
three are true: reward improvement is below 3%, success trend is non-positive, and entropy has
collapsed. It does not stop for one poor checkpoint.

Entropy is signed differential entropy for a Gaussian policy. Do not use an entropy ratio across
zero: the reference falsely reported collapse when entropy had increased from negative to positive.
Use `entropy_now < 0.15` *and* `entropy_now < entropy_start`; the 0.15 floor was calibrated from
a video-confirmed frozen policy. The written report is preliminary: it must point to the matching
video and trajectory behaviour before a targeted next experiment is selected.

### 16.5 Curriculum, experiment selection, and known limits

Curriculum state is explicit and logged. In the reference task, assisted carry/release starts are
annealed by callback updates; evaluation never uses them. Promotion/changes must be evidence-led,
and no continuous reward can be farmed by camping in a state. The reference repeatedly found that
reward fixes should be verified through rendered rollouts, geometry/IK checks, and task-stage
metrics before spending another long run.

Choose parents by final-task success, intermediate-stage success, consistency, behaviour quality,
then reward. Continuation must verify observation/action compatibility and execute a prediction
smoke test. The existing reference restores model/optimizer state but not runtime curriculum
anneal progress—new implementations must persist this state or explicitly record the reset.
The reference experiment ledger is currently manually maintained; new humanoid/RGB-D runs must
write a machine-readable experiment record automatically at start and completion, including parent
checkpoint, configuration snapshot, rationale, metrics, selected best checkpoint, and end reason.

## 17. Bootstrap checklist for a new task

Everything below is what actually got built and used for `pick_place`, generalized so the next
task (e.g. `camera_pick_place`) doesn't have to re-derive it. Treat this as the concrete "what to
implement" checklist; sections 1-16 are the why.

### 17.1 Isolated venv per task family

Give a task with different dependency needs (e.g. a CUDA torch build, or vision libs) its own venv
rather than editing a venv another task depends on (`env_pickplace` was created specifically because
the shared `env_isaaclab` venv has hard pins — numpy<2, gymnasium==1.2.0 — that a careless
`pip install` silently broke). Never upgrade a shared venv's core deps to satisfy one task; clone or
create a new venv instead. Record which venv a task uses at the top of its `AUTOMATED_TRAINING_GUIDE.md`.

### 17.2 Video rendering (`render_checkpoint_video` pattern)

Implement one function that: builds an `eval_mode=True` env (curriculum-free — otherwise the demo
shows an assisted episode, not genuine task performance), creates a `mujoco.Renderer` + `MjvCamera`
with fixed lookat/distance/azimuth/elevation constants, rolls out one deterministic episode, and
calls a `_draw_stats_overlay(frame, step, info, reward)` helper after every step. The overlay must
read from the *same* `info` dict the reward and metrics logger use — never a second, independent
computation — so what's burned into the video pixels can never drift from what actually happened.
Burn overlays into the frame itself (PIL `ImageDraw` on the RGB array) rather than a JS overlay keyed
to playback time, so the video stays correct however/wherever it's played. Save with
`imageio.mimsave(path, frames, fps=control_hz)`; `imageio[pyav]` must be installed in the task's venv
(`pip install "imageio[pyav]"`) or frame reads elsewhere in the pipeline fail with
`OSError: Could not find a backend`.

### 17.3 Interactive live viewer (`watch_<task>.py`)

For actually watching a trained policy run repeatedly with fresh randomization in a real window
(not a rendered video) — build a small script per task using `mujoco.viewer.launch_passive(env.model,
env.data)`, loop `while viewer.is_running()`, call `model.predict(obs, deterministic=True)` each
step, `env.step(action)`, `viewer.sync()`, and `time.sleep(1.0 / control_hz)`. Construct the env with
`eval_mode=True` so curriculum shortcuts never fire and every episode is the genuine full task with
whatever domain randomization `reset()` already performs (e.g. `randomize_cube_in_box`) — no extra
randomization wiring needed if the env already randomizes on reset. Print a running success-rate line
after every episode (`info["success"]` or the task's equivalent terminal-success key — check the env's
actual key name, don't assume). Reference implementation: `simulation/scripts/watch_pick_place.py`
(generalized from the older `watch_policy.py` written for `BinPickingEnv`).

Two operational gotchas hit when first running this live-viewer pattern, worth avoiding next time:
- **Output buffering**: stdout is block-buffered (not line-buffered) when redirected to a log file,
  so per-episode `print()` lines can sit invisible in the buffer for minutes even though the process
  is actively running. Always launch with `python -u` (or `flush=True` on the print) when piping to a
  log file you intend to tail live.
- **Cold-start latency looks like a hang**: `PPO.load()` + `torch`/`mujoco` imports + first CUDA
  context init can take 30-90s with near-zero visible memory growth before the real work starts.
  Before concluding a launched process is stuck, check `wmic process where "ProcessId=<pid>" get
  WorkingSetSize,UserModeTime,KernelModeTime` across two samples — climbing numbers mean it's alive,
  not stuck, even with an empty log.

### 17.4 Cross-run dashboard

Every task should have a `serve_runs.py`-style local HTTP server (`training/serve_runs.py` is the
reference) that discovers `runs/<task>/<run_id>/manifest.json` files and serves an HTML dashboard
comparing runs side by side (success-rate curves, latest videos, latest analysis reports). Regenerate
a per-run `dashboard.html`/manifest entry after every artifact cycle (checkpoint+eval+video+analysis),
not just at the end — a run that's still training should already be inspectable.

### 17.5 Desktop notifications for long unattended runs

`notify_windows(title, message)` in `train_ppo_pick_place.py` fires a native Windows toast via a
backgrounded, hidden PowerShell process using `System.Windows.Forms.NotifyIcon` (no extra
dependency — ships with .NET). Call it after each checkpoint/eval/render cycle so progress is visible
without watching a terminal. Must be best-effort: wrap in try/except and swallow all exceptions, since
a notification failure must never interrupt training.

### 17.6 Reward-shaping guardrails (hard-won, don't relitigate per task)

- Never give a continuous/farmable reward for holding a state (e.g. reward-per-step for staying
  attached, staying idle in a good position). Farmable rewards get discovered and exploited before
  real task completion does. Use one-time milestone bonuses or progress-gated penalties instead.
- Add an explicit idle/stillness penalty (velocity below a threshold for N consecutive steps) gated
  to only the phase where standing still is never correct (e.g. pre-attach) — this was added
  specifically because the policy learned to camp in place otherwise.
- When adding a state-transition action (attach/detach, open/close, etc.), gate the reward on
  *first* transition and add a short debounce (a minimum number of steps before the reverse
  transition is allowed) — otherwise the policy discovers it can rack up unbounded reward by
  chattering the transition back and forth.
- Before trusting a reward-shape theory, verify it with a direct scripted step-by-step trace of an
  adversarial rollout, not just a plausible mechanism story — a stated theory about *why* an exploit
  works can be wrong even when the fix that follows from a wrong theory happens to work; re-verify
  against the actual per-step trace.
- Tune curriculum start-probabilities as a set, not independently — cutting one curriculum branch's
  probability without rebalancing the others can silently starve full-task episode exposure (a fresh
  policy trained on curriculum ratios tuned for continuation runs failed until the full-task episode
  fraction was restored to ~60%).

### 17.7 Entropy management

Fixed `ent_coef` (not 0 — collapses to a frozen policy; not too high — causes runaway/noisy
exploration that never converges) is a per-task tuning pass, not a universal constant — but treat
"policy stopped changing behaviour across evaluations" and "entropy is near/below an absolute floor
*and* has decreased from its run-start value" as the two things to check together. Do not use a
ratio test (`entropy_now / entropy_start`) for a Gaussian policy's differential entropy — it can be
signed and cross zero, producing false positives/negatives. Use an absolute floor plus a
decreased-from-start check instead (reference floor: 0.15, calibrated against a video-confirmed
frozen policy — recalibrate per task, don't reuse the number blindly).

### 17.8 IK/reachability verification before blaming RL

When a policy seems to plateau approaching a pose, check the kinematic feasibility directly before
assuming it's a learning problem: use `ikpy` (reference: `scripts/reachability_check.py`,
`_build_arm_chain`, `_midrange_initial_guess`, `_is_reachable`) to solve or verify whether the target
pose is actually reachable from the arm's chain. This ruled out a kinematic-ceiling theory in one
investigation and produced the correct curriculum pose (`near_dest_pose_rad`) in another.

### 17.9 Diagnostic methodology when success rate is stuck

In priority order, before changing anything: (1) direct scripted checkpoint rollouts (15-30
episodes minimum — a 10-episode eval manifest is too noisy to trust a single read), (2) step-by-step
reward/state tracing to find the exact decision point where behaviour diverges, (3) video frame
extraction (`imageio.v3`, `plugin="pyav"`) at the specific steps identified in (2), (4) IK/physics
checks if geometry is suspect. If five distinct reward-shape fixes in a row produce zero behavioural
change, that is itself diagnostic — it points to a reinforced habit (something curriculum or
initial-state distribution keeps re-teaching) rather than another reward-shape problem; look at
curriculum probabilities and initial-state distributions next, not a sixth reward tweak.

### 17.10 Documentation conventions

Every task directory carries `HANDOFF.md` (current status, how to resume), `AUTOMATED_TRAINING_GUIDE.md`
(task-specific instance of this master doc), `EXPERIMENTS.md` (the machine-readable-ish ledger from
§10), and `TRAINING_LOG.md` (narrative account of every run — what changed, why, what was observed,
verification method used, and a running "lessons learned" section). Update these after *every*
version, not just at milestones — the narrative log is what lets a session resumed after context
loss (or a different session entirely) pick up without re-deriving already-learned lessons.

### 17.11 Windows/git-bash environment gotchas

- Bash tool session cwd can silently reset between calls — chain `cd <dir> && <command>` in one call
  rather than relying on a previous `cd` having stuck.
  A Python process started from a Windows-native interpreter interprets a leading `/c/...` path as
  drive-relative from the *current* drive, not as the git-bash absolute path — it lands under
  `C:\c\...`, not `/c/...`. When a script writes to a hardcoded `/c/...` path, check both locations
  if the expected output isn't where you expect it.
- Destructive-looking output paths (e.g. `C:\tmp_*.mp4`) can hit permission errors — write scratch
  outputs into the session scratchpad directory instead of a bare drive root.
