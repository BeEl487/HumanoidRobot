# Humanoid Robot — Architecture

**Status:** early build, top half only (torso + 2 arms on a gimbal). No legs, no hands yet.
Currently in Phase 1: scripted kinematic control (see §8).
**Last updated:** 2026-08-02

> **Keep this file current.** This is the single source of truth for the robot's hardware and
> software design. Any time an actuator, sensor, wiring assignment, power decision, comms
> protocol, or the AI/software plan changes, update the relevant section below (and the
> Open Questions checklist) in the same change. Code should be written to match what's written
> here, not the other way around.

## 1. Overview

A top-half humanoid robot: a torso that pivots on a 2-motor gimbal, with two 3-actuator arms
mounted on it. Goal is autonomous task completion — collect data on the robot, train models
off-device, deploy trained policies back onto the robot for on-device inference.

## 2. Mechanical structure

### Torso / gimbal
- Torso sits on a gimbal driven by **2 motors mounted in the same plane**, acting on **ball
  joints**, giving the torso front/back and left/right tilt.
- Mechanism: **independent axes via linkage/yoke** — each motor drives its own tilt axis through
  a linkage into the ball joint (not a differential pair where combined motor motion maps to
  combined axes).
- Each of the 2 gimbal motors has a **CAN-bus absolute encoder (CANcoder) mounted on its output**,
  separate from the ODrive's own motor-side encoder. This gives true joint-angle feedback through
  the linkage (needed because motor-side encoder position ≠ actual output angle once a
  linkage/yoke with backlash or non-1:1 mechanical advantage is in the loop).

### Arms
- Two arms (left/right), **3 actuators each**:
  1. Shoulder pitch
  2. Shoulder roll / abduction
  3. Elbow flexion
- No wrist joint, no gripper/hand yet — arms currently terminate at the elbow. End effectors are
  future work.

### Actuator count
- 6 arm ODrive Minis (3 × 2 arms) + 2 gimbal ODrive Minis = **8 ODrive Minis total**
- Plus 2 CANcoders (sensors, not actuators) on the gimbal output

## 3. Actuation — MKS ODrive Mini

- Hardware: MKS ODrive Mini, **HW v3.6 "56V variant" board** — this is a third-party ODrive
  clone, **not official ODrive Robotics hardware/firmware**.
