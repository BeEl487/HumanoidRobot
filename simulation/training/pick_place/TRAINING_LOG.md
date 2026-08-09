# Training log — suction pick-place PPO iterations

Companion to [`../TRAINING_LOG.md`](../TRAINING_LOG.md) (the bin-picking task's log), same format,
for the separate suction-cup pick-and-place task (`sim_env/suction_pick_place_env.py`): pick a
cube from a source box and place it in a destination box using a single suction-cup gripper
(MuJoCo weld equality constraint), not the finger-grasp bin-picking task. Own scene/config/reward
(`config/pick_place_env.yaml`, `config/pick_place_scene.yaml`, `sim_env/pick_place_rewards.py`),
own trainer (`train_ppo_pick_place.py`), own dashboard pipeline
(`scripts/generate_pick_place_dashboard.py`) — see [`training/serve_runs.py`](../serve_runs.py)
for a live cross-run view of both tasks together.

All runs: PPO (Stable-Baselines3), `MultiInputPolicy`, 2,000,000-timestep budget, checkpoint +
eval (10 episodes) + video every 200,000 steps. `pick_success_rate` = attached the object at least
once (`info["attached"]`); `place_success_rate`/`success_rate` = the actual terminal goal, placed
in the destination box (`info["success"]`) — same diagnostic split bin-picking's
contact_rate/grasp_rate has provided throughout that task's log.

## Summary

| Run | Change from previous | Reward @ 200k | Pick success @ 200k | Place success | Status |
|---|---|---|---|---|---|
| pp_v1 | first attempt, initial scene/reward | −56.25 | 0% | 0% | stopped at 200k |
| pp_v2 | claw geometry fix + box reachability fix | −11.91 | 40% | 0% | stopped at 400k (start-attached curriculum needed) |
| pp_v3/pp_v4 | + start-attached curriculum, continuous lift_bonus_weight (**reward-hacking exploit**) | +135 → +290 (inflated) | ~30% | 0% | stopped -- reward not trustworthy |
| pp_v5 | + exploit fix (one-time lift_bonus, progress-gated idle penalty) | −142.72 (realistic) | 30% | 0% | stopped -- suction avoidance overcorrection |
| pp_v6 | + curriculum-free eval, softened after-lift penalties, annealed curriculum | −69.2 → −49.2 (200k→400k, clean numbers) | 20% | 0% | stopped -- arm jamming/wall tunneling found in rollout |
| pp_v7 | + stall penalty, thicker box walls (tunneling fix), 128x128 network, synced video overlay | −213 → +44 → −60 (200k→600k→1.2M, noisy but trending up) | 0% → **60%** (200k→1.2M) | 0% | stopped at 1.2M -- continued into pp_v8, not discarded |
| pp_v8 | + self-monitoring pipeline, 600-step episodes, cube-disturbance ("gentleness") penalty, **continued from pp_v7's 1.2M weights** (below) | −66.7 | 70% | 0% (one 10% blip at 200k) | stopped at 1.8M -- entropy collapsed to near-zero, policy froze; continued into pp_v9 |
| pp_v9 | + ent_coef 0.0→0.01, stronger pre-lift idle penalty, GPU/throughput tuning, **continued from pp_v8's 1.8M weights** (below) | +282.0 (inflated) | 60%→80% | 0% | stopped ~400k -- **attach-chatter reward exploit** (attach_bonus unconditional), discarded, fixed into pp_v10 |
| pp_v10 | + attach_bonus one-time gate, attach/detach debounce, **continued from pp_v8's clean 1.8M weights** | −172→−115 (realistic) | 40%→60% | 0% | stopped 800k by a **false-positive stall** (self_monitor entropy-ratio bug, fixed); continued (not restarted) into pp_v11 |
| pp_v11 | self_monitor entropy fix now live, no other changes, **continued from pp_v10's 800k weights** | −108.7→−66.6 (noisy, no clear trend) | 30%→50% (below pp_v10's peak 60%) | 0% | stopped ~1M by user -- **entropy/std runaway** (0.23→0.82 across the whole v9→v10→v11 lineage), policy too noisy to close final attach distance; ent_coef re-tuned, restarted **fresh (not continued)** into pp_v12 |
| pp_v12 | ent_coef 0.01→0.003 (fix runaway std), **fresh random init** (not continued -- testing whether the v8→v11 lineage's habits are worth keeping) | −439.8→−164.3 (noisy, no clean trend) | 0-30% (mostly ~10%, never matched pp_v10's 60%) | 0% | stopped by user at 1.4M -- fresh init strictly underperformed continuation over this many steps, see below |
| pp_v13 | back to **continuing from pp_v10's clean checkpoint** (pre-runaway, std≈0.455, 60% pick, no exploit) with the corrected `ent_coef: 0.003` | −119→−102 (plateaued 600k-1.6M, boxed in this band) | 20-50% (oscillating, no trend) | 0% | stopped by user at 1.6M -- **std finally stable** (8 straight checkpoints, 0.44-0.472), but the underlying pick/place plateau didn't move; continued into pp_v14 with the idle penalty |
| pp_v14 | + `idle_penalty` (new), **continued from pp_v13's 1.6M weights** | −237→−115 improving then reversing (200k-1.6M) | 20% flat for 6 straight checkpoints (worse than pp_v13's 20-50% range) | 0% | froze-behavior confirmed fixed (video: idle:False at 1.4M vs idle:True at 600k) but pick plateau didn't break, arguably worse; continued into pp_v15 with a steeper close-approach reward gradient |
| pp_v15 | + `close_approach_weight`/`close_approach_range_m` (new), **continued from pp_v14's 1.8M weights** | −290→−206 (noisy, no clean trend) | 30-50% (best-sustained pick average of any run) | 0% | **completed its full 2M budget** (first run to do so, not stopped early) -- pick improved on average vs pp_v14 but still plateaued, place never moved; continued into pp_v16 with a carry→release curriculum stage |
| pp_v16 | + `start_carrying_prob` curriculum stage, **continued from pp_v15's final 2M weights** | −258→−200 (noisy) | 20-40% | 0% (7 straight checkpoints) | curriculum-only diagnostic showed 90% release success when starting already-carrying, but real episodes never reached that state -- root cause found: attach succeeds early with 500+ steps left, but height caps at 0.022-0.040m, never crossing lift_threshold_m 0.05; continued into pp_v17 with a height-progress penalty |
| pp_v17 | + `lift_progress_penalty` (new), **continued from pp_v16's 1.4M weights** | −280→−58 (noisy) | 20-50% | 0% | fix verified firing correctly but max cube height never moved (0.02-0.04m at every checkpoint, 200k-1.4M) -- direct trace showed why (see below); continued into pp_v18 with a much larger premature-release penalty |
| pp_v18 | `premature_release_penalty` −3.0→−10.0, **continued from pp_v17's 1.4M weights** | −249→−67 (noisy) | 30-40% | 0% | height ceiling still unmoved after 800k (0.019-0.041m); IK-verified reachability rules out a kinematic ceiling; trace found the real competing incentive -- continued into pp_v19 with `carry_distance_weight` cut ~85% pre-lift |
| pp_v19 | `carry_distance_weight` −2.0→−0.3 pre-lift, **continued from pp_v18's 800k weights** | −227→−240 (flat) | 20% flat (3 checkpoints) | 0% | height ceiling STILL unmoved (0.021-0.043m) after 3 consecutive fixes/~3.6M cumulative steps -- stopped at 800k, pivoted to a fresh-init test (all pp_v13-v19 fixes combined from step 0) rather than a 4th continuation-lineage tweak |
| pp_v20 | **fresh random init**, all pp_v13-v19 fixes combined from step 0 | −715→−180 (improving, but from a deep hole) | 0% flat for 7 straight checkpoints (worse than pp_v12's own fresh-init timeline) | 0% | stopped at 1.4M -- second confirmed case of fresh-init clearly underperforming continuation; likely explained by only 10% of episodes being full-task-from-scratch under the current curriculum (vs. 40% when pp_v12 ran) -- see below |
| pp_v21 | no config changes, **continued from pp_v19's 800k weights** (reverting the fresh-init detour) | −252→−232 (flat) | 20-30% | 0% | height ceiling STILL unmoved (0.018-0.041m) after 600k -- physics/actuator/mass checks all ruled out a physical ceiling; stopped, pivoted to a rebalanced-curriculum fresh-init test |
| **pp_v22** | **fresh random init**, curriculum rebalanced for ~60% full-task exposure (see below) | pending | pending | pending | running |

## pp_v1 — first attempt

Initial suction pick-place setup: cube in a source box, suction cup attaches via a MuJoCo weld
constraint, goal is placing it in a destination box. First and only checkpoint (200k) showed
**0% pick success** — the gripper never attached to the object at all in any of the 10 eval
episodes — and reward well underwater (−56.25). Training was stopped at this point rather than run
to the full 2M budget once the underlying cause below was found by watching the rollout.

Checkpoint: `checkpoints/ckpt_200000.zip`

## pp_v2 — claw geometry + box reachability fixes

**Two problems found, both fixed before spending more compute:**

1. **Leftover claw geometry.** The gripper still had finger-grasp collision geoms (5cm prongs
   extending past the gripper base) left over from being adapted from the bin-picking task's
   finger gripper — these were catching on the boxes/table before the suction cup itself could
   ever reach the object, plausibly explaining pp_v1's 0% pick rate outright. Shrunk to near-zero
   size, collision-disabled, and made invisible. Verified fixed with a deliberate drive-into-the-
   wall test that would previously have snagged on these prongs: 0 finger-vs-furniture contacts
   after the fix.
2. **Box placement vs. reachability.** Widening the boxes 3x in Y (to comfortably fit the object
   with the new, smaller gripper footprint) would have overlapped the two boxes at their old
   centers and pushed the source box out of the arm's reach entirely if left uncorrected. Re-ran
   IK reachability checking — now a permanent gate, `check_pickplace_reach.py`, the same
   "verify with real IK before trusting a geometry change" discipline that caught bin-picking's
   torso self-collision bug (see `../TRAINING_LOG.md`'s v11 entry) — and relocated the boxes to
   source (0.16, 0.02) / destination (0.16, −0.26), all 4 corners of both boxes confirmed
   reachable, table widened to fit both.

**Result so far:** a real jump at 200k — pick success 0% → **40%**, reward −56.25 → **−11.91**.
At 400k it dipped (pick success 20%, reward −61.58) — reported as-is rather than smoothed over,
consistent with this being read as normal PPO non-monotonicity (the same pattern seen repeatedly
in the bin-picking log, e.g. v11's 200k→300k dip) rather than evidence the fix stopped working,
though that read isn't independently confirmed yet the way bin-picking's dip-then-recovery was.
Still running toward the full 2,000,000-step budget. Place success (the actual terminal goal, not
just picking up the object) is still 0% at both checkpoints so far.

Checkpoint (final, stopped here): `checkpoints/ckpt_400000.zip`. `mean_episode_length` was pinned
at the full 300-step timeout across every eval episode at both checkpoints -- no successes, no
knockouts, ever. Watching the rendered rollout: the policy attaches, then holds position for the
rest of the episode. It isn't a run-length cap -- it's that this task has no curriculum at all
(full-difficulty cube spawn from step 1) and PPO's action std was already collapsing (~0.5 by
200k) before the full 4-stage chain (approach → attach → carry → release) could plausibly be
stumbled into by chance. Stopped here rather than continuing to spend compute on a plateau with a
known, fixable cause.

## pp_v3 — start-attached curriculum

**Fix** (`config/pick_place_env.yaml`'s `curriculum` block, `SuctionPickPlaceEnv.reset`): half of
episodes (`start_attached_prob: 0.5`) now skip the approach+attach stage entirely — the arm snaps
to a verified mid-carry pose and the cube is welded on immediately, so the episode goes straight to
practicing carry+release. The other half still run the full task from scratch, so the
already-learned attach skill keeps getting reinforced rather than forgotten. Same root cause,
same style of fix, as the bin-picking task's own v5 curriculum.

**Bug caught before spending compute on it:** the first version of this curriculum reused
`ready_pose_rad` as the attach point, but that pose's own EE sits at world Z=0.740 — only 1cm
above the episode's knockout threshold (`table_top(0.78) − table_edge_margin_m(0.05) = 0.73`) and
off to the side, not actually over the table. Curriculum episodes were failing in 1-2 steps
regardless of policy behavior — caught by running a random-action sanity rollout and noticing
curriculum episodes terminating almost instantly, not by assuming the config change was correct.
Fixed with a purpose-solved `mid_carry_pose_rad`: `ikpy` against `humanoid.urdf` for world
`(0.16, -0.12, 0.85)` (the Y-midpoint between the two boxes, well above the table) — 0.0 residual,
all 3 joints within range. Re-ran the random-action check after the fix: found a genuine success
(17 steps, +22 reward) in 1 of 4 curriculum episodes, confirming placement is now reachable by
exploration alone, not merely theoretically possible.

**pp_v3**: relaunched with the curriculum, same PPO budget/hyperparameters as pp_v1/pp_v2.
`check_env` re-verified passing after the env change. TensorBoard restarted against
`training/pick_place/runs`. Live dashboard: `training/serve_runs.py` → All Runs → task
`pick_place` → `pp_v3`.

**Outcome: a real reward-hacking exploit, caught before it corrupted more compute.** Reward
climbed 135 → 290 between checkpoints while `place_success_rate` stayed 0.0 and
`mean_episode_length` was pinned at the full 300-step timeout -- no terminations at all. A
deterministic rollout of the 400k checkpoint confirmed it: the arm drove to a fixed point and sat
there for the rest of the episode, collecting reward the whole time. Root cause: `lift_bonus_weight`
was continuous (paid every step while attached, scaled by height), and the raw
`carry_distance_weight * carry_dist` term wasn't steep enough on its own to outweigh it near the
curriculum's mid-carry start -- so the policy learned to attach once (via the curriculum) and then
just hold still. Same shape of bug as the bin-picking task's own v2.

## pp_v4 → pp_v5: exploit fix (one-time lift bonus, progress-gated idle penalty)

Fix: `lift_bonus_weight` set to 0 (comment in the reward config: "continuous height reward is
disabled to avoid attach-and-hold exploits"), replaced with a one-time `lift_bonus` +
`stage_transition_bonus`, plus `attached_idle_penalty`/`attached_idle_penalty_after_lift` that only
fire when the cube-to-destination distance fails to improve by at least `carry_progress_tolerance_m`
in a step -- a progress-gated penalty instead of a state-based bonus, closing the exploit
structurally rather than patching the one instance found.

**pp_v5**: reward back to a realistic, non-inflated baseline (−142.72 at 200k) -- exploit
confirmed closed. But `mean_suction_cmd_rate: 0.006` -- the policy now commands suction ON only
0.6% of the time, essentially avoiding the whole interaction. `pick_success_rate` unchanged at 30%.

## pp_v5 → pp_v6: curriculum-free eval, softened after-lift penalties, annealed curriculum

Two more problems found before relaunching again:

1. **Overcorrection.** The math: with `carry_distance_weight_after_lift: -12.0`/m and a typical
   post-attach carry distance of ~0.14-0.28m, simply BEING far from the destination (unavoidable
   right after attaching, before any carry skill exists) cost roughly -1 to -3/step attached, vs.
   only ~-0.16/step for just hovering unattached near the cube -- attaching was a losing bet
   regardless of policy quality, not because of the (correct) progress-gated idle penalty but
   because of the raw distance term stacked on top of it. Fix: `carry_distance_weight`/
   `carry_distance_weight_after_lift` cut roughly 4x (-8/-12 → -2/-3), `attach_bonus`/`lift_bonus`
   raised (8/8 → 12/10), so attempting attach isn't punished before the policy has had a chance to
   learn to carry, while the idle-progress penalties (unchanged) stay the actual anti-camping
   mechanism.
2. **Eval/video methodology bug.** `evaluate_checkpoint`/`render_checkpoint_video`
   (`train_ppo_pick_place.py`) built a plain `SuctionPickPlaceEnv()`, which still had
   `curriculum.enabled: true` -- so roughly half of every eval run's episodes (and the demo video,
   depending on its seed) started pre-attached via the curriculum shortcut. Every
   pick/place-success number reported since the curriculum was added was a mix of "genuinely
   solved it" and "started already past the hard part," not a clean read of real competence --
   also the likely explanation for consecutive checkpoints' videos looking inconsistent (different
   fixed seeds landing on different curriculum branches). Fixed with a new `eval_mode` constructor
   flag on `SuctionPickPlaceEnv` that forces the curriculum off; training keeps the curriculum,
   only eval/video go curriculum-free now.

Also annealed `curriculum.start_attached_prob` (`0.6 → 0.15` linearly over the run, via
`PeriodicArtifactCallback.ANNEAL_FREQ`-step `env_method` calls) instead of holding it fixed for
the whole 2M-step budget -- high early (what unblocked pp_v2's plateau) but decaying so the policy
is pushed back toward solving the full task from scratch as it improves.

**pp_v6**: relaunched with all three fixes. `check_env` and a direct start-attached-fraction check
(`eval_mode=True` → 0%, training mode → ~53% at prob=0.6, ~17% after a manual
`set_start_attached_prob(0.15)` call) both verified before launch. TensorBoard restarted against
`training/pick_place/runs`. Live dashboard: `training/serve_runs.py` → All Runs → task
`pick_place` → `pp_v6`.

**Outcome: exactly the recovery hoped for, no exploit reopened.** `mean_suction_cmd_rate` recovered
from pp_v5's 0.006 floor to 0.749 (200k) and 0.977 (400k); `mean_reward` improved realistically
(−69.2 → −49.2), no positive spike. `pick_success_rate` 0.2 at both checkpoints -- the first
genuinely clean number (curriculum-free eval), lower than pp_v2's curriculum-contaminated 40% as
expected. `place_success_rate` still 0%.

Watching the rendered rollout: the arm goes up and over the box, comes down near the center, then
drifts sideways until it hits the box wall and stays jammed there for the rest of the episode. On
the 200k checkpoint, the cube was pushed hard enough to pass clean through a box wall instead of
bouncing off it. Stopped here rather than run to completion with two known, fixable problems.

## pp_v6 → pp_v7: stall penalty, wall-tunneling fix, bigger network, synced video overlay

Four changes, addressing the two problems above plus two more the user asked to try:

1. **Stall penalty.** `collision_penalty` alone (a flat -0.02/step, raised to -0.05) didn't
   distinguish a glancing, still-moving contact from getting rammed and stuck. Added
   `SuctionPickPlaceEnv._update_stall_counter`: consecutive steps of arm-furniture collision AND
   mean |qvel| across the 3 arm joints below `stall_velocity_threshold_rad_s`, sustained for
   `stall_steps_threshold` (10) steps, before `stall_penalty: -0.6`/step kicks in -- same shape as
   the bin-picking task's `reward.stuck` mechanism. Verified the counter logic directly (fires
   exactly at the threshold, resets when collision or motion resumes) rather than relying on a
   scripted rollout finding a "clean" sustained collision by luck.
2. **Wall-tunneling fix.** `boxes.wall_thickness: 0.004 → 0.01` (`config/pick_place_scene.yaml`).
   At `physics_hz=500` (0.002s/substep), MuJoCo's discrete collision detection can miss a contact
   entirely once relative velocity exceeds roughly wall_thickness/timestep -- 0.004/0.002 = 2 m/s
   at the old thickness, comfortably within what a hard push could produce. This is a MuJoCo
   geometry/physics fix, not a reward change. Re-ran `check_pickplace_reach.py` after (still all 8
   corners reachable -- the floor height shift from the thicker walls is only ~6mm).
3. **Bigger network.** `config/train_pick_place_ppo.yaml`: `policy_kwargs.net_arch` set to
   `{pi: [128,128], vf: [128,128]}` (was SB3's default 64x64, untried on this task). This task
   chains 4 sequential stages through one flat observation -- plausible capacity is now a real
   constraint, and `n_envs: 6` (SubprocVecEnv, already added) gives enough throughput to make a
   bigger net worth the extra wall-clock cost per step.
4. **Synced video stats overlay.** `render_checkpoint_video` now burns a small telemetry panel
   into every frame (step, attached, suction command, stage, EE-to-cube distance, cube-to-
   destination distance, cube height, collision/stall flags, reward) via Pillow, reading from the
   exact same `info` dict the reward and dashboard already use -- not a separate computation, and
   baked directly into the video rather than a JS overlay keyed to playback time, so it can't drift
   out of sync however the video is played. Required expanding `SuctionPickPlaceEnv.step`'s `info`
   dict with the underlying fields (`is_arm_collision`, `is_stalled`, `ee_to_cube_dist`,
   `carry_dist`, `cube_height`).

**pp_v7**: relaunched with all four changes together (`check_pickplace_reach.py`, `check_env`, the
stall-counter unit test, and a rendered test video with the overlay all verified passing first).
TensorBoard restarted against `training/pick_place/runs`. Live dashboard:
`training/serve_runs.py` → All Runs → task `pick_place` → `pp_v7`.

**Outcome: a real, sustained improvement -- the best pick-success trend of any run so far.**
`pick_success_rate` climbed 0% (200k) → 20% (400k) → 40% (600k) → 50% (800k) → **60%** (1.2M),
`mean_reward` noisy but trending up (−213 → +44 at 600k → −60 at 1.2M -- non-monotonic, same normal
PPO pattern seen throughout this project's history, not a regression signal on its own).
`place_success_rate` still 0% at every checkpoint -- attach is now working well, carry-to-place is
the clearly isolated remaining frontier, similar to how the bin-picking task's own v11 isolated
grasping after solving reach. Not stopped for a problem this time -- paused only to fold in the
next round of user-requested pipeline/reward work below, and **continued (see pp_v8) rather than
retrained from scratch**, since letting this trend keep compounding was clearly worth more than a
clean restart.

## pp_v7 → pp_v8: self-monitoring pipeline, longer episodes, gentleness penalty, checkpoint continuation

Four changes:

1. **Self-monitoring pipeline** (`training/pick_place/self_monitor.py`, new module):
   - **Continuous CSV log** (`metrics_log.csv` in the run dir, one row every `log_freq` steps):
     global step, episode number, episode reward/length, rolling success rate, rolling avg reward,
     policy/value loss, entropy, learning rate, fps, ETA, EE/cube position, EE-to-cube and
     cube-to-goal distance, grasped flag -- survives an early-terminated run, unlike TensorBoard's
     event files which need the TB UI running to inspect.
   - **Periodic analysis every `analysis_freq` (400,000) steps** -- deliberately infrequent, does
     not interrupt training in between, per request. Reads the CSV, computes reward/success-rate
     trend slopes and whether entropy has collapsed early relative to the run's own start, and
     writes a markdown report (`analysis_<step>.md`) with the metrics trend, simulation
     performance/ETA, and a trajectory-based behavior analysis (below).
   - **Stalled-learning detection**: flat/non-improving reward+success over the last
     `stall_window_steps` (300,000) AND early-collapsed entropy, together -- either alone is normal
     PPO behavior at some point in a run, both sustained together is the "stuck" signature. If
     triggered, the callback captures a final checkpoint/eval/video at the stall point, writes a
     `STALL_DETECTED.flag`, and returns `False` from `_on_step` to stop `model.learn()` early --
     no more budget spent on a plateau with a diagnosable cause, matching how every prior stall in
     this log (pp_v2, pp_v5, pp_v6) was actually handled by hand.
   - **Trajectory-based behavior classification** (`record_trajectories` + `classify_behavior`):
     runs a batch of curriculum-free eval episodes recording the FULL per-step EE/cube trajectory
     (not just the aggregate reward), then answers automatically what watching a rollout by hand
     has answered all session -- does it enter the box at all, does it approach the cube, does it
     reach without grasping, grasp without lifting, lift without transporting, oscillate, get
     stuck at a collision, or show a lateral bias toward one side.
   - When a stall is detected, the callback's own report is metrics-only by design -- it explicitly
     flags that a visual pass over the rendered video is still needed to confirm which behavior
     classification actually explains the plateau before deciding the next fix, which the agent
     does directly (rendering + inspecting frames) rather than asking the user for the recording.
2. **Episode length 300 → 600 steps** (`config/pick_place_env.yaml`'s `episode_max_steps`, by
   request) -- pp_v6/v7's rollouts showed a large fraction of the episode spent just getting into
   the box before ever reaching the cube; more budget per episode gives the full 4-stage chain more
   room before truncation cuts it off.
3. **Cube-disturbance ("gentleness") penalty.** User's direct observation: the policy touches the
   cube, pushes it down/away instead of gripping it, and keeps chasing it even as it shoves it out
   of reach -- nothing in the reward previously distinguished a careful approach from bulldozing
   (EE-to-cube distance can even look like "progress" mid-shove). Added: while touching but NOT
   attached, if cube speed exceeds `disturbance_velocity_threshold_m_s`, a continuous
   `cube_disturbance_weight` penalty scales with how hard it's being pushed. Only applies pre-attach
   -- once attached, cube velocity is legitimate carry motion. Also added to the video overlay for
   visibility.
4. **Checkpoint continuation** (`train_ppo_pick_place.py --init-checkpoint`): `PPO.load(path,
   env=env, ...)` instead of a fresh random init when a checkpoint path is given -- the policy
   architecture is restored from the checkpoint itself, so this only makes sense between runs that
   share the same observation/action space (true for pp_v6 onward). Verified loading pp_v7's final
   checkpoint against the current env before using it for real.

**pp_v8**: launched **continuing from pp_v7's ckpt_1200024.zip** (its strongest checkpoint, 60%
pick success) rather than a fresh random init -- pp_v7 was showing a real, sustained improvement
trend when the next round of requested changes arrived, and restarting from scratch would have
thrown that away for no reason (all the pp_v7 changes are config/reward-level, not
observation/action-space changes, so the checkpoint loads cleanly). `check_env`, the full
self-monitoring pipeline (logger, trend analysis, stall detection, behavior classification), and
checkpoint continuation were all verified working in isolation before launch. TensorBoard restarted
against `training/pick_place/runs`. Live dashboard: `training/serve_runs.py` → All Runs → task
`pick_place` → `pp_v8`.

**Outcome: pick recovered and improved (70% at 1.8M) but place never happened again.**
`pick_success_rate` dipped early (70%→20% by 800k) then climbed back to 70% by 1.8M -- non-monotonic but a real recovery, not noise, matching the pattern seen throughout this log. `place_success_rate` was 10% at the very first checkpoint (200k) then flat 0% at every one of the next 8 checkpoints through 1.8M -- a full 1.6M steps without a single placement, despite pick clearly still improving. The 4 self-monitoring analysis reports (400k/800k/1.2M/1.6M) never triggered the stall detector (reward/success trend wasn't flat enough over any 300k window), but the 1.6M report did flag entropy collapsing 1.497 → 0.009 ("COLLAPSED EARLY") -- below the stall threshold's combined bar, but a real signal on its own.

Stopped at 1.8M (externally terminated, not by the stall detector -- no `STALL_DETECTED.flag`, no error in the log) before reaching the full 2M budget. Rendered rollout frames from ckpt_1600032 were pulled and inspected before deciding pp_v9's fix (per this project's "watch the video before theorizing" rule): frames at steps 181, 361, 541, and 589 of the same 600-step episode showed **identical** ee→cube distance (0.018m), cube→dest distance (0.186m), cube height (0.017m), and reward (+11.40) -- the policy attaches early, nudges the cube slightly, then freezes into one fixed action for the remaining ~400 steps of the episode. Cube height (0.017m) never crosses `lift_threshold_m` (0.05m), so `has_lifted` stays `False` the whole time, which means the *weaker* `attached_idle_penalty` (-0.08) applies rather than the stronger after-lift one (-0.15) -- a frozen near-the-curriculum-spawn hover was cheap enough to sit in indefinitely. This directly explains why `place_success_rate` never recovered even as pick did: the policy isn't failing to find place, it's not exploring past this frozen equilibrium at all once entropy collapsed.

Checkpoint (final available, stopped here): `checkpoints/ckpt_1800036.zip`.

## pp_v8 → pp_v9: entropy collapse fix, stronger pre-lift idle penalty, GPU/throughput tuning

Two behavior/reward changes targeting the exact freeze diagnosed above, plus infrastructure changes (this run trains on a different, GPU-equipped machine than pp_v1-v8 used):

1. **`ent_coef`: 0.0 → 0.01** (`config/train_pick_place_ppo.yaml`). Every run of this task so far used SB3's `ent_coef=0.0` default -- nothing ever pushed back against entropy collapse. Directly targets the diagnosed failure mode: keep enough exploration noise alive that the frozen attached-not-lifted equilibrium isn't a permanent trap.
2. **`attached_idle_penalty`: -0.08 → -0.2** (`config/pick_place_env.yaml`), now stronger than `attached_idle_penalty_after_lift` (-0.15). This is the exact penalty that was too weak to dislodge the observed freeze (attached, not yet lifted, sitting still for ~400/600 steps).
3. **GPU + throughput tuning, by request.** This run's machine has a working CUDA torch install (RTX 5070, previously unused by this project -- `torch`/`mujoco`/`stable-baselines3` had to be installed into a GPU-enabled venv first, verified with a direct `torch.cuda.is_available()` check before launch) and 20 logical cores / 45GB free RAM (vs. the 8-core machine pp_v1-v8 ran on). Changed: `device: auto` → `cuda` (explicit, so a misdetection can't silently fall back to CPU), `n_envs: 6` → `16` (env stepping is the real throughput bottleneck -- MuJoCo physics is CPU-only regardless of the policy net's device), `batch_size: 64` → `256` (rollout buffer is `n_steps*n_envs` = 8192, still divides evenly into 32 minibatches -- a 128x128 MLP barely dents a modern GPU at batch=64). Note MuJoCo env stepping itself is inherently CPU-bound no matter what -- the GPU change only accelerates the PPO network's forward/backward passes, not the simulator.

**pp_v9**: launched **continuing from pp_v8's ckpt_1800036.zip** (the latest available checkpoint, 70% pick success) -- same architecture/obs/action space, so the checkpoint loads cleanly; no reason to discard 1.8M steps of pick-skill learning over a config-level fix. Not yet confirmed whether the entropy/idle-penalty changes actually unstick place -- first checkpoint/analysis pending.

**Outcome: stopped by the user at ~400k after observing a new exploit -- rapid attach/detach chatter with reward spiking each cycle.** Root cause found in `sim_env/suction_pick_place_env.py`'s `step()`: `attach_bonus` (+12.0) was paying out on **every** attach, not gated to the episode's first the way `lift_bonus` already was via `_has_lifted_this_episode` -- `pick_place_rewards.py`'s own module docstring says attach is supposed to be "once", so this was a genuine bug, not a design choice. A chatter cycle (attach +12, command suction off -> `premature_release_penalty` -3 since release wasn't over the destination, reattach +12, ...) nets +9/cycle, farmable indefinitely -- same shape of bug as pp_v3/v4's continuous `lift_bonus_weight` exploit. Checkpoints at 200k/400k show inflated `mean_reward` (282.0, 159.5) well above pp_v8's comparable range (57-212) with `place_success_rate` still 0% at both -- reward not trustworthy, matching how pp_v3/v4's exploited checkpoint was handled: **discarded, not continued from.**

Checkpoints (not used as a parent): `checkpoints/ckpt_200000.zip`, `checkpoints/ckpt_400000.zip`.
