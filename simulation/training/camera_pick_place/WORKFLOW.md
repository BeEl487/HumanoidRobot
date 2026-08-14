# Camera pick-place: step-by-step plan to policy training

**Current status:** `prototype_pipeline.py` + `tests/test_camera_pick_place_pipeline.py` already
implement and unit-test the *algorithms* for grasp-candidate estimation (with a depth-min-range
flag for the D435i's ~28cm limit), hand-eye transform fitting (Kabsch, least-squares rigid body),
and Iq-current grasp feedback — all against synthetic data. That satisfies "the math is correct"
but not any step's real test below: every one of those tests still needs to pass against real
camera frames, a real fitted transform validated on held-out physical poses, and real Iq
thresholds characterized on the actual gripper — synthetic-data unit tests are a precursor to
Phase 0-3's hardware tests, not a substitute for them. Keep treating each phase's test as separate
work, not as "already covered by the prototype."

This is the ordered build-out for the camera-based pick-and-place stack, from the current
docs-only state through to imitation-learning policy training (per
[`docs/ARCHITECTURE.md`](../../../docs/ARCHITECTURE.md) §8's decision: scripted pipeline first,
imitation learning second — not RL, on real hardware). **Do not skip a phase.** Each step has an
explicit test — do not start the next step until the current one's test passes. If a test fails,
fix the step in place; do not work around it downstream.

Every step here depends on real hardware, so treat physical safety as a standing rule, not a
per-step reminder: start every new motion at low speed / low current limit, keep a hand near
power-off, and only raise speed/force once a step's test has passed at the conservative setting.

---

## Phase 0 — Hardware decisions (blocking, nothing below can start without these)

These are all open items already tracked in ARCHITECTURE.md §9 — resolve them there, not just
here, since that file is the single source of truth per this project's standing rule.

1. **Decide and mount the gripper/end-effector.**
   Test: manually command open/close over CAN; confirm actuation, confirm current draw is sane
   (no stall current), confirm it can hold a representative test object statically for 30s+.

2. **Confirm the exact Jetson model and JetPack version.**
   Test: read board ID off the device (`/etc/nv_tegra_release` or equivalent), confirm CUDA/
   TensorRT availability matches what Phase 7 inference will need.

3. **Decide and physically mount the camera** (count, type, position — ARCHITECTURE.md §7).
   Test: stream RGB+depth from the camera *through the actual Jetson's actual interface*
   (CSI or USB3, not a dev laptop) at the resolution/fps the pipeline needs; confirm no bandwidth
   drop or frame loss under sustained streaming (run for several minutes, not one frame).

4. **Resolve the Teensy↔Jetson comms protocol** (custom serial vs. micro-ROS — ARCHITECTURE.md
   §4), since Phase 6+ will need to send commands down this path in near-real-time.
   Test: round-trip latency check — Jetson sends a dummy joint target, Teensy executes and
   telemetry returns; measure and record the loop latency.

5. **Measure and record real robot geometry**: arm link lengths, shoulder mounting offsets,
   joint sign conventions/range-of-motion, gimbal linkage empirical calibration via the 2
   CANcoders (all open items in ARCHITECTURE.md §9). Update the URDF with real numbers.
   Test: command a few known joint configurations, compare `ikpy` FK output against a physical
   tape-measure/known-fixture reading of the actual end-effector position. Must agree within a
   pre-agreed tolerance (a few mm / a couple degrees) before trusting the URDF for anything else.

---

## Phase 1 — Camera calibration and static perception (no arm motion yet)

6. **Camera intrinsic calibration** (checkerboard/target), even if using factory calibration as a
   starting point.
   Test: reprojection error under a set threshold (e.g. < 0.5px).

7. **Hand-eye calibration** — solve for the fixed camera→robot-base (or camera→end-effector, if
   an eye-in-hand mount was chosen in step 3) transform. This is a real calibration procedure
   (move the arm to several known poses, observe a fiducial), not something derivable from CAD —
   see the earlier conversation for why the geometry alone doesn't give you this.
   Test: hold out a subset of the calibration poses (not used to fit the transform); the computed
   transform must predict the fiducial's position at those held-out poses within a stated
   tolerance (e.g. < 1cm). Fitting error alone is not a valid pass — it must generalize to
   unseen poses.

8. **Object segmentation baseline** (single known cube) on RGB only, arm stationary.
   Test: run across the workspace's real position/lighting variation (not just one spot) —
   record a success rate over at least 20 trials before moving on.

9. **Depth alignment + 3D point-cluster projection** from the segmented mask.
   Test: compare the projected centroid against a hand-measured ground-truth cube position in
   robot base frame; must be within tolerance (e.g. < 1cm). Explicitly test the near-limit case —
   how the depth data degrades at the D435i's ~28cm minimum range, since that's exactly the
   distance during final grasp approach (flagged earlier as a known gap in this plan).

---

## Phase 2 — Reachability-aware grasp selection

10. **Grasp candidate generation + reachability check** (side/elevated approach bias, IK
    solvability against real joint limits from the calibrated URDF) — no arm motion required yet.
    Test: for a batch of candidate cube positions spanning the workspace, confirm accepted/
    rejected candidates match manual expectation (in particular: candidates that would force the
    arm to occlude the camera or violate a joint limit are correctly rejected).

11. **First scripted single-object pick execution, open-loop, slow/low-force.**
    Test: N physical trials (start with a conservative fixed speed/current cap) — confirm no
    collisions, confirm the arm reaches the intended pose within tolerance. Use the ODrive's Iq
    (current) telemetry as a collision/anomaly abort signal, and validate the abort logic actually
    fires by deliberately inducing a light touch during a trial.

---

## Phase 3 — Grasp execution with force/contact feedback

12. **Characterize the grasp force proxy** (Iq current draw at the gripper actuator, or a
    dedicated sensor if the chosen gripper design includes one — this closes the "no real-time
    grasp feedback" gap flagged earlier).
    Test: record baseline current for no-object / holding-object / over-gripping across several
    trials; confirm the thresholds reliably separate these cases.

13. **Full pick cycle**: approach → grasp → lift → verify (re-capture *and* the force signal from
    step 12) → place at destination, fixed object position.
    Test: success rate over 20-30 trials at a fixed position; log every failure mode (missed
    grasp, dropped object, misplacement) rather than just a pass/fail count.

---

## Phase 4 — Generalizing the scripted pipeline

14. **Vary object position across the workspace**, re-run the full cycle.
    Test: success rate across a grid of positions; explicitly map out where the camera-occlusion
    problem still causes failures despite the Phase 2 motion bias.

15. **Add closed-loop retry**: if the verify step (step 13) detects a failed pick, retry or flag
    rather than silently continuing.
    Test: deliberately induce a failure mid-grasp (nudge the object) and confirm the system
    detects and retries/reports correctly.

---

## Phase 5 — Teleoperation infrastructure (prep for imitation learning)

16. **Decide and build the teleoperation method** (leader arm / joystick / VR / hand-guided
    backdrive — open item, ARCHITECTURE.md §9).
    Test: an operator can teleoperate the arm through a full pick-place cycle smoothly, with
    joint targets logged correctly and latency low enough to feel controllable.

17. **Build the demonstration-recording pipeline**: synchronized camera frames + joint states +
    gripper state + timestamps, saved per episode.
    Test: record a handful of demo episodes, replay the logs offline and confirm no dropped
    frames and timestamps aligned within the control loop's tolerance.

---

## Phase 6 — Demonstration data collection

18. **Collect a real demonstration dataset** covering the position variation validated in Phase 4.
    Test: dataset sanity pass — no corrupted episodes, position coverage reviewed, a random
    sample of episodes spot-checked visually before trusting the full set.

---

## Phase 7 — Policy training

19. **Set up the imitation-learning pipeline** (ACT / diffusion-policy / LeRobot-style, per
    ARCHITECTURE.md §8), training off-device (PC/cloud GPU — the Jetson is inference-only).
    Test: **overfit sanity check first** — train on just 2-3 demo episodes and confirm the policy
    can near-perfectly reproduce those specific episodes. This validates the whole data pipeline
    (observation formatting, action space, loss) before trusting a full run on top of it.

20. **Train on the full dataset.**
    Test: held-out prediction error trending down, then a real-robot rollout success rate as the
    metric that actually matters — compare it against the Phase 3/4 scripted-pipeline success
    rate as the floor to beat, not against training loss alone.

---

## Workflow practices (apply throughout, not just at the end)

- **Update `docs/ARCHITECTURE.md` in the same change** whenever a hardware/software decision in
  Phase 0-1 gets resolved (gripper, Jetson model, camera, comms protocol, geometry) — this repo's
  standing rule is that ARCHITECTURE.md is the source of truth and must stay current, not that
  code/docs here duplicate it.
- **Record every phase's test result in [`EXPERIMENTS.md`](EXPERIMENTS.md)**, including failed
  attempts and what fixed them — the existing ledger format (perception/grasp/scene changes +
  success notes + reason ended) already fits this; use it per phase, not just per training run.
- **Move open items out of the ARCHITECTURE.md §9 checklist as they resolve**, don't just note
  the resolution here and leave the checklist stale.
- **Don't reorder phases to "save time."** Several steps exist specifically because an earlier
  session skipped equivalent groundwork and had to retract a conclusion later (see
  ARCHITECTURE.md's VBUS misread history) — a calibration or measurement skipped now becomes a
  much more expensive debugging session two phases later, when the symptom no longer obviously
  points back to the real cause.
- **Physical safety default:** every new motion (first execution of a new step, or after any
  hardware change) starts at reduced speed/current limit; only raise it after that step's test
  has passed conservatively.
- **Git-commit at phase boundaries**, not mid-phase — makes it possible to bisect "which phase
  introduced this regression" the same way the pp_v-series sim runs are tracked per-experiment.
