# Suction pick-place: experiment ledger

Every training run treated as an experiment, not a from-scratch restart -- per request (see
[`AUTOMATED_TRAINING_GUIDE.md`](AUTOMATED_TRAINING_GUIDE.md) §7). Populated retroactively for
pp_v1 through pp_v8 from [`TRAINING_LOG.md`](TRAINING_LOG.md)'s narrative history and each run's
`manifest.json`; append a new row here for every future run, ideally at launch time (fill in
"final metrics"/"reason ended" once it actually ends).

| # | Run | Parent checkpoint | Hyperparameter changes | Reward changes | Env/scene changes | Curriculum changes | Final reward | Pick / Place success | Best checkpoint | Reason ended |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | pp_v1 | none (fresh) | stock defaults, 64x64, n_envs=1 | initial: distance/attach/lift/carry/place/step | initial scene (0.08x0.08 boxes, finger-grasp gripper geoms unmodified) | none | −56.25 | 0% / 0% | ckpt_200000 | Gripper never attached at all (0% pick) -- root cause found by watching rollout: leftover finger-grasp collision geoms ("claw") snagging on box walls |
| 2 | pp_v2 | none (fresh -- structural geometry fix, not worth carrying v1's near-zero-signal weights) | unchanged | unchanged | claw geoms neutralized (shrunk, decollided, invisible); boxes repositioned for reachability | none | −61.58 (400k, dipped from −11.91 at 200k) | 40%→20% (200k→400k) / 0% | ckpt_200000 | Stopped -- attach works but plateaus without ever discovering carry+release; diagnosed as needing a curriculum (mirrors bin-picking's own v5 fix) |
| 3-4 | pp_v3/pp_v4 | none (fresh) | unchanged | added start-attached curriculum's cube spawn; `lift_bonus_weight` continuous (**bug**) | unchanged | added: `start_attached_prob: 0.5`, fixed | +290 (inflated, reward-hacking exploit) | ~30% / 0% | n/a -- reward not trustworthy | Reward-hacking exploit: continuous lift_bonus_weight let the policy camp attached+lifted indefinitely for free reward, confirmed via a deterministic rollout trace showing zero movement |
| 5 | pp_v5 | none (fresh -- exploited checkpoint's weights not worth carrying) | unchanged | `lift_bonus_weight`→0, one-time `lift_bonus`+`stage_transition_bonus`, progress-gated `attached_idle_penalty` | unchanged | unchanged | −142.72 (realistic) | 30% / 0% | ckpt_200000 | Exploit fix worked (reward realistic again) but overcorrected: `mean_suction_cmd_rate=0.006` -- policy almost never attempts suction |
| 6 | pp_v6 | none (fresh) | unchanged | `carry_distance_weight`/`_after_lift` cut ~4x, `attach_bonus`/`lift_bonus` raised | unchanged | added `eval_mode` (curriculum-free eval/video); annealed `start_attached_prob` 0.6→0.15 | −119.7 (1M, regressed from −26.3 at 600k) | 20%→0% (200k→1M) / 0% | ckpt_600000 | Rendered rollout showed the arm jamming against a box wall and staying stuck; cube also seen tunneling clean through a wall on one checkpoint |
| 7 | pp_v7 | none (fresh) | `policy_kwargs.net_arch`: 64x64→128x128 | `stall_penalty` (collision+near-zero-velocity, sustained); `collision_penalty` −0.02→−0.05 | `boxes.wall_thickness` 0.004→0.01 (fixes tunneling) | unchanged | noisy, +44 (600k) to −60 (1.2M) | 0%→**60%** (200k→1.2M, real sustained trend) / 0% | ckpt_1200024 | Not a failure -- paused to fold in the next round of requested pipeline/reward work; continued (not discarded) into pp_v8 |
| 8 | pp_v8 | pp_v7 / ckpt_1200024 (chosen: real, sustained 60% pick-success trend -- clearly the "learned useful low-level behavior" case the parent-checkpoint decision rule is for, not a local optimum to discard) | unchanged from pp_v7 (128x128, n_envs=6) | added `cube_disturbance_weight` ("gentleness" -- penalizes pushing the cube while touching-not-attached) | `episode_max_steps` 300→600 | unchanged (still annealing from wherever pp_v7 left the curriculum config -- see note below) | +57.6 (1.8M, noisy) | 70% / 0% (one 10% blip at 200k) | ckpt_1800036 | Stopped at 1.8M (externally terminated, not by the stall detector). Self-monitoring's own 1.6M analysis flagged entropy collapsing 1.497→0.009; a rendered rollout (ckpt_1600032) confirmed the consequence -- identical ee/cube/reward values from step 181 to 589 of a 600-step episode, frozen attached-but-never-lifted (cube height 0.017m, below the 0.05m lift threshold). Diagnosed as: pre-lift `attached_idle_penalty` too weak to dislodge a frozen hover, and nothing (`ent_coef=0.0`) was ever pushing back against the entropy collapse that locked the policy into it. Continued into pp_v9. |

**Note on pp_v8's curriculum continuation:** `--init-checkpoint` restores policy/value network
weights and optimizer state, but `start_attached_prob` lives in `config/pick_place_env.yaml`, read
fresh at each run's start -- so pp_v8 restarted the anneal from `start_attached_prob_initial: 0.6`
rather than continuing from wherever pp_v7's anneal had reached by step 1.2M. Not necessarily wrong
(more curriculum-assisted practice on the new `cube_disturbance` penalty isn't unreasonable), but
worth knowing: checkpoint continuation currently carries over network weights only, not
environment/curriculum runtime state. A future improvement could persist+restore the anneal
progress too if that turns out to matter.

| 27 | pp_v27 | **none (fresh init -- pp_v26's checkpoint is action-space-incompatible)** | unchanged (ent_coef 0.003, n_envs 16) | unchanged | **`humanoid.urdf` arm model changed: added `shoulder_yaw_joint` (4th arm joint, rotation about vertical, innermost), so action space grew 4→5 dims** | unchanged (start_attached/carrying probs) | in progress | in progress | in progress | Launched. Not a reward/curriculum experiment -- a robot-model change (user-requested: arm couldn't pivot out of the head camera's FOV with only pitch/roll/elbow). Surfaced and fixed a real self-collision bug in the new joint's proxy geometry (see `docs/ASSUMPTIONS.md` "Arms" table) before launching. pp_v26's 70%/60% pick/place result stands as the 3-DOF-arm reference, not invalidated, just superseded. |

## How to add a new row

Before launching a new experiment, per the automation guide's §7 requirement: write the row's
"parent checkpoint" / "changes" / "why this is expected to help" / "which failure mode it
addresses" columns *before* starting the run (this is the "explain before launching" step), then
fill in the outcome columns once it ends (or at each analysis checkpoint, if still running).
