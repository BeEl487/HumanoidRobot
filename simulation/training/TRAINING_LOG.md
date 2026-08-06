# Training log — bin-picking PPO iterations

Consolidated report across all training runs on the state-based bin-picking policy. Each run's
full engineering detail (exact reward-function diffs, bug diagnoses, config changes) lives in
[`../docs/ASSUMPTIONS.md`](../docs/ASSUMPTIONS.md) under "Task / RL" — this file is the short,
readable version: what changed, what happened, what it means.

All runs: PPO (Stable-Baselines3), `MultiInputPolicy` (2×64 MLP, ~12k params), 500,000 timesteps
(except the original Milestone 8 smoke test, 30,000), both arms active, same environment
(`sim_env/bin_picking_env.py`) and camera/scene config throughout. See
[`README.md`](../README.md#watching-a-trained-policy) for how to watch any checkpoint yourself.

## Summary

| Run | Change from previous | Final reward | Best reward seen | Grasp success |
|---|---|---|---|---|
| Milestone 8 smoke test | — (pipeline verification only, 30k steps) | −83.1 | — | 0% |
| v1 | full 500k budget, same reward as smoke test | −46.0 | −46.0 | 0% |
| v2 | + dense proximity/contact bonuses (**had a reward-hacking exploit, fixed mid-run**) | −50.6 | −48.7 (pre-exploit) | 0% |
| **v3** | + one-time milestone bonuses (structural exploit fix) | −40.2 | **−29.0** (at 300k) | 0% |
| v4 | + entropy bonus (`ent_coef=0.01`) | −51.1 | −44.0 (at 200k) | 0% |
| v5 | + curriculum spawning (object starts near one arm) | −28.4 | −28.4 (at 500k, final) | 0% |
| v6 | + tighter curriculum + 3x touch/grasp bonuses | −41.9* | −41.9* | 0% |
| v7 (aborted) | + fingertip reference point (untested alone) | ~−40 (partial run, 340k/500k) | — | 0% |
| **v8** | + shorter walls + wall-clearance curriculum target | −51.6 | −51.6 | **0% (but 2/10 episodes made finger contact)** |

*v6's reward isn't directly comparable to earlier runs — its `distance_weight` is 1.5x steeper, so
the same behavior scores more negative by construction. A direct, reward-independent check (raw
EE-to-object distance) shows v6's policy is behaviorally identical to v5's — see the v6 section
below. v8 uses the same `distance_weight` as v6, so v6-vs-v8 numbers ARE directly comparable.

**v8 is the first checkpoint in this entire project to achieve finger contact at all** — 2 of 10
evaluation episodes, verified via the environment's own contact flag. v5 remains the best result by
raw reward. No run has produced a successful grasp (lift ≥5cm, held 10 consecutive steps) at these
budgets.

## v1 — baseline, full budget

Same reward as the Milestone 8 smoke test (distance shaping + sparse grasp/lift bonus only), run
for the full 500,000 timesteps instead of the smoke test's 30,000. Reward improved steadily
through training but **plateaued around −46 to −50 for the entire run** — the policy learned to
approach the object but had no signal telling it that closing the gripper near the object was
useful, so the sparse grasp bonus was never discovered by chance.

Checkpoint: `checkpoints/ppo_state_full.zip`

## v2 — dense bridging bonuses, and a real exploit

**Change:** added `gripper_close_bonus_weight` (rewards gripper closedness within a proximity
threshold, every step) and `single_finger_contact_bonus` (small per-step per-finger credit),
meant to bridge "close to the object" toward "gripper closed on it."

**What happened:** while monitoring training live, checkpoint 420k's evaluation reward spiked to
**+12.0** (vs. the −48 to −61 every other checkpoint showed). Traced to a single anomalous episode
scoring +247.9 — inspecting it frame by frame showed **zero finger contact for all 200 steps** and
the object never moving, yet reward held steady at ~1.87/step. The policy had discovered it could
park the gripper shut near the object and farm the proximity bonus indefinitely without ever
touching it — a genuine reward-hacking exploit, not progress.

**Fix (v2.1, incomplete):** gated the bonus on actual finger contact. **Fix (v2.2, structural):**
a closer audit found the v2.1 gate still left a loophole (the gripper's two fingers are
mechanically linked, so only one may ever reach an off-center object — a policy could graze that
one finger and hold position, still farming reward). Replaced both continuous bonuses with
**one-time-per-episode milestone bonuses** (`touch_bonus`, `grasp_bonus`) that cannot be
re-collected by holding still. Verified the fix by replaying the exact exploiting scenario: same
checkpoint, same seed, scored −31.6 under the corrected reward instead of +247.9.

Checkpoint: `checkpoints/ppo_state_v2.zip` (trained under the exploited v2.1 reward — its listed
reward is not comparable to later runs, which is why v3 was trained from scratch, not continued
from this checkpoint)

## v3 — clean run with the fixed reward

**Change:** the v2.2 structural fix (above) as the starting reward, trained from scratch.

**What happened:** a real, substantial improvement curve — −87.9 (20k) → −46.4 (100k) → −38.7
(200k) → **−29.0 (300k, best)** → −37.0 (400k) → −40.2 (500k, final). Unlike v1/v2's flat
plateaus, this is genuine learning, not noise. Completed in ~19 minutes (439 fps average — much
faster than v1/v2, which had eval/render processes competing for CPU during training). Grasp
success stayed at 0% throughout despite the improved reward.

Checkpoint: `checkpoints/ppo_state_v3.zip` — **best-performing checkpoint across all runs.**

## v4 — entropy bonus (did not help)

**Diagnosis going in:** the policy's action-distribution spread (`std`) consistently narrowed
from ~1.0 toward ~0.48–0.67 across v1–v3 (normal PPO behavior), plausibly converging on the easy
distance-reduction behavior before ever discovering the more precise contact behavior needed for
a grasp. SB3's PPO defaults to `ent_coef=0.0` (no entropy bonus).

**Change:** added `ent_coef=0.01`, a standard PPO exploration lever, to keep the action
distribution from narrowing as fast.

**What happened:** the mechanism worked exactly as intended — `std` stayed at 1.53 through the
end of training (vs. v3's 0.48). But sustained exploration **did not convert into a better
policy**: v4 trailed v3 at every single checkpoint (best: −44.0 at 200k, vs. v3's −29.0) and never
found a grasp either. The diagnosis was plausible but the fix didn't help in practice — noted
honestly rather than reframed as a partial win.

Checkpoint: `checkpoints/ppo_state_v4.zip`

## v5 — curriculum spawning (best result yet, still no grasp)

**Decision:** after presenting the v1-v4 picture, the user chose to keep iterating rather than
stop or switch to imitation learning -- option (b), a structurally different lever.

**Diagnosis:** every run (v1-v4) learned to reduce EE-to-object distance efficiently (that part
of the reward always improved), but none ever discovered actual finger contact, regardless of
reward shape (v1-v3) or exploration pressure (v4's entropy bonus). That pattern points at an
*exploration* bottleneck, not a *capacity* one -- contact is just rare to stumble into by chance
when the object can spawn anywhere across the full ~0.30×0.20 m bin, so the touch/grasp milestone
bonuses rarely fire early enough to ever get reinforced.

**Change:** reverted `ent_coef` to 0 (v4's fix didn't help, no reason to keep it) and added
curriculum spawning (`config/env.yaml`'s `curriculum` section, `sim_env/bin_picking_env.py`'s
`_curriculum_spawn`): instead of the full bin footprint, the object spawns in a small 0.02 m-radius
region close to one arm's ready-pose reach (~0.21-0.23 m away, vs. up to ~0.36 m under full
randomization), alternating between the left and right arm's side each episode. Contact should be
far easier to find early, so the milestone bonuses can start actually shaping behavior. Verified
with `check_env.py` before launching.

**What happened:** −70.3 (20k) → −31.5 (100k) → −30.9 (200k) → −31.3 (300k) → −29.9 (400k) →
**−28.4 (500k, final, best of all five runs)**. The shape of this curve is qualitatively different
from every prior run: it converges to near-final performance by 100k and then *holds* in a tight
−29 to −32 band for the remaining 400k steps, instead of peaking once and regressing (v3) or never
really breaking out of a plateau (v1, v4). Final evaluation (10 episodes, seeded): mean
reward −28.425, success rate 0.00. Grasp success was 0% at every single evaluated checkpoint from
20k through 500k — no exception anywhere in training.

Checkpoint: `checkpoints/ppo_state_v5.zip` — **best-performing checkpoint across all five runs.**

**Refined diagnosis:** the curriculum already starts the object close to the arm (spawn radius
0.02 m, ~0.21-0.23 m from the ready pose), and the policy reliably converges to *near* that object
early and then holds position there for the rest of training without ever crossing into contact.
That's a different failure signature than v1-v4 ("never reliably gets close") — it now looks more
like a last-mile precision problem (positioning the gripper accurately enough for the fingers to
actually touch) than a broad exploration problem. The policy network has stayed a stock SB3 default
(64×64 MLP, ~12k params) across all five runs and hasn't been tested as a variable on its own.

## v6 — tighter curriculum + bigger touch/grasp bonuses

**Decision:** the user chose option 1 from the previous round (tighten the curriculum further),
and separately asked to reward touching/closeness more directly. Both went into this run.

**Change:** `curriculum.spawn_radius_m` 0.02 → 0.006 (object now spawns almost exactly at the
target point); `touch_bonus` 2.0 → 6.0, `grasp_bonus` 5.0 → 12.0, `distance_weight` −2.0 → −3.0
(steeper). Theory: v5 reliably got close but never touched — maybe closing the last few cm felt
too risky (`knockout_penalty` −5.0) for a touch_bonus that wasn't worth it. Both bonuses stayed
one-time-per-episode, so this doesn't reopen the v2 exploit.

**Training note:** the first launch died silently at ~65k/500k steps when its background shell
session was torn down — not a code error. Checkpoints up to 60k survived and were left on disk;
training restarted cleanly from scratch. The results below are from that complete second run.

**What happened:** −105.4 (20k) → −42.9 (100k) → −42.8 (200k) → −43.5 (300k) → −42.5 (400k) →
**−41.9 (500k, final)**. Worse than v5 at every single checkpoint, at face value. But v6's
`distance_weight` is 1.5x steeper than v5's — the same underlying behavior produces a more
negative number by construction, so this isn't a fair comparison as-is.

**Direct check (bypassing reward weights entirely):** measured raw EE-to-object distance straight
from body positions for both final checkpoints, 10 episodes each. v5: 0.0645 m. v6: 0.0665 m —
2mm apart, within noise. **Neither v6 change moved the policy's actual behavior at all.** This is
itself a real result: reward magnitude was not the bottleneck, and the risk-aversion theory isn't
supported — tripling the touch bonus produced zero change in how close the policy got.

**A real finding, discovered while instrumenting the check above:** `ee_pos` (used for both the
distance-shaping reward and the observation vector) is actually `{side}_gripper_base_link` — the
wrist/mount frame, not the fingertips (see `sim_env/robot_model.py`'s `ee_body_name`). The real
fingertips sit ~5cm further along the gripper per the URDF's finger geometry. Measured directly on
a v6 rollout: mean distance from `gripper_base_link` to object = 0.0660 m (closest approach
0.0528 m) vs. mean distance from the actual fingertips = 0.0539 m (closest approach 0.0346 m).
The fingertips are consistently 1-2cm closer than what the policy is rewarded and shown for — this
has been true in every run, v1 through v6. It's a genuine gap in the environment design, not
something curriculum or bonus tuning could ever have fixed. It doesn't fully explain the wall
either (even the truer fingertip distance plateaus at 3-5cm, short of contact), but it's the most
concrete, well-evidenced lead to come out of six iterations.

Checkpoint: `checkpoints/ppo_state_v6.zip`

## v7 — fingertip reference point (aborted, superseded by v8)

**Change:** implemented v6's leading hypothesis — `BinPickingEnv._ee_pos()` now returns the
midpoint between the two fingertip collision geoms, used for both the distance-shaping reward and
the `ee_pos` observation, instead of `gripper_base_link`.

**What happened:** launched a 500k-step run. The first attempt died silently at 65k/500k when its
background shell session was torn down (a session/infra issue, not a code error); restarted and
reached 340k/500k before being **intentionally stopped**. While it was running, watching v6's
re-rendered rollout surfaced the wall-clearance finding below — it became clear v7 was training
under the same physically-blocked curriculum target v5/v6 used, so continuing it wouldn't isolate
whether the reference-point fix alone helped. Surviving checkpoints (100k-340k) showed 0% success
and no contact, consistent with that read but not treated as a clean final result. The fix carried
forward into v8 rather than being re-tested alone.

## v8 — wall-clearance fix: first-ever finger contact

**The finding:** watching v6's rollout, the user pointed out the gripper looked like it was
"really just pressing into the bin" rather than reaching the object. Quantified: the gripper's max
jaw opening is 0.06 m, but the v5/v6/v7 curriculum targets (Y=±0.08) left only 0.02 m of clearance
to the nearest bin wall — physically less than a third of what the gripper needs to open around
the object. True for every curriculum-based run so far, independent of reward shape or reference
point, and the leading explanation for zero contact across v5-v7.

**Change:** curriculum target Y moved from ±0.08 to ±0.02 (0.08 m clearance vs. the gripper's
0.06 m jaw). Also cut bin wall height to 1/3 (separately motivated by rendered video looking like a
closed aquarium) and carried forward v7's fingertip reference-point fix. `check_model.py`,
`check_env.py`, and `reachability_check.py` (88.9%, gate is 80%) all passed before launch.

**What happened:** −119.7 (20k) → −54.2 (100k) → −54.2 (200k) → −54.4 (300k) → −52.1 (400k) →
**−51.6 (500k, final)**. Contact rate (episodes with any finger touch, of 10 evaluated): 0 → 1 → 2
→ 2 → 1 → **2**. **This is the first time any checkpoint in this project has made finger contact**
— confirmed via the environment's own contact-milestone flag, not eyeballed, and visible in the
published rollout (seed 2, contact at step 31/200). Success (full 2-finger grasp + lift + hold)
stayed at 0% throughout — even touching episodes only ever get one finger on the object, never
both simultaneously.

Reward is numerically similar to v6's plateau (-51.6 vs. -41.9) but this comparison IS fair (both
use the same `distance_weight`, -3.0) — v8 sits a bit worse on raw reward despite the real
behavioral improvement, plausibly because episodes that get close enough to touch also risk more
knockout penalties than episodes that stay farther away.

Checkpoint: `checkpoints/ppo_state_v8.zip` — **first checkpoint to ever make contact.**

## Where this stands

Eight iterations. v8 is the first to break through to actual contact, confirming the wall-clearance
diagnosis was a real, physically-grounded blocker — not just another hyperparameter guess. The
remaining gap looks different in kind from every earlier round: not "can't get close" (v1-v4), not
"gets close but the reward doesn't reflect it" (v6's measurement-gap finding), but "touches with one
finger and stops" — a precision/control problem. Options on the table:

1. **The queued anti-stall penalty** — `config/env.yaml`'s `reward.stuck` (added this session, off
   by default so it couldn't leak into v8's own evaluation) penalizes the closest arm's EE for
   staying near-motionless too long. Touch-then-freeze is exactly the pattern this targets; flip
   `enabled: true` for v9.
2. **Increase network capacity** — still a stock 64×64 MLP across all eight runs; closing both
   fingers around an object may need finer control than it can express.
3. **Switch to imitation learning** — `../../docs/ARCHITECTURE.md` §8 already prefers this over
   RL for the real robot's manipulation learning, for reasons that apply here too (contact-rich,
   precision-sensitive tasks are exactly where sparse-reward RL struggles and demonstrations shine).
4. **Stop here** — v8 is a genuinely new baseline (first-ever contact), and the simulation pipeline
   itself is solid and fully verified regardless of whether this specific RL search converges.

## Bugs found and fixed along the way (not RL-specific, but found during this work)

- **Camera coverage**: the head camera missed the object in ~45% of its actual randomized spawn
  positions, passing every prior visual check because those checks only rendered the object at
  the bin's center. Caught by watching a real policy rollout, fixed by widening the lens and
  re-aiming it (verified via a new coverage-sampling check, `scripts/check_camera_coverage.py`,
  now at 100% coverage).
- **Grasp detection**: with both arms active, the original contact check could report "grasped"
  from two *different* arms' fingers touching independently, not one arm's two fingers actually
  enclosing the object. Fixed to require both fingers of the same arm.