- Firmware: custom build from
  [shazib2t/MKS_ODrive_MINI_custom_firmware](https://github.com/shazib2t/MKS_ODrive_MINI_custom_firmware),
  branch **`dev-get_iq`**, based on **ODrive firmware v0.5.1**, flashed to every ODrive Mini in
  the system (all 8, per the current build).
- Modifications vs. stock ODrive v0.5.1:
  - Encoder position estimate is piggybacked onto the existing CAN heartbeat message.
  - Added an **Iq (motor current) telemetry message** over CAN.
  - Both changes exist specifically to support ODrive-over-CAN in ROS 2, since the official
    ODrive ROS package doesn't support v3.6 hardware.
- CAN protocol: stock **ODrive CANSimple** (as implemented in v0.5.1) plus the two additions
  above. Standard CANSimple commands (Set_Input_Pos / Set_Input_Vel / Set_Input_Torque, Heartbeat,
  axis state changes, etc.) should apply, but this fork has **not** been diffed line-by-line
  against upstream — verify command IDs against this fork's source before assuming parity with
  official ODrive docs.
- Reference config values seen in the firmware repo's sample `mks_odrive_config.txt` (**defaults
  from the repo, not yet confirmed as this robot's actual per-axis settings**):
  - Pole pairs: 7, PMSM current control
  - Encoder: SPI absolute (AMS-style), 14-bit / 16384 CPR
  - DC bus undervoltage trip: 8.0V, overvoltage trip: 56.0V, max current: 20A
  - CAN node IDs suggested as incrementing by 2 per controller (0, 2, 4, …)
  - **⚠ This system runs at 12V.** The sample trip thresholds (8V–56V) were set for a
    56V-capable board being run near its ceiling, not tuned for a 12V pack. Confirm actual
    per-axis config on the robot, and make sure the undervoltage trip has headroom above the
    battery's real sag-under-load voltage.

### ⚠ VBUS voltage misreads — under investigation, earlier "fix" retracted (updated 2026-08-07)

- Exact board: **Makerbase XDrive Mini** (["based on ODrive3.6 with AS5047P on
  board"](https://makerbase3d.com/product/makerbase-xdrive-mini-high-precision-brushless-servo-motor-controller-based-on-odrive3-6-with-as5047p-on-board/)),
  documented input range **12–56V** — i.e. the 56V hardware class, not 24V.
- Symptom: `odrv0.vbus_voltage` reads consistently low vs. a multimeter at the same point (two
  data points: actual 12V → read 6.9V, actual 22V → read 12.7V — a ~1.73x scaling error in both
  cases).
- **2026-08-06 diagnosis (now believed wrong):** a prior session concluded the physical board's
  VBUS divider matches the firmware's `v3.6-24V` variant (ratio 11.0) rather than `v3.6-56V`
  (ratio 19.0), reasoning that `MKS-Odrive-Mini-Firmware/ODriveFirmware.bin` in this repo — a
  `CONFIG_BOARD_VERSION=v3.6-24V` build — was already the fix and just needed flashing.
- **Why that's retracted:** that `.bin` was confirmed (2026-08-07) to have been built as `v3.6-24V`
  since its very first commit (`13d48e6`, 2026-08-02) — it was never a build produced *in response*
  to the voltage diagnosis, just a pre-existing, unverified `tup.config` setting that happened to
  scale in the right direction to look like a match. Three independent sources instead agree the
  board is the **56V class**: (1) this exact product's documented 12–56V input range, (2) the
  official Makerbase firmware release (`ODriveFirmware_v3.6-56V.bin`, from
  [makerbase-motor/MKS-ODrive](https://github.com/makerbase-motor/MKS-ODrive)), and (3) the
  `dev-get_iq` fork's own out-of-the-box default (`shazib2t/MKS_ODrive_MINI_custom_firmware`
  README: "compiled for V3.6 56V variant board", default `CONFIG_BOARD_VERSION=v3.6-56V`). The
  user also confirms the board's original (factory) firmware read voltage correctly, before this
  repo's (always-24V) build was ever flashed.
- **Not yet resolved:** why the misread happens if the board is genuinely 56V — that requires a
  clean test with a *known* config, since no reading so far has been taken with a firmware build
  whose `CONFIG_BOARD_VERSION` was confirmed at the time of measurement. Candidates to try:
  - Rebuild the fork with its untouched default (`CONFIG_BOARD_VERSION=v3.6-56V`) and flash that.
  - Flash the community-dumped factory image,
    [`XDRIVE_MINI_original_FW.bin`](https://github.com/justlovescience/MKS-XDRIVE-MINI/blob/main/Firmwares/XDRIVE_MINI_original_FW.bin)
    (a real ST-Link dump of a working XDrive Mini, from
    [justlovescience/MKS-XDRIVE-MINI](https://github.com/justlovescience/MKS-XDRIVE-MINI)), and
    test against that as a known-good baseline.
  - **Status: waiting on the user to test one of the above on physical hardware** before drawing
    any further conclusion.
- **Do not flash the existing `MKS-Odrive-Mini-Firmware/ODriveFirmware.bin` (`v3.6-24V`) to any
  unit** until this is resolved — treat it as an unverified artifact, not a fix.
- This also affects DC bus voltage trip thresholds, which are computed from `HW_VERSION_VOLTAGE`
  at compile time (`dc_bus_overvoltage_trip_level = 1.07 * HW_VERSION_VOLTAGE`) — whichever variant
  turns out correct, re-check that the resulting overvoltage trip and the undervoltage trip are
  both still sane for this system's 12V pack.
- **Scope across the fleet:** all 8 units are presumably the same board batch/variant, so whatever
  this turns out to be likely applies to all 8, not just the one under test — but confirm per-unit
  before assuming, since a mixed batch isn't impossible.

## 4. Low-level control — Teensy 4.1

- Runs 3 independent CAN bus interfaces:
  | CAN bus | Connects to | ODrive Minis |
  |---|---|---|
  | CAN 1 | Arm 1 | 3 |
  | CAN 2 | Arm 2 | 3 |
  | CAN 3 | Torso gimbal (+ future additions) | 2, plus the 2 gimbal CANcoders |
- Role: real-time joint-level control — issues CAN commands to the ODrives, reads back
  heartbeat/encoder/Iq telemetry and CANcoder position, and bridges to the Jetson over USB.
- **Teensy ↔ Jetson link protocol: not yet decided.** Candidates on the table:
  - Custom USB-serial (CDC) framing, Teensy as a dumb relay/command executor
  - micro-ROS over the USB serial transport, Teensy as a native ROS 2 node
  - Decision is open — resolve before writing the firmware's host-communication layer.

## 5. High-level compute — Jetson Nano

- Connects to the Teensy 4.1 via USB.
- **Exact Jetson model not yet confirmed** (original Jetson Nano vs. Orin Nano vs. other). This
  matters a lot: JetPack version, CUDA/TensorRT capability, and camera interface all differ
  significantly between them. Confirm before assuming a JetPack version or inference runtime.
- Role: perception (camera capture), running the trained policy for **on-device inference only**,
  sending resulting joint targets down to the Teensy.
- **Not used for training.** Training happens on a separate PC or cloud GPU; only trained weights
  are deployed to the Jetson. (If the Jetson turns out to be the original 4GB Nano, this is a
  hard requirement, not just a preference — that board cannot realistically train modern models.)

## 6. Power system

- System voltage: **12V**.
- Source: **LiPo/Li-ion battery pack + BMS** (untethered, not a bench supply).
- Distribution: **split rails** — 12V goes directly to the 8 ODrive Minis (motor power, high
  current, electrically noisy); a separate regulated/isolated rail powers the Jetson and Teensy,
  keeping motor-driver switching noise off the compute supply.
- Open: battery cell count/capacity and BMS model not yet recorded here — add once finalized.
- See the ⚠ note in §3 about matching ODrive firmware voltage trip points to this pack.

## 7. Perception

- Camera setup: **not decided yet.** Open question — count, type (mono/stereo/depth), and
  mounting (head-only vs. multi-view) all still need deciding. Whatever is chosen needs to match
  what the confirmed Jetson model can actually interface (CSI lanes vs. USB3).

## 8. Software / AI plan

- End goal: train models that let the robot complete tasks autonomously, deploy them onto the
  robot for on-device inference.
- Training/inference split: **train off-device (PC/cloud GPU) → deploy trained weights to the
  Jetson for inference.** Confirmed, not open.
- Learning approach: **phased, not a single final choice.**
  - **Phase 1 (current):** scripted/classical kinematic control — no ML yet. Rationale: there's no
    gripper, no camera decision, and no finalized comms protocol yet, so there's nothing meaningful
    for imitation learning to imitate. Phase 1 validates the CAN/Teensy/Jetson pipeline with
    hardware that already exists.
  - **Phase 2 (planned, not started):** teleoperation + imitation learning (record demonstrations,
    train a policy such as ACT/diffusion-policy/LeRobot-style to imitate them) once there's a
    gripper/end-effector and a camera. This is the intended default for the actual manipulation
    learning, chosen over sim-to-real RL — RL earns its cost mainly on locomotion/dynamic balance,
    and this build is arms-and-gimbal only with no legs.
  - Re-evaluate this phasing once Phase 1 kinematic control is working and the gripper/camera
    decisions land.

### Phase 1 — kinematic control

- **Where it runs:** on the Jetson, in Python. The Teensy stays a thin relay — it executes joint
  targets over CAN and reports telemetry back, it does not compute kinematics itself. Rationale:
  faster to iterate on than C++ on the Teensy, and it's already where Phase 2 ML will live, so the
  kinematics layer isn't thrown away later.
- **Modeling approach:** a proper **URDF** robot description, not ad-hoc transforms in code. Chosen
  over a minimal custom FK/IK module because it's directly reusable later for visualization (RViz
  or similar), simulation, and eventual sim-to-real work — the extra upfront setup pays for itself.
- **Library:** [`ikpy`](https://github.com/Phylliade/ikpy) — pure-Python, loads URDF directly, solves
  FK/IK for simple serial chains without needing a full ROS install. Sufficient for 3-DOF arms and
  a 2-DOF gimbal; revisit (e.g. `pinocchio`, full ROS 2 + MoveIt2) only if the robot grows more DOF,
  needs collision-aware planning, or a ROS 2 stack gets adopted for other reasons.
- **Control mode:** position-only to start, matching the ODrive firmware's default position-control
  w/ trapezoidal-trajectory mode (see §3). Velocity/torque control is future work.
- **Gimbal modeling caveat:** the real gimbal is 2 independently-linked motors driving a ball joint
  (§2), not a clean 2-DOF serial joint. For a first-pass URDF, model it as an **idealized universal
  joint** — two orthogonal revolute axes intersecting at a point — and treat that as an
  approximation to be corrected later using the 2 gimbal CANcoders' actual readings (calibrate the
  motor-angle → true-output-angle mapping empirically rather than assuming it analytically).
- **Blocked on:** none of this needs the Teensy↔Jetson protocol decision (§4) — the kinematics
  layer can be built and tested standalone (feed it joint angles, get poses back) before that's
  resolved. It does need the physical measurements listed in the checklist below before the URDF
  can use real numbers instead of placeholders.

### Manipulation tasks (e.g. sorting items from a box)

- **Prerequisites, in order:** gripper/end-effector → scripted pick-and-place using it (still
  Phase 1, no vision) → confirmed Jetson model + camera choice → object recognition/perception →
  teleoperation method for demo collection → imitation learning.
- **Control algorithm sequencing:** don't reach for imitation learning first. Do **scripted IK +
  object recognition** (Phase 1 extended with vision — detect item pose, IK to it, scripted grasp)
  for a small fixed set of known items/bins first. It validates the gripper, camera, and reach
  accuracy without also needing teleoperation infra and training data at the same time.
  **Imitation learning** (Phase 2, per above) is reserved for when scripted grasping hits its
  actual limit — generalizing to item types/arrangements not hand-coded for — not before.
- **Teleoperation method for demo collection is not yet decided** (leader arm, joystick, VR
  controller, hand-guided backdrive) — needed for Phase 2 regardless of which option above, added
  to the checklist below.

## 9. Open questions / TBD checklist

Update this list as items get resolved — move resolved items into the relevant section above
instead of just deleting them.

- [ ] Teensy ↔ Jetson comms protocol (custom serial vs. micro-ROS)
- [ ] Exact Jetson model (original Nano vs. Orin Nano vs. other)
- [ ] Camera setup (count / type / mounting)
- [ ] Actual per-axis CAN node ID assignments (repo sample suggests increments of 2)
- [ ] Actual motor model(s) and confirmed pole pairs / current limits per axis
- [ ] VBUS misread root cause **retracted, not yet re-solved** — earlier `v3.6-24V` diagnosis was
      based on an unverified pre-existing build, not a confirmed fix; board is very likely the
      56V class per vendor spec + official firmware + fork default (see §3). **Blocked on user
      testing** either a fresh `v3.6-56V` rebuild or the community-dumped
      `XDRIVE_MINI_original_FW.bin` on physical hardware.
- [ ] Do **not** flash `MKS-Odrive-Mini-Firmware/ODriveFirmware.bin` (`v3.6-24V`) to any unit until
      the above is resolved
- [ ] Install `openocd` (e.g. in the `Ubuntu` WSL distro alongside the existing `tup`/
      `arm-none-eabi-gcc` toolchain) before flashing can happen
- [ ] Once a config is confirmed correct, re-verify `odrv0.vbus_voltage` reads accurately and
      re-check/re-tune the undervoltage trip (overvoltage trip is `1.07 * HW_VERSION_VOLTAGE` —
      sanity check both against this system's 12V pack once the variant is settled)
- [ ] Battery pack spec (chemistry, cell count, capacity, BMS model)
- [x] Learning approach — phased: scripted kinematic control now, teleop+imitation learning later (§8)
- [ ] Gripper / end-effector plan for the arms
- [ ] Arm link lengths (shoulder-to-elbow, elbow-to-end) for the URDF, both arms
- [ ] Shoulder mounting offsets relative to the torso/gimbal center (lateral + vertical)
- [ ] Joint sign conventions and mechanical range-of-motion limits for shoulder pitch, shoulder
      roll, and elbow (per arm)
- [ ] Gimbal linkage geometry / motor-angle-to-output-angle relationship (or a calibration
      procedure using the 2 CANcoders, if no closed-form relationship is available)
- [ ] Reference "zero pose" definition (what the physical rest position of each joint looks like)
- [ ] Teleoperation method for imitation-learning demo collection (leader arm / joystick / VR
      controller / hand-guided backdrive) — needed for Phase 2 (§8)

## 10. Related work — MuJoCo RL simulation track

A MuJoCo digital-twin simulation lives under `simulation/` at the repo root, built for **sim-to-real
reinforcement learning** (Gymnasium + Stable-Baselines3, PPO/SAC) on vision-based bin-picking/sorting.

This is an **independent research track**, kept deliberately separate from this document's own
Phase 1/Phase 2 plan (§8) — it does **not** change or replace the §8 decision to use teleoperation +
imitation learning for the real robot's manipulation learning (RL was explicitly considered and
rejected there for reasons specific to this hardware). The simulation explores whether RL works for
grasping in parallel, on its own track, using placeholder/estimated hardware specs (no gripper or
camera exists on the real robot yet, and the sim's first milestones don't model the gimbal either —
see `simulation/docs/ASSUMPTIONS.md` for every assumed value and what needs confirming before it
informs real hardware decisions).

See `simulation/README.md` for scope and setup, and `simulation/docs/ASSUMPTIONS.md` for the full
log of every estimated dimension/mass/limit/spec used, since none of this repo's real measurements
exist yet (per §9 above).
