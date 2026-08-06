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

### ⚠ Known hardware bug: VBUS divider mismatch (found 2026-08-06)

- The physical board's VBUS sense-resistor divider measures like the firmware's **`v3.6-24V`**
  variant (divider ratio 11.0), **not** the `v3.6-56V` variant the repo defaults to (ratio 19.0) —
  confirmed by feeding known voltages and observing a consistent ~1.73x scaling error
  (19.0/11.0 = 1.727), and independently confirmed by reading the ratio logic directly from
  `Firmware/Board/v3/Inc/main.h` in the firmware source.
- Root cause: `Firmware/tup.config`'s `CONFIG_BOARD_VERSION` selects the divider ratio at compile
  time (`Firmware/Tupfile.lua`). This board was sold/labeled as the "56V variant" but its actual
  sense resistors match the 24V-variant design. Because this is a clone board with no factory OTP
  calibration burned in, `odrv0.hw_version_variant` can't be used to detect this — it just echoes
  back whatever `HW_VERSION_VOLTAGE` the firmware was compiled with, whether or not that matches
  the real hardware.
- **This is already fixed in `MKS-Odrive-Mini-Firmware/ODriveFirmware.bin` in this repo** — that
  file was verified (SHA-256 match) to be a build with `CONFIG_BOARD_VERSION=v3.6-24V`, built from
  a working WSL toolchain (`~/MKS_ODrive_MINI_custom_firmware` in the `Ubuntu` WSL distro on this
  machine, which has `tup`/`arm-none-eabi-gcc` already installed — the `Ubuntu-22.04` distro does
  not). **Unconfirmed: whether this corrected build has actually been flashed to the physical
  board(s) yet** — flashing needs `openocd`, which isn't installed anywhere on this machine as of
  this check.
- **Scope across the fleet:** this was diagnosed on one unit. All 8 ODrive Minis are presumably
  the same board batch/variant, so the same divider mismatch — and the same fix — likely applies
  to all 8, not just the one tested. Worth confirming per-unit before assuming, since a mixed batch
  isn't impossible.
- This also means the DC bus voltage trip thresholds are computed from `HW_VERSION_VOLTAGE` at
  compile time (`dc_bus_overvoltage_trip_level = 1.07 * HW_VERSION_VOLTAGE`), so building for
  `v3.6-24V` changes the overvoltage trip to ~25.7V — check this is still sane for a 12V pack
  alongside whatever the undervoltage trip is configured to.

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

## 9. Open questions / TBD checklist

Update this list as items get resolved — move resolved items into the relevant section above
instead of just deleting them.

- [ ] Teensy ↔ Jetson comms protocol (custom serial vs. micro-ROS)
- [ ] Exact Jetson model (original Nano vs. Orin Nano vs. other)
- [ ] Camera setup (count / type / mounting)
- [ ] Actual per-axis CAN node ID assignments (repo sample suggests increments of 2)
- [ ] Actual motor model(s) and confirmed pole pairs / current limits per axis
- [x] Root cause of bad VBUS readings found: board's divider matches `v3.6-24V`, not `v3.6-56V`
      (see §3) — fix is built (`ODriveFirmware.bin` verified as a `v3.6-24V` build) but **not
      confirmed flashed** to any board yet
- [ ] Flash the corrected `v3.6-24V` `ODriveFirmware.bin` to all 8 units (confirm each is the same
      board variant first) — needs `openocd`, not currently installed anywhere on this machine
- [ ] Install `openocd` (e.g. in the `Ubuntu` WSL distro alongside the existing `tup`/
      `arm-none-eabi-gcc` toolchain) before flashing can happen
- [ ] After reflashing, re-verify `odrv0.vbus_voltage` reads correctly and re-check/re-tune the
      undervoltage trip (overvoltage trip is now computed as `1.07 * 24 ≈ 25.7V` post-fix — sanity
      check this and the undervoltage trip are both still appropriate for a 12V pack)
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
