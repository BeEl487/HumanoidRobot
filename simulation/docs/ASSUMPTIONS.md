# Assumptions Log

Every numeric value or design decision in `simulation/` that isn't a measured/confirmed fact about
the real robot gets a row here, in the same change that introduces it. No placeholder is allowed to
live only as a code or config comment — this file is the single place to check "what did the sim
assume, and what needs a real measurement before it can inform physical hardware?"

Units: SI throughout (meters, kilograms, radians, seconds) unless a column says otherwise.

## Meta-assumptions (apply across the whole simulation, not tied to one part)

These are structural decisions made before any numeric value was picked, driven by user direction
and by `docs/ARCHITECTURE.md` having almost nothing measured yet (confirmed via full repo search —
no URDF, CAD, mesh, or measurement doc exists anywhere in this repo outside ARCHITECTURE.md itself).

| # | Assumption | Rationale | Confirm before real hardware? |
|---|---|---|---|
| M1 | Torso is modeled as a single rigid body, welded to the world — **no gimbal joints, permanently.** | User directive: the two arms are the only moving subsystem in this simulation, by design, not as a temporary build-order simplification. The real robot **does** have a 2-motor gimbal (ARCHITECTURE.md §2) — this is a deliberate, permanent scope decision for this simulation, not a claim that the real robot has no gimbal, and gimbal reintroduction is not on this project's roadmap. | **Yes — critical.** A policy trained with a fixed torso will not transfer to hardware whose torso can tilt. This is a standing, accepted sim-to-real gap for this project, not a TODO. |
| M6 | Arm dimensions, shoulder offsets, and joint range magnitudes are cross-checked for plausibility against [Poppy Torso](https://github.com/poppy-project/poppy-torso), an open-source 3D-printed research torso+2-arm robot of comparable scale and purpose. | Poppy Torso's arms have 4 DOF (shoulder_y, shoulder_x, arm_z, elbow_y) vs. this robot's 3 (no arm-rotation joint) and different actuators (Dynamixel servos vs. ODrive Mini + BLDC), so its files/meshes/exact joint graph are **not** reused — only order-of-magnitude proportions (shoulder lateral offset ~0.077m, upper-arm segment ~0.11m, joint ranges ~100–150° per axis) as a real-world sanity check against pure guesswork. | No — this is a grounding reference for estimates, not a hardware claim about this robot. |
| M2 | No gripper/end-effector exists on the real robot. A placeholder parallel-jaw gripper is designed for simulation purposes only (Milestone 3). | User directive, since the grasping task is meaningless without *some* end effector, and none has been chosen physically yet. | **Yes — critical.** Every gripper dimension/mass/friction value here is a simulation-only proposal, not a hardware spec. Must be replaced wholesale once real gripper hardware is chosen — do not treat any value under "Gripper" below as a design target. |
| M3 | No camera has been chosen for the real robot, and no head/neck link exists in the architecture at all — the torso is the topmost body segment. The simulation's camera is fixed rigidly to the top-front of the torso, standing in for a "head" camera. | Most sensible default given the real architecture: a torso-mounted camera co-moves with the gimbal-driven torso tilt the same way a head-mounted camera would track gaze via neck motion — so it's a reasonable functional stand-in even though it isn't mounted on a dedicated head link. | **Yes.** Confirm whether a future head/neck mechanism is planned separately from torso tilt; if so, camera mounting geometry here should be revisited, not assumed to transfer directly. |
| M4 | All part masses/inertias are computed by MuJoCo automatically from primitive collision geometry × a per-part material density, not hand-derived inertia tensors. | More defensible than guessing full 3×3 inertia tensors by hand; MuJoCo's compiler does this natively and correctly for primitive geoms. Densities themselves are still estimates (see per-part rows below) — only the tensor *derivation* is offloaded to the compiler, not the underlying mass estimate. | No — this is a modeling methodology choice, not a hardware claim. |
| M5 | Control mode aims to approximate the real ODrive firmware's **position control with a trapezoidal velocity/accel-limited trajectory** (ARCHITECTURE.md §3), via a trajectory-shaping layer feeding MuJoCo position actuators — not raw torque control and not an instantaneous position actuator. | Matches the real actuator's documented behavior more closely than a naive position servo, which matters for sim-to-real transfer of any learned timing/dynamics. | Yes — once real ODrive trap-trajectory accel/velocity limits are configured on hardware, the sim's `trajectory_shaper` limits should be matched to them, not left at placeholder values. |

## Torso (Milestone 1)

| Parameter | Value | Rationale | Confirm before real hardware? |
|---|---|---|---|
| Torso box dimensions | 0.09 × 0.07 × 0.30 m (W×D×H) — was 0.18 × 0.12 × 0.30 through v10 | **v11 change, load-bearing finding:** every past reachability verification (v8's wall-clearance fix, v10's shoulder_roll widening, `reachability_check.py`'s whole gate) used ikpy IK only, which has no notion of the torso's collision geometry at all. Checked directly against actual MuJoCo contact detection (not just IK) for the first time: at the old size, reaching the curriculum target required the upper arm to penetrate **3.6cm into the torso box** — physically impossible in the real sim, meaning the "verified reachable" target v10 shipped was never actually reachable. Full-bin check redone with both IK-solvability AND zero self-collision required: old size passed only 22/36 (61%) of the bin-floor grid; this size passes 36/36, with margin (0.10 × 0.08 is the bare-minimum clearing size). **This conflicts with the row below** — flagging rather than silently dropping it. | Yes |
| Torso box dimensions vs. electronics fit | Unresolved conflict | The old 0.18×0.12×0.30 size was explicitly sized to "plausibly enclose a small torso frame + 12V battery pack + Jetson + Teensy + 2 gimbal ODrives" (prior placeholder rationale). At 0.09×0.07×0.30, that stated packaging assumption almost certainly no longer holds — this shrink was driven entirely by sim arm-reach/self-collision, not a real packaging study. Real hardware will need either a genuinely smaller electronics package, a torso shape that isn't a simple box (freeing up reach clearance without shrinking overall volume), or shoulders mounted further forward/outward to clear a full-size torso. | Yes — this is the one to resolve before any real build, not just measure. |
| Torso lumped density | 550 kg/m³ | Unchanged — backed out from a target mass guess, not a bill of materials (see prior note; aluminum at the old volume would be ~17.5 kg, clearly wrong for a hollow/lightweight structure). | Yes — replace with a real lumped density once the torso assembly is weighed. |
| Torso mass (derived) | ≈1.04 kg — was ≈3.6 kg through v10 | 0.09×0.07×0.30 × 550 kg/m³. Dropped with the volume; not a real mass estimate for whatever the real torso ends up being once the electronics-fit conflict above is resolved. | Yes (follows from the two rows above) |
| Mount height above ground | 0.90 m | Arbitrary fixed-rig height for a tabletop-reach workspace; revisited by the reachability check in Milestone 5. | No — sim-only rig parameter, not a real robot spec (the real robot has no defined mounting/base height either). |

## Arms (Milestone 2)

| Parameter | Value | Rationale | Confirm before real hardware? |
|---|---|---|---|
| Rest-pose convention | Arms hang straight down from the shoulder, fully extended (elbow straight), at all-zero joint angles. | Standard "arms at ease" humanoid convention; also the only convention (of the ones considered) where every joint's rotation axis is perpendicular to the arm's own pointing direction at that stage of the chain — an "arms forward at rest" alternative was tried first and rejected because it made shoulder_roll's axis coincide with the arm's pointing direction, turning it into a no-op that just spun the arm about its own axis instead of swinging it. Caught by `rollout_smoke_test.py`'s `fk_sanity_check`. | This is the sim-scoped answer to ARCHITECTURE.md §9's open "reference zero pose" item — sim-only until validated on hardware. |
| Shoulder lateral offset from torso origin | (0, ±0.11, +0.05) m | Order-of-magnitude matched to Poppy Torso's shoulder offset (~0.077 m lateral); widened slightly for this robot's larger torso. | Yes |
| Upper arm | Cylinder r=0.020 m, l=0.18 m, PETG density 1200 kg/m³ → mass 0.271 kg (+0.15 kg lumped actuator mass at the shoulder-roll end, see below) | Scale order-of-magnitude matched to Poppy Torso's upper-arm segment (~0.11 m to elbow, plus intermediate brackets); sized somewhat larger to reach a table-height bin. | Yes |
| Forearm | Cylinder r=0.018 m, l=0.15 m, PETG density 1200 kg/m³ → mass 0.183 kg (+0.15 kg lumped actuator mass at the elbow end) | Same rationale as upper arm. | Yes |
| Per-joint lumped actuator mass | 0.15 kg per joint (0.025 m cube, density 9600 kg/m³), placed at each of the 3 joints per arm (shoulder_pitch on the shoulder connector link, shoulder_roll and elbow at the proximal end of their respective links) | Stands in for the ODrive Mini + BLDC motor assembly at each joint — no real datasheet mass exists yet, so a single box of plausible density (comparable to a compact motor+driver assembly) was used rather than modeling actual motor geometry. | Yes — critical, replace with real ODrive Mini + motor mass once weighed. |
| Joint ranges | shoulder_pitch: −120° to +155°; shoulder_roll: **−50° to +120°** (was −15° to +120° through v9); elbow: 0° to +148° | Magnitudes matched to Poppy Torso's l_shoulder_y (−120°/+155°), l_shoulder_x (~110° span), and l_elbow_y (~148° span) joints — Poppy's own zero-pose convention differs from this robot's ("arms down" here vs. Poppy's own reference), so only the range *magnitudes* were reused, not copied as absolute values against a matching zero. shoulder_roll's lower bound was widened from 0° to −15° during Milestone 5 (dead-zone fix, below), then to **−50° for v10** after a user-flagged suspicion ("I don't think your joint config is able to reach the cube") turned out correct: a proper IK solve (ikpy/LM, the same method `reachability_check.py` uses) at the v8/v9 curriculum target (Y=0.02) showed −15° left the point genuinely *unreachable* — not close, not marginal, outside the workspace entirely for any joint combination — while v5/v6's original target (Y=0.08) had converged to within 2.4mm precisely because it sat almost exactly at that −15° boundary. −50° gives the v8/v9 target a comfortable ~13° margin from the new limit (0.00cm IK residual) instead of being pinned at the edge; verified before the fix mattered `reachability_check.py`'s general bin-floor grid also improved, 88.9%→100%. The original 0°→−15° widening (below) left a dead zone between the two shoulders (±11 cm) that neither arm could reach at all — confirmed via `reachability_check.py` dropping to ~6% coverage; that fix stands independently of this one. A wider negative (adduction) allowance is also anatomically plausible for a shoulder joint, not purely a reachability hack. | Yes |
| Joint velocity limit | 120°/s (2.0944 rad/s), all arm joints | Placeholder — not derived from a real motor speed/gear-ratio spec (unconfirmed per ARCHITECTURE.md §3/§9). | Yes |
| Joint torque (effort) limit | 3.0 N·m shoulder joints, 2.0 N·m elbow | Placeholder — not derived from ODrive Mini current limit (20 A per the firmware sample config) x an actual motor torque constant, since no confirmed motor model/Kt exists yet. | Yes |
| Sign convention | shoulder_pitch axis = lateral (Y), same both sides. shoulder_roll axis = fore-aft (X), **mirrored** between sides (left: +X, right: −X) so a positive command means "raise arm away from body" symmetrically on both arms. elbow axis = Y, same both sides, 0°=straight/positive=flexion. | A concrete, internally-consistent choice was needed to build anything; verified correct (not just internally consistent) by `fk_sanity_check` in `rollout_smoke_test.py`, which confirms shoulder_roll actually displaces the end effector sideways rather than spinning the arm in place. | Pre-answers ARCHITECTURE.md §9's open sign-convention item for simulation purposes only — real hardware sign convention still needs confirming independently. |
| Position-actuator gains | kp=60, kv=6.0 (all 6 arm joints) | Empirically tuned via a step-response sweep (target 10°, checked settling error over the final 20% of a 3 s rollout) — kp=30 initially chosen but left ~10° of steady-state-adjacent error before tuning; kp=60/kv=6 settles to within 0.19°, well inside the 2° tolerance. | No — MuJoCo-only control parameter, not a hardware claim (though the real ODrive's position-control gains would need their own independent tuning on hardware). |
| Integrator | `implicitfast` (MuJoCo option), not the default `Euler` | The default explicit/semi-implicit Euler integrator was empirically unstable for these joints: a kp on the order of tens-to-hundreds N·m/rad acting on the arm segments' small inertia gives a natural frequency high enough (relative to the 500 Hz physics rate) that Euler integration diverged within ~20 steps instead of settling. `implicitfast` is MuJoCo's documented fix for exactly this "stiff position actuator on a low-inertia link" scenario, at negligible extra cost, without needing to shrink the timestep. | No — numerical-methods choice, not a hardware claim. |
| **shoulder_yaw joint (added 2026-08-11)** | New innermost joint per arm: `{side}_shoulder_yaw_joint`, parent=torso_link, axis=Z (vertical), range ±90° (−1.5708 to 1.5708 rad), same kp/kv/effort/velocity spec as shoulder_pitch. `shoulder_pitch_joint` is now its child (origin moved to (0,0,0), the yaw joint owns the old (0, ±0.11, 0.05) shoulder mount offset). Arms are now **4-DOF**: shoulder_yaw → shoulder_pitch → shoulder_roll → elbow. | The prior 3-DOF (pitch+roll+elbow) chain gave full elevation/azimuth *within the sagittal+frontal planes centered on the shoulder*, but no way to rotate that whole plane around the vertical axis — observed as the arm/forearm being unable to swing out of the front-mounted head camera's FOV without fighting the pitch/roll coupling. shoulder_yaw is the "turret" DOF that reorients the entire downstream chain as a rigid unit. All existing IK-solved curriculum poses (`ready_pose_rad`, `mid_carry_pose_rad`, `near_dest_pose_rad` in `config/*.yaml`) reproduce their exact pre-change end-effector position at `shoulder_yaw: 0.0` — not re-solved, just extended with a neutral 4th value. | **Yes — this is a simulation-only kinematic change.** The real robot's arm hardware (ARCHITECTURE.md §2 "Arms"/"Actuator count") still has only the original 3 actuators/arm (6 arm ODrive Minis total) — no shoulder-yaw actuator has been sourced, mounted, or wired. If the real robot needs to replicate this capability, that's a separate, not-yet-made hardware decision (new ODrive Mini + motor, CAN wiring, mechanical mount) — do not treat this row as implying that decision has been made. |
| shoulder_yaw self-collision exclude | `build_model.py` adds an explicit MuJoCo `<contact><exclude>` between `{side}_shoulder_yaw_link` and `{side}_upper_arm_link` | Discovered building the joint above: MuJoCo auto-excludes contact only between *directly adjacent* parent/child body pairs, so the new intermediate yaw link's 0.025 m actuator-lump proxy box — sized/positioned to match the pre-existing tightly-packed shoulder cluster — interpenetrated `upper_arm_link` (two joints downstream) by ~1 cm at rest. The resulting repulsion force was strong enough to hold shoulder_pitch/shoulder_roll within ~1° of zero regardless of commanded target (caught by `rollout_smoke_test.py`'s `step_response_settle`, which briefly regressed to a 10.8° settle error before this fix). Verified root-cause (not a tolerance workaround): re-ran with the exclude added and all smoke-test tolerances returned to their original pre-change values (`rollout_smoke_test.py`, `contact_smoke_test.py` both pass unmodified). | No — collision-modeling fix for the actuator-lump proxy geometry, not a hardware claim. |

## Gripper (Milestone 3) — sim-only proposal, no gripper exists on the real robot

**Flagged prominently: every value in this table is a proposed spec for simulation purposes
only, not a hardware design.** The real robot's arms currently terminate at the elbow.

| Parameter | Value | Rationale | Confirm before real hardware? |
|---|---|---|---|
| Mechanism | Parallel-jaw, 2 prismatic fingers per side. finger1 is independently actuated; finger2 mechanically mirrors it via a MuJoCo `<equality joint>` constraint (finger2_qpos = finger1_qpos, direct 1:1 — finger2's joint axis is pre-flipped in the URDF so a direct copy produces symmetric opening, not a negated one). | Simplest mechanism that can grasp small objects; equality-constrained mimic joints are a standard MuJoCo pattern for coupled gripper fingers. URDF alone can't express the coupling, which is the concrete case motivating the URDF/MJCF split (build_model.py adds the constraint). | Yes — entire mechanism is a proposal, not a chosen design. |
| Max jaw opening | 0.06 m (0.03 m travel per finger) | Sized to grasp small bin-picking objects (a few cm) with margin. | Yes |
| Finger dimensions | 0.015 × 0.008 × 0.05 m (W×T×L) box, PETG density 1200 kg/m³ → ~7 g each | Small, light placeholder finger; same material assumption as the arm tubes. | Yes |
| Finger rest-position offset | Each finger's collision geometry is offset ±0.004 m (half its own thickness) from its joint's local origin, so at qpos=(0,0) the fingers sit edge-to-edge (closed) rather than overlapping. | **Load-bearing fix, not cosmetic:** without this offset both finger collision boxes were coincident at rest, and the resulting contact-repulsion force fought the finger1 actuator and the finger2 equality constraint badly enough that neither converged anywhere near its commanded target (finger1 stuck ~7% of the way to a full-open command). Caught by `contact_smoke_test.py`. | No — geometric/numerical correctness fix, not a hardware claim. |
| Gripper base | 0.03×0.04×0.02 m box, density 5000 kg/m³ → 0.12 kg | Lumped mass standing in for an unchosen small actuator (e.g. a linear servo or small motor+leadscrew) driving the jaw. | Yes |
| Fingertip friction | sliding=1.2, torsional=0.005, rolling=0.0001 | Higher sliding friction than MuJoCo's default (1.0), assuming a rubberized grip pad. | Yes |
| Position-actuator gains | kp=200, kv=10 (finger1 only, both sides) | Same step-response tuning approach as the arms; the much lighter/shorter-travel prismatic joint needed higher kp than the arms to settle promptly. Verified via `contact_smoke_test.py`'s open/close cycle (finger2 tracks finger1 within 1 mm outside a ~0.3 s settling transient after each target change). | No — MuJoCo-only control parameter. |

## Camera (Milestone 4)

| Parameter | Value | Rationale | Confirm before real hardware? |
|---|---|---|---|
| Mount body | Rigid, fixed to `torso_link` (MJCF-only — not part of the URDF) | No head/neck link exists in the architecture (torso is the topmost segment) and no camera has been chosen for the real robot at all (ARCHITECTURE.md §7). A torso-fixed camera co-moves with the gimbal-driven torso tilt the same way a head-mounted camera would track gaze via neck motion, so it's a reasonable functional stand-in. | Yes — revisit if a dedicated head/neck mechanism is ever planned. |
| Mount offset | (+0.07, 0, +0.13) m from torso origin, pitched 30° down from horizontal | Placed near the top-front of the torso box, angled toward the workspace. **Stale since v11's torso shrink** (0.18×0.12→0.09×0.07): the box's front-face half-extent is now 0.045 m, so this +0.07 m offset now sits ~2.5cm in front of the box rather than recessed within it — cosmetic (doesn't affect what the camera sees or any check script), but the offset hasn't been re-tuned to the new box size. | Yes |
| Resolution | 640×480 default (RL training), 1280×720 debug (manual inspection, not used in training) | 640×480 is a standard small RL-image-observation resolution, fast to render at the step rates RL training needs. | No — a config choice, not a hardware claim. |
| Horizontal FOV | 58° | Representative of a commodity Jetson/USB3-compatible global-shutter RGB module (e.g. e-CAM/See3CAM class, or a RealSense-class module's RGB stream) — no real camera has been chosen yet. | Yes |
| FOV conversion | Horizontal FOV → MuJoCo's vertical `fovy`, computed at build time from the configured resolution's aspect ratio: `fovy = 2*atan(tan(hfov/2) / aspect)` (`scripts/build_model.py:hfov_to_fovy`) | Camera specs are conventionally quoted as horizontal FOV, but MuJoCo's `<camera fovy>` is vertical — computing this at build time (rather than hardcoding a fovy number) keeps the effective FOV correct if `resolution_default`'s aspect ratio ever changes. | No — arithmetic, not a hardware claim. |
| Offscreen framebuffer | `<visual><global offwidth="1280" offheight="720"/></visual>` in scene.xml, sized to the largest resolution any script requests | `mujoco.Renderer` errors if asked to render larger than the model's configured offscreen buffer — this must cover `resolution_debug`, the largest declared resolution, not just `resolution_default`. | No — MuJoCo API requirement, not a hardware claim. |
| Offscreen rendering on this Windows dev machine | Confirmed working (`camera_smoke_test.py`, non-blank renders at both configured resolutions; separately verified with a posed-arm render matching a hand-computed expected framing) | Flagged as a known cross-platform risk in the plan (GL context behavior differs from Linux/EGL) — resolved here, before the Gymnasium env (Milestone 7) depends on it. | No — environment capability, confirmed working. |
| **Mount position/orientation (revised 2026-08-13)** | Moved off the torso-forward "head camera" placement to `mount_pos: [0.45, -0.12, 0.15]`, `yaw_deg: 180`, `pitch_down_deg: 42` — an external, stationary camera on the far side of the table from the robot, looking back across both boxes toward the robot. Still implemented as a `torso_link`-fixed MJCF camera (simplest — no new body), which is only geometrically equivalent to a true world-fixed camera because the robot base never moves in this sim (M1). | The RGB-D policy oscillated near-but-not-touching the cube: root-caused to the (2026-08-12) `camera_occlusion_penalty` reward term fighting `close_approach_weight` whenever the only reachable approach path crossed the robot-mounted camera's own sightline to the cube (confirmed: full source-box spawn range is IK-reachable with 0 residual under random-restart, so it wasn't a kinematic gap). Moving the camera across the table makes the cube sit in the foreground for nearly the whole approach — occlusion becomes structural rather than something the reward has to teach against (verified: the occlusion penalty no longer fires for a scripted "typical approach from the robot's own side" case, and 100%/7x7-grid coverage of the source box's full randomized spawn range confirmed via the camera's real frustum, not just its center). | **Yes — critical, this is no longer "a head camera," it's a fixed workspace camera. Revisit deliberately before any real-hardware camera decision** (see `docs/ARCHITECTURE.md` "Camera" section) — do not assume this sim convention transfers to the real robot without that discussion. |

### Post-Milestone-8 fix: camera field-of-view coverage

**Real bug, caught by watching an actual trained-policy rollout, not by the original build-time
checks.** The head camera's mount offset/pitch/FOV all passed every Milestone 4/5/7 verification
(`camera_smoke_test.py`, `check_vision_env.py`) because those checks only ever rendered the object
at the bin's *center* — which happened to be in frame. The real environment randomizes the
object's spawn position across the whole bin footprint (`sim_env/domain_randomization.py`), and at
the original mount_pos `[0.07, 0, 0.13]` / `pitch_down_deg: 30` / `horizontal_fov_deg: 58`, only
about **55%** of that randomized spawn area was ever actually in frame — confirmed both by a
rendered policy rollout showing an empty bin, and by a new dedicated check,
`scripts/check_camera_coverage.py`, which samples object positions with the exact same
distribution `randomize_objects()` uses and checks each against the camera's real frustum (not a
single static snapshot). Fixed by raising the mount to the torso's top edge (`z: 0.15`), steepening
the pitch to `55°`, and widening the lens to `90°` horizontal FOV (physically realistic for a
close-range workspace camera — many real robot head/wrist cameras use 90-120° lenses for exactly
this reason) — swept against `check_camera_coverage.py` rather than hand-tuned, now at 100%
coverage, and reconfirmed against a real policy rollout (object clearly visible throughout, per
`docs/camfix_pov_frame0.png`).

**Lesson generalized:** a visual check against one fixed, convenient scene state (object at bin
center) is not equivalent to verifying coverage across the actual randomized distribution the
environment produces — this is why `check_camera_coverage.py` samples from
`domain_randomization`'s own distribution rather than asserting against a single snapshot.

| Parameter | Old value | New value | Confirm before real hardware? |
|---|---|---|---|
| Mount offset | (+0.07, 0, +0.13) m | (+0.07, 0, **+0.15**) m | Yes (as before — placeholder spec either way) |
| Pitch | 30° down | **55°** down | Yes |
| Horizontal FOV | 58° | **90°** | Yes |
| Spawn-area coverage | 55% (`check_camera_coverage.py`) | **100%** | No — verification result, not a hardware claim |

## Scene / environment (Milestone 5)

| Parameter | Value | Rationale | Confirm before real hardware? |
|---|---|---|---|
| Table position | Center (0.205, 0) m | Went through three iterations, each caught by a verification script rather than eyeballed: (1) originally planned 0.30 m forward of the mount point, but `reachability_check.py` (ikpy against the real URDF) showed the bin center was ~0.36 m from each shoulder, just past the ~0.33 m max arm reach (upper 0.18 m + forearm 0.15 m) — only ~6% of bin-floor points reachable. (2) Pulled in to 0.15 m to fix reach, but that made the (necessarily bin-sized) table top overlap the arms' own resting-at-ease position (hanging straight down passes through x=0, and a table top wide enough to support the bin unavoidably extends back to meet it) — caught by `check_scene_settle.py`'s spawn-interpenetration check, not by reachability. (3) Settled at 0.205 m with a tabletop sized to the bin rather than oversized (see below): 88.9% reachable, 0 mm spawn interpenetration. | No — sim workspace layout, not a hardware claim (though it does illustrate that this arm length needs a fairly close workspace). |
| Table dimensions | 0.36×0.30 m top (sized to the bin, not oversized), 0.03 m thick, single 0.16×0.16 m pedestal from floor to 0.75 m | Originally 0.5×0.5 m; shrunk during the table-position iteration above so the tabletop's near edge stops short of where the resting arms hang, rather than fighting that constraint with position alone. Standard table height; single pedestal is a simplification vs. 4 legs, cheap to simulate and irrelevant to the manipulation task. | No |
| Bin | 0.30×0.20×0.10 m inner, 0.005 m walls, centered on the table | Sized to plausibly hold a handful of small graspable objects. | No |
| Object roster | 4 fixed slots, shapes cycle [cube, cylinder, sphere, cube], half-size ~0.0145 m, mass ~30 g | MuJoCo geom type/size are compile-time properties (can't be changed without recompiling), so true per-episode shape/size randomization isn't practical at RL step rates — a fixed roster with per-episode pose/count/friction randomization is the standard approach (see `sim_env/domain_randomization.py`). | Not applicable — sim/task design choice. |
| Object count randomization | 1–4 active per episode; inactive slots parked at world (10+slot, 10, −5) | Keeps the compiled model's body count fixed while still exposing count as an episode variable — parking far below the ground plane keeps inactive objects out of the workspace and camera frustum without deleting them. | No |
| Object friction | Nominal sliding=0.8, torsional=0.005, rolling=0.005 (±20% jitter per episode) | MuJoCo's own default rolling friction (0.0001) is realistic for a mathematically perfect sphere but means any sphere that picks up spin off an uneven landing rolls at a small constant velocity almost indefinitely (confirmed empirically: raising rolling friction to 0.03 didn't change the steady-state outcome either — a spinning, non-slipping sphere has zero relative velocity at its contact point, so kinetic friction has nothing to dissipate). This is correct physics, not a bug, but isn't representative of the slightly-deformable small objects this roster approximates, and made a bounded-step settle check impractical. `check_scene_settle.py` therefore checks linear (not angular) velocity against an absolute threshold, not relative decay. | Yes — replace with measured friction once real graspable objects are chosen. |
| Object friction jitter, count/pose randomization determinism | Verified via `check_domain_randomization.py`: 50 trials stay within configured ranges, same-seed calls reproduce identically | Caught a real bug during implementation: `randomize_object_friction` originally read the *current* (already-jittered) friction as its baseline each call, compounding into unbounded drift across repeated calls instead of jittering around a fixed nominal. Fixed to always reference `build_model.OBJECT_FRICTION`'s fixed baseline. | No — implementation correctness, not a hardware claim. |
| Lighting jitter | Key light position ±0.5 m, ambient in [0.2, 0.5] | Schema/plumbing only — defined now since it's plain MuJoCo model-array mutation with no rendering dependency, but not yet exercised by any code (nothing needs it until Milestone 7's camera observations). | No — RL training technique, not a hardware claim. |

## Task / RL (Milestone 6)

| Parameter | Value | Rationale | Confirm before real hardware? |
|---|---|---|---|
| Control / physics rates | control_hz=20, physics_hz=500 (25 physics substeps per control step) | Standard RL control rate; physics rate matches models/mjcf/scene.xml's 0.002 s timestep exactly (asserted at env construction). | No |
| Ready pose | shoulder_pitch=-60°, shoulder_roll=+40°, elbow=+60° (radians in config), applied to every active arm on reset | Chosen to put the EE roughly above the bin, arm partway extended — a deliberately non-trivial starting configuration (not the gravity-stable full-hang rest pose, which is both a poor RL starting point and closer to a kinematic singularity). This is the sim-scoped, not-yet-hardware-validated answer to ARCHITECTURE.md §9's open "reference zero pose" item. | Sim-only until validated on hardware, per the same flag as the M2 rest-pose convention. |
| Trajectory shaping | Velocity-only ramp (no acceleration limiting) toward the commanded target, at `max_arm_joint_velocity_rad_s`/`max_gripper_velocity_m_s` from config/env.yaml | Approximates the real ODrive's trapezoidal-trajectory position control (ARCHITECTURE.md §3) well enough for a first RL-ready environment; full accel-limiting deferred as unnecessary complexity until something concrete needs it. These velocity values duplicate humanoid.urdf's `<limit velocity="...">` by hand, because MuJoCo does not preserve URDF velocity limits on compiled joints (confirmed empirically — no `jnt_velocity_limit`-equivalent array exists post-compile), so there is no way to read them back from the model at runtime; must be kept in sync manually if the URDF's velocity limits ever change. | Sim-only approximation of the real control mode; also inherits the "Yes" flags already on the underlying velocity-limit values themselves (ASSUMPTIONS.md "Arms" table). |
| Reward shaping | distance_weight=-2.0/m, grasp_bonus=+5.0 (one-time), lift_bonus_weight=+20.0/m while grasped, step_penalty=-0.01, knockout_penalty=-5.0 | Standard dense-shaping choices (distance + event bonuses) for a first RL-ready environment; not tuned against actual training results yet (Milestone 8 is a pipeline smoke test, not a convergence run) — expect to revisit once real training data exists. | No — RL hyperparameter, not a hardware claim. |
| Success / failure | Success: grasped AND >5 cm above bin floor, held 10 consecutive control steps (0.5 s). Failure: object center + 5 cm margin leaves the bin's inner footprint ("knocked out"). | Simple, unambiguous episode-ending conditions for a first environment. | No |
| Single fixed grasp target | Exactly one object (`object_0`) is always the tracked target, regardless of how many objects are in the bin; `active_slots=[0]` is passed to `domain_randomization.randomize_objects` to guarantee it, rather than relying on the general random-slot-permutation path | True multi-object target selection (choosing *which* object to grasp, handling variable-cardinality observations) is a materially harder RL problem, deliberately out of scope for this milestone. This fixed-slot pinning was added after a real bug: without it, `randomize_objects(count=1)`'s random slot permutation left `object_0` parked outside the workspace in ~75% of episodes (1 in 4 chance it was the slot chosen active), caught by `check_env.py`'s scripted-controller reward check returning consistently near-flat reward regardless of controller quality. | No — env/task design choice, not a hardware claim. |
| Both-arms generalization (6.2) | `active_arms: [left, right]` in config/env.yaml; the env's action/observation spaces, reward (closest-arm distance), and all of `check_env.py`'s verification were written generic over `active_arms` from the start, so generalizing from 6.1's single-arm config was a config change re-verified end-to-end, not a code rewrite | Avoids a "6.1 code, then 6.2 code" split that would need to be kept in sync — one implementation parameterized by config, per this repo's config-over-hardcoding convention. | No — implementation approach, not a hardware claim. |

## Performance notes (Milestone 7, updated Milestone 8)

| Note | Value | Context |
|---|---|---|
| State-only vs. vision-inclusive step rate (env only, no learning) | ~368 steps/s state-only, ~91 steps/s with the `VisionWrapper` RGB render (~4x slowdown) | Single-process, this Windows dev machine, unoptimized (rendering every step at 640x480). |
| State-only vs. vision PPO training throughput (env + SB3 policy forward/backward) | ~88 fps state (`MultiInputPolicy` MLP), ~2 fps vision (`MultiInputPolicy` CNN feature extractor) — a ~44x slowdown, far larger than the ~4x env-only rendering slowdown above | The CNN forward/backward pass dominates once actual SB3 training (not just env stepping) is in the loop, not the rendering itself. 8000 vision timesteps took ~58 minutes wall-clock on this machine. This is the number to plan around for any future full (non-smoke-test) vision-based training run, not the env-only ~91 steps/s figure — obvious levers if throughput becomes a blocker: multiple parallel envs (`SubprocVecEnv`), a smaller CNN, or rendering less than 640x480, none implemented now since nothing has needed it yet. |

## Milestone 8 — RL training smoke test (SB3 PPO)

| Check | Result | Notes |
|---|---|---|
| State profile trains without exceptions | Pass — 30,000 timesteps, ~88 fps, ~340 s wall-clock | Checkpoint: `training/checkpoints/ppo_state_smoke_test.zip` |
| Vision profile trains without exceptions | Pass — 8,000 timesteps, ~2 fps, ~3467 s (~58 min) wall-clock | Checkpoint: `training/checkpoints/ppo_vision_smoke_test.zip` |
| `evaluate.py` runs deterministic eval episodes without crashing | Pass, both profiles | State: mean_reward=-83.12, success_rate=0.00/5. Vision: mean_reward=-91.61, success_rate=0.00/5. Zero success at these tiny smoke-test budgets is the expected, acceptable outcome per the plan — this milestone verifies the pipeline runs end to end, not that the policy has converged. |
| TensorBoard logs contain reward/loss curves | Pass | `training/logs/{state,vision}/` — served locally via `python -m tensorboard.main --logdir training/logs`. |
| Same-seed/single-env determinism on final policy weights | Pass | `scripts/check_training_determinism.py`: state profile trained twice from an identical seed (2048 timesteps, single env, no subprocess parallelism) produced bit-for-bit identical weights across all 13 policy parameter tensors — the final gate on the whole pipeline (URDF -> MuJoCo -> Gym env -> SB3). |

### Follow-up: a full (non-smoke-test) training run

After Milestone 8 itself was verified, a full 500,000-timestep state-profile run was made (checkpoint
`training/checkpoints/ppo_state_full.zip`, `--save-freq 20000` for progress checkpoints, ~46 min
wall-clock at ~88-179 fps) to see actual learning behavior, not just pipeline correctness. Reward
trend across checkpoints (`evaluate.py`, 5-10 episodes each):

| Steps | Mean reward | Grasp success |
|---|---|---|
| 30,000 (smoke test) | -83.1 | 0% |
| 40,000 | -61.3 | 0% |
| 360,000 | -50.1 | 0% |
| 440,000 | -49.0 | 0% |
| 500,000 (final) | -46.0 | 0% |

**Read honestly:** reward climbed steadily then plateaued; grasp success never left 0%. The policy
learned to reduce EE-to-object distance (the dominant reward term) but never discovered the
contact-then-hold behavior the sparse grasp/lift bonuses require — distance-shaped reward alone
didn't bridge into contact-rich manipulation at this budget. This is a real result about the
current reward shaping (`config/env.yaml`), not a pipeline failure — Milestone 8's actual gates
(trains without exceptions, evaluates deterministically, reproducible from a seed) all still pass
on this run too. If pursued further, next steps would be: a shaping term for the approach-to-contact
phase specifically (e.g. a bonus for closing the gripper near the object, not just for lifting it),
a longer budget once shaping improves, or — consistent with ARCHITECTURE.md §8's own stated
preference for the real robot — imitation learning from a handful of demonstrations, which
sidesteps this exact reward-shaping gap. None of this is implemented; flagged here for whoever
picks this up next.

Also added during this run: `scripts/render_policy_rollout.py` (renders a checkpoint's rollout to
GIF from an external camera and, optionally, the robot's own `head_camera` POV, captured from the
same synced episode) and `scripts/watch_policy.py` (drives a checkpoint live in an interactive
MuJoCo window via `mujoco.viewer.launch_passive`) — both useful for inspecting any future
checkpoint without re-deriving this from scratch.

### Reward revision (v2) — closing the approach-to-grasp gap

Implemented the "shaping term for the approach-to-contact phase" suggested above, plus a
correctness fix found while making that change:

- **Bug fix, `sim_env/bin_picking_env.py::_contact_state`** (was `_is_grasped`): the grasp check
  OR'd finger-contact across all active arms independently, so with both arms active
  (`active_arms: [left, right]`) it could report "grasped" from the left arm's finger1 touching
  plus the right arm's finger2 touching -- two different arms, not an actual enclosing grasp by
  either one. Fixed to require both fingers of the *same* arm.
- **New reward terms, `sim_env/rewards.py` + `config/env.yaml`**: `gripper_close_bonus_weight`
  (rewards the nearest arm's gripper closedness, but only once EE-to-object distance is under
  `close_proximity_threshold_m`) and `single_finger_contact_bonus` (small per-step, per-finger
  partial credit toward the full two-finger grasp). Both are dense signal for the exact gap the
  v1 run's plateau exposed: nothing previously told the policy that closing the gripper near the
  object was useful at all, so the sparse grasp/lift bonuses had to be discovered by chance.
- Re-verified `check_env.py` and `check_vision_env.py` both still pass with the new reward
  function before starting a new run.
- A fresh 500,000-timestep run (`ppo_state_v2`, same budget/config as the v1 run for a fair
  comparison, both arms active) was started from scratch rather than continuing the v1
  checkpoint -- the reward landscape changed meaningfully enough that the old value function's
  estimates would no longer be meaningful starting points.

**Checkpoint reward trend (v2, `evaluate.py`, 5 episodes unless noted):**

| Steps | Mean reward | Grasp success |
|---|---|---|
| 100,000 | -51.5 | 0% |
| 240,000 | -61.5 | 0% |
| 260,000 | -50.5 | 0% |
| 280,000 | -50.8 | 0% |
| 300,000 | -48.7 | 0% |
| 340,000 | -49.7 | 0% |
| 360,000 | -48.8 | 0% |
| 380,000 | -48.9 | 0% |
| 400,000 | -49.6 | 0% |
| 420,000 | **+12.0** (reward-hacking artifact, see below) | 0% |
| 500,000 (final, 10 episodes) | -50.6 | 0% |

### Reward revision (v2.1) — a real exploit found via live monitoring, not a design review

The 420,000-step checkpoint's 5-episode evaluation averaged **+12.0**, sharply breaking the
-48 to -61 pattern every other checkpoint showed. Before publishing that as progress, it was
traced per-episode: 4 of the 5 seeds scored a normal -41 to -53; the fifth (seed 1004) scored
**+247.9** on its own. Re-running that specific episode with per-step contact state instrumented
(`env._contact_state()`) showed `touched_f1`/`touched_f2` both `False` for all 200 steps, and
`object_pos` never changing (the object sat motionless on the bin floor the entire episode) --
yet reward held steady around **+1.87/step from step 56 onward**. Root cause:
`gripper_close_bonus_weight` (added in the v2 revision above) rewarded gripper closedness on
*every step* the EE was merely within `close_proximity_threshold_m` of the object, with no
requirement of ever touching it -- the policy had discovered it could park the gripper shut near
the object and collect that bonus indefinitely, unrelated to any real grasp progress.

**Fix:** the bonus now also requires actual finger contact (`touched_f1 or touched_f2`), not
merely proximity (`sim_env/rewards.py`). Re-verified `check_env.py` passes. The final v2
checkpoint's 10-episode evaluation (different seeds than the 5-episode checks above) came back at
a normal -50.6 -- the exploit was real but seed-dependent/sporadic, not something the whole policy
had collapsed into by the end of training.

**General lesson, not just a one-off bug:** a per-step dense reward term with no requirement of
continued task progress is farmable, and a small evaluation sample (5 episodes) can hide a single
exploiting episode inside an average that superficially looks like a breakthrough. Caught here
only because the artifact-page workflow rendered and inspected the actual footage before reporting
a suspiciously large jump as progress -- a purely numeric eval log would have reported +12.0
without explanation. Worth remembering for any future reward-shaping addition: check whether a
term can be "cashed in" without genuine progress before trusting an average.

A v3 run was started with that fix (gate the bonus on contact) -- but before it got far, a closer
audit of that fix found it was still incomplete, leading to a further redesign.

### Reward revision (v2.2) — replacing continuous bonuses with one-time milestones (structural fix)

Re-auditing the v2.1 fix (gate `gripper_close_bonus_weight` on contact) surfaced a residual
loophole: `finger2` mechanically mirrors `finger1` (a MuJoCo equality constraint, see the Gripper
table), so the two fingers can't open/close independently. If the object sits off-center, only
ONE finger may ever physically reach it. A policy could still graze that single finger against
the object and hold position, continuously farming both the (now contact-gated) proximity bonus
and `single_finger_contact_bonus`, without ever achieving or approaching a real two-finger grasp.
The general problem: **any continuous per-step bonus tied to a state the agent can passively hold
is farmable, no matter how it's gated** -- gating fixes one specific trigger condition, not the
underlying "reward for standing still in a good-looking state" structure.

**Fix (structural, not another gate):** `gripper_close_bonus_weight` and
`single_finger_contact_bonus` were removed entirely and replaced with two ONE-TIME-per-episode
milestone bonuses (`sim_env/rewards.py`, `sim_env/bin_picking_env.py`):
- `touch_bonus` (+2.0): paid once, the first step ANY finger contacts the object.
- `grasp_bonus` (+5.0, unchanged from v1/v2): paid once, the first step BOTH fingers of one arm
  contact the object simultaneously.

Both are tracked via per-episode flags (`_has_touched_this_episode`, `_has_grasped_this_episode`,
reset only in `reset()`) rather than "changed since last step" flags -- this also closes a second
potential loophole (repeatedly tapping contact on/off, or grasping/dropping/re-grasping, to
re-trigger a "just changed" bonus each time). The only reward terms that still vary continuously
are: `distance_weight * dist` (always <=0, nothing to farm -- at best you minimize an ongoing
penalty by actually closing distance) and `lift_bonus_weight * height_above_floor` while grasped
(tied to genuine object height, which cannot be faked without a real two-finger grasp holding the
object up). **Verified directly**: replaying the exact exploiting scenario (checkpoint 420k,
seed 1004) through the v2.2 reward scores -31.6, matching the normal -41 to -53 range other seeds
showed, vs. the +247.9 the same policy/scenario scored under the v2.1-patched reward.

### v3 outcome — real improvement, still no grasp

`ppo_state_v3` (500k timesteps, v2.2 reward, ~19 min wall-clock at ~439 fps -- much faster than
v1/v2 since no concurrent eval/render processes competed for CPU this run) completed the full
budget before a halfway check could apply (it finished faster than the check's cadence).

| Steps | Mean reward | Grasp success |
|---|---|---|
| 20,000 | -87.9 | 0% |
| 100,000 | -46.4 | 0% |
| 200,000 | -38.7 | 0% |
| 300,000 (best) | **-29.0** | 0% |
| 400,000 | -37.0 | 0% |
| 500,000 (final, 10 episodes) | -40.2 | 0% |

Unlike v1 and v2 (which plateaued around -46 to -61 for their entire runs), v3 shows a real,
substantial improvement curve (-88 -> -29) before drifting back up slightly after 300k -- a
genuine learning trend, not noise, and the best result across all three reward designs. Grasp
success stayed at 0% throughout regardless.

Diagnosis: the policy's action-distribution spread (`std` in the training log) narrows from ~1.0
toward ~0.48-0.67 over a run in every one of v1/v2/v3 (a normal PPO pattern) -- but combined with
v3's reward drifting back down after 300k, this is consistent with exploration narrowing around
the easy, well-shaped distance-reduction behavior before the policy ever discovers the far more
precise "close the gripper exactly on the object" behavior needed for contact. SB3's PPO defaults
to `ent_coef=0.0` (no explicit entropy bonus), so nothing in the v1-v3 configs counteracted that.

### v4 change — entropy bonus

Added `ent_coef: 0.01` to `config/train_ppo.yaml`'s state profile (wired through
`training/train_ppo.py`) -- a small, standard PPO entropy bonus (common default in robotics RL
literature, not aggressively tuned) that keeps the action distribution from narrowing as quickly,
trading some exploitation efficiency for sustained exploration later into training. This targets
the specific mechanism diagnosed above, rather than repeating the same recipe with a bigger budget.
Smoke-tested (2048 timesteps) before committing to a full run.

### v4 outcome — the fix worked mechanically, but underperformed v3

| Steps | v3 reward | v4 reward |
|---|---|---|
| 20,000 | -87.9 | -75.0 |
| 100,000 | -46.4 | -68.6 |
| 200,000 | -38.7 | -44.0 |
| 300,000 | -29.0 (v3 best) | -44.8 |
| 400,000 | -37.0 | -46.0 |
| 500,000 (final, 10 episodes) | -40.2 | -51.1 |

The entropy bonus did exactly what it was designed to do -- `std` stayed at 1.53 through the end
of training instead of collapsing to 0.48 like v3's did. But that sustained exploration never
converged into anything better: v4 trailed v3 at every single checkpoint and never approached
v3's best point. Still 0% grasp success. **A real, informative negative result**: the diagnosis
(exploration collapsing too early) was plausible, but this particular fix (blanket entropy bonus)
made things worse, not better -- reported honestly rather than reframed as a partial win.

After presenting the full v1-v4 picture (all four final results, all 0% success, v3 best overall)
the user chose to keep iterating with a structurally different lever rather than stop or switch
to imitation learning.

### v5 — curriculum spawning

Every run (v1-v4) learned to reduce EE-to-object distance efficiently regardless of reward shape
or exploration pressure, but none discovered actual contact -- pointing at an *exploration*
bottleneck (contact rare to stumble into across the full ~0.30x0.20 m bin), not a *capacity* one.

Reverted `ent_coef` to 0 (v4's fix didn't help) and added curriculum spawning
(`config/env.yaml`'s `curriculum` section, `sim_env/bin_picking_env.py`'s `_curriculum_spawn`):
the object spawns in a small 0.02 m-radius region close to one arm's ready-pose reach
(~0.21-0.23 m away, vs. up to ~0.36 m under full-bin randomization), alternating between the
left and right arm's side each episode, instead of anywhere across the full bin footprint --
still routes through `randomize_objects` first so the other 3 object slots get parked exactly as
before; only object_0's spawn position is narrowed. Verified with `check_env.py` before launching.

### v5 outcome — best reward of all five runs, still 0% grasp success

| Steps | v3 reward | v5 reward |
|---|---|---|
| 20,000 | -87.9 | -70.3 |
| 100,000 | -46.4 | -31.5 |
| 200,000 | -38.7 | -30.9 |
| 300,000 | -29.0 (v3 best) | -31.3 |
| 400,000 | -37.0 | -29.9 |
| 500,000 (final) | -40.2 | **-28.4 (v5 best)** |

Curriculum spawning produced a genuinely different training dynamic, not just a better number:
v5 converges to near-final performance by 100k steps and stays stable in the -29 to -32 band
through 500k, in contrast to v3's peak-at-300k-then-regress curve. Final eval (10 episodes,
seeded): mean_reward=-28.425, success_rate=0.00. Every evaluated checkpoint from 20k through
500k had 0% grasp success -- no exception at any point in training.

This refines, rather than confirms, the v4 diagnosis. The curriculum already places the object
close to the arm (spawn radius 0.02 m, ~0.21-0.23 m from the ready pose) and the policy reliably
converges to *near* that object early and holds position there for the rest of training without
ever crossing into contact. That is a different failure signature than v1-v4's "never reliably
gets close" pattern -- it now looks more like a last-mile precision problem (positioning the
gripper accurately enough for the fingers to actually touch the object) than a broad exploration
problem. A 64x64-unit MLP policy (SB3 PPO default, ~12k parameters) has not been ruled out as a
capacity bottleneck for that precision, and hasn't been tested with a larger network at any point
in v1-v5.

After presenting the v3-vs-v5 comparison and the refined diagnosis, next-step options given to the
user were: (a) tighten the curriculum further (smaller spawn radius, or a near-touching start
position), (b) increase network capacity to test the precision-bottleneck hypothesis, (c) switch to
imitation learning per ARCHITECTURE.md §8's existing stated preference for the real robot, or
(d) stop here and treat v5 as the working baseline. See `training/TRAINING_LOG.md` for the full
v1-v5 readable summary. The user chose (a), plus asked to also reward touching/closeness more
directly -- both folded into v6, below.

### v6 — tighter curriculum + bigger touch/grasp bonuses

**Change** (`config/env.yaml`): `curriculum.spawn_radius_m` 0.02 -> 0.006 (object now spawns
almost exactly at the target point); `touch_bonus` 2.0 -> 6.0, `grasp_bonus` 5.0 -> 12.0,
`distance_weight` -2.0 -> -3.0 (steeper). Rationale: v5 reliably got close but never touched;
theorized this could be risk-aversion (closing the last few cm risks `knockout_penalty` -5.0 for
a touch_bonus that, at 2.0, might not have been worth the risk). Both bonuses stayed one-time
per episode, so this doesn't reopen the v2 exploit -- only their size changed. `check_env.py`
passed before launch.

**Training note:** the first launch attempt died silently at ~65k/500k steps when its background
shell session was torn down (not a code/env error -- checkpoints up to 60k survived and were left
on disk). Restarted cleanly from scratch under a new run name; the full 500k-step run reported
below is that second, complete attempt.

**Outcome — reward looks worse, but a direct check shows it's a scale artifact, not a regression:**

| Steps | v5 reward | v6 reward |
|---|---|---|
| 20,000 | -70.3 | -105.4 |
| 100,000 | -31.5 | -42.9 |
| 200,000 | -30.9 | -42.8 |
| 300,000 | -31.3 | -43.5 |
| 400,000 | -29.9 | -42.5 |
| 500,000 (final) | -28.4 (v5 best) | -41.9 |

At face value v6 is worse than v5 at every checkpoint. But v6's `distance_weight` is 1.5x steeper
than v5's, so the same underlying behavior produces a more negative number by construction. A
direct, reward-independent check -- raw EE-to-object distance, computed straight from body
positions, bypassing reward weights entirely -- shows the two policies are behaviorally
indistinguishable:

| Checkpoint | mean EE-to-object distance | success rate |
|---|---|---|
| v5 final | 0.0645 m | 0% |
| v6 final | 0.0665 m | 0% |

2mm apart, within noise. Neither v6 change (tighter curriculum, 3x bigger touch/grasp bonuses)
moved the policy's actual behavior at all. This is itself informative: reward *magnitude* is not
the bottleneck, and the "risk-aversion" theory behind the bigger touch_bonus is not supported --
tripling it produced zero change in how close the policy was willing to get.

**A real finding, found while instrumenting the check above:** `ee_pos` (used for both the
distance-shaping reward and the observation vector) is `{side}_gripper_base_link` -- the
wrist/mount frame the gripper attaches to (see `robot_model.py`'s `ee_body_name`) -- not the
fingertips. Per `humanoid.urdf`'s finger geometry, the actual fingertips sit ~5cm further along
the gripper from that point. Measured directly on a real v6 rollout (seed 0):

| Reference point | mean distance to object | closest approach in episode |
|---|---|---|
| `gripper_base_link` (what reward/obs use) | 0.0660 m | 0.0528 m |
| actual fingertips (`finger1`/`finger2` geoms) | 0.0539 m | 0.0346 m |

Confirmed: the fingertips are consistently ~1-2cm closer to the object than what the policy is
rewarded and shown for. This has been true in every run so far (v1-v6) -- it is a measurement gap
in the environment, not something curriculum or bonus-size tuning could ever fix. It's a partial
explanation, not the whole story: even the truer fingertip distance still plateaus at 3-5cm, short
of actual contact. But it is the most concrete, well-evidenced lead to come out of six iterations,
and hasn't been tried.

Checkpoint: `checkpoints/ppo_state_v6.zip`. Options presented to the user: (a) fix `ee_pos` to
reference the fingertips instead of `gripper_base_link`, for both reward and observation -- the
new leading hypothesis; (b) increase network capacity (still a stock 64x64 MLP across all six
runs); (c) switch to imitation learning per ARCHITECTURE.md §8; (d) stop here, treat v5 as the
best checkpoint (v6 didn't change behavior). See `training/TRAINING_LOG.md` for the full v1-v6
readable summary.

### v7 — fingertip reference point (aborted, superseded by v8)

Implemented option (a) above: `BinPickingEnv._ee_pos()` now returns the midpoint between the
`finger1`/`finger2` collision geoms, used for both the distance-shaping reward and the `ee_pos`
observation, replacing `gripper_base_link`. `robot_model.ee_body_name`/`ee_body_id` stayed (still
used by `check_env.py`'s Jacobian computation, a fine proxy since it's rigidly attached to the
same arm DOFs) but is no longer what the reward/observation see. `check_env.py`'s scripted
P-controller test updated to steer toward the same fingertip point it now validates. All checks
(`check_env.py`, `check_model.py`) passed.

Launched a 500k-step run. The first attempt died silently at 65k/500k when its background shell
session was torn down (unrelated to the code change); restarted cleanly and reached 340k/500k
before being **intentionally stopped** -- while it was running, watching v6's rendered rollout
surfaced the wall-clearance finding below, which made it clear v7 was training under the same
physically-blocked curriculum target as v5/v6 and was therefore unlikely to produce a clean signal
regardless of the reference-point fix. Its surviving checkpoints (100k/200k/300k/340k, 5 episodes
each) showed 0% success and reward plateauing around -40 -- consistent with that read, not
conclusive on their own. Not treated as v7's "final" result; the fix itself carried forward into
v8 rather than being re-tested alone.

### v8 — wall-clearance fix: first-ever finger contact

**The finding, from watching v6's re-rendered rollout (user-reported: "the cube is at the edge of
the bin and the hand is on the other side of the bin so it gets reward for being close but its
realy just pressing into the bin"):** the gripper was visibly pressed into the bin wall next to
the object, not on the object. Quantified: the gripper's max jaw opening is 0.06 m
(`docs/ASSUMPTIONS.md` "Gripper" table), but the v5/v6/v7 curriculum targets (Y=±0.08) left only
0.02 m of clearance to the nearest wall (bin inner half-depth 0.10 m) -- physically less than a
third of what the gripper needs to open around the object. This was true for every run since v5
introduced the curriculum, independent of reward shape or reference point, and is the leading
explanation for why none of them ever made contact.

**Changes** (`config/scene.yaml`, `config/env.yaml`): bin wall height cut to 1/3 (0.10 -> 0.033 m
inner Z -- also addresses separate user feedback that tall, 60%-alpha walls rendered as a closed
aquarium; wall rgba alpha was already lowered 0.6->0.2 for the same reason, `build_model.py`);
curriculum target Y moved from ±0.08 to ±0.02, giving 0.08 m clearance to the wall (vs. the
gripper's 0.06 m jaw). Neither change touches X/Y bin footprint, floor height, or knockout-margin
logic (XY-only). `check_model.py`, `check_env.py`, and `reachability_check.py` (88.9% reachable,
gate is 80%) all passed before launch. Combined with v7's (carried-forward, not independently
re-tested) fingertip reference point fix.

**Outcome:**

| Steps | reward | episodes with contact (of 10) |
|---|---|---|
| 20,000 | -119.7 | 0 |
| 100,000 | -54.2 | 1 |
| 200,000 | -54.2 | 2 |
| 300,000 | -54.4 | 2 |
| 400,000 | -52.1 | 1 |
| 500,000 (final) | -51.6 | 2 |

**First-ever finger contact in this project.** v1 through the aborted v7 all showed exactly zero
contact across every evaluated checkpoint. v8's final checkpoint achieved contact
(`_has_touched_this_episode`, verified via the environment's own contact-milestone flag, not
eyeballed) in 2 of 10 evaluation episodes; contact first appears around 100k and plateaus at
10-20% of episodes, never climbing further. Success rate (full 2-finger grasp + lift + 10-step
hold) remained 0% throughout -- even in touching episodes, only one finger ever made contact
(`touched` fires, `grasped`, which requires both fingers simultaneously, never does).

Raw reward (-51.6 final) is numerically similar to v6's plateau (-41.9) but on an apples-to-apples
basis this time (same `distance_weight`, -3.0, in both) -- v8 sits a bit worse on raw reward
despite the genuine behavioral improvement, likely because episodes that make contact and then
fail to grasp risk more knockout penalties than episodes that never approach that closely at all.

Checkpoint: `checkpoints/ppo_state_v8.zip`. The wall-clearance diagnosis is confirmed real (contact
was physically impossible before, now happens in ~20% of episodes) but is a partial fix, not the
full answer -- the remaining gap is single-finger graze vs. a genuine two-finger grasp, which reads
as a precision/control problem rather than an obstruction problem. Options presented to the user:
(a) the queued-but-disabled `reward.stuck` anti-stall penalty (`config/env.yaml`, added this
session per user request -- penalizes the closest arm's EE for staying near-motionless too long,
on the theory that touch-then-freeze is exactly the pattern a stuck-penalty targets); (b) increase
network capacity; (c) switch to imitation learning; (d) stop here with v8 (first checkpoint to ever
make contact) as the new baseline. User chose (a).

### v9 — anti-stall penalty (regression: made contact rate worse, not better)

**Change:** flipped `config/env.yaml`'s `reward.stuck.enabled` to `true` (was added, off by
default, alongside v8's fix). Continuous penalty (-0.05/step) once the closest arm's EE moves less
than 1mm for 15+ consecutive steps. Verified mechanically before launch (zero-action rollout
correctly triggered the penalty after the threshold; `check_env.py` passed).

**Outcome:**

| Steps | reward | episodes with contact (of 10) |
|---|---|---|
| 20,000 | -127.1 | 0 |
| 100,000 | -64.5 | 1 |
| 200,000 | -61.4 | 0 |
| 300,000 | -58.3 | 0 |
| 400,000 | -55.4 | 0 |
| 500,000 (final) | -60.8 | 0 |

**A clear regression, not noise.** v8 achieved contact in 10-20% of episodes at every checkpoint
from 100k onward, consistently across four checkpoints. v9 managed exactly 1 touch across all 60
evaluated episodes (10 x 6 checkpoints) -- essentially zero.

**Root-caused, not just observed.** Instrumented a v9 rollout to count how often the stuck penalty
actually fires: **48% of all steps.** Not a rare correction for pathological freezing -- a
dominant, near-constant pressure across roughly half of every episode. Likely mechanism: precise
reaching/grasping inherently requires slowing down and holding carefully still during final
approach (real grasp controllers decelerate on purpose near contact); a blanket "keep moving >1mm
every 15 steps or get penalized" rule can't distinguish that from unproductive idling, and likely
discouraged exactly the careful slow-approach behavior that led to v8's contact events.

One specific hypothesis was checked and **ruled out** before settling on the above: that
`_ee_pos()`'s fingertip-midpoint reference might be structurally blind to the gripper closing
(since the two fingers move symmetrically via the mimic constraint, their average position could
in principle stay fixed as they close). Directly measured via a qpos sweep (arm frozen, gripper
swept qpos 0->0.03): the midpoint moved ~1.5cm across the full travel, well above the 1mm
threshold -- so gripper-closing motion alone is NOT invisible to the detector. The over-firing is
broader than that single mechanism, consistent with the "penalizes careful slow approach in
general" explanation above.

Checkpoint: `checkpoints/ppo_state_v9.zip`. Options presented to the user: (a) revert to v8's
config (`reward.stuck.enabled: false`) and treat v8 as the working baseline; (b) retune the
penalty much more conservatively -- e.g. only apply once `is_touching` is already true (so it can
never discourage the approach itself, only genuine post-contact freezing), or a far longer
`steps_threshold` (~40-60 steps / 2-3s) so brief careful slowdowns aren't caught; (c) increase
network capacity instead; (d) switch to imitation learning. See `training/TRAINING_LOG.md` for the
full v1-v9 readable summary.

### v10 — kinematic reachability fix (widened shoulder_roll)

**The finding, from a user hunch after watching v9's rollout** ("I don't think your joint config
is able to reach the cube"): checked directly rather than assumed. A crude Jacobian-transpose
controller (same style as `check_env.py`'s scripted test) driven at the exact v8/v9 curriculum
target (Y=0.02) for 2000 steps -- 10x an RL episode's budget -- converged to a steady state 6cm
short, with `shoulder_roll` pinned exactly at its then lower limit (−15°/−0.2618 rad). Comparing
against the original v5/v6 target (Y=0.08): that one converged to within 2.4mm, *also* with
`shoulder_roll` pinned at the same limit -- meaning v5/v6's target was only barely reachable, right
at the workspace boundary, and v8's "wall clearance" fix (moving the target closer to the bin
centerline, away from the wall) had unknowingly moved it from *barely reachable* to *genuinely
unreachable*, fixing one problem while worsening a different, previously-invisible one.

Confirmed with the authoritative method (ikpy/LM, same solver `reachability_check.py`'s gate uses,
not the crude Jacobian-transpose test -- that one turned out to just be a poor/slow-converging
numerical method for this configuration, not evidence of a true kinematic wall; its 6cm/5.5cm
results before/after the fix are both misleading about the underlying reachability, only useful as
motivation to check properly): at the old −15° limit, Y=0.02 has **no exact solution at all** for
any joint combination -- confirmed via the same LM solver used everywhere else in this project, not
just the crude test.

**Change** (`models/urdf/humanoid.urdf`): `shoulder_roll`'s lower limit widened −15° → **−50°**
(−0.2618 → −0.8727 rad), both arms (mirrored). Chosen empirically: −35° made Y=0.02 solvable
(0.47cm residual) but still pinned exactly at the new boundary (no margin, same failure mode as
v5/v6's original target); −50° gives a genuinely comfortable margin (0.00cm residual, solved angle
~13° clear of the limit). A wider negative (adduction) allowance is anatomically plausible for a
shoulder joint, not purely a reachability hack, though still a sim-only placeholder pending real
hardware confirmation like every other joint-range value in this table.

**Verification:** `check_model.py`, `check_env.py` both pass. `reachability_check.py`'s general
bin-floor grid gate *improved* (88.9% → 100%), not just the one specific target point -- no
regression elsewhere from the wider range.

**Important caveat, stated honestly:** this removes a genuine *impossibility* (no arm configuration
could reach the target before; now one can, with margin) -- it does not guarantee the RL policy
will easily *find* that configuration through training. A kinematic solution existing is necessary
but not sufficient; a small 64x64-MLP policy still has to discover the right multi-joint
coordination via exploration. Also reverted `reward.stuck.enabled` back to `false` (v9's
regression) for this run, so the reachability fix is the one new variable being tested, not
compounded with a mechanism already shown to hurt.

**Outcome: fix verified correct, still 0/10 contact.**

| Steps | reward | contact (of 10) |
|---|---|---|
| 20,000 | -90.0 | 0 |
| 100,000 | -117.7 | 0 |
| 200,000 | -52.0 | 0 |
| 300,000 | -51.4 | 0 |
| 400,000 | -51.5 | 0 |
| 500,000 (final) | -51.3 | 0 |

Zero contact across all 60 evaluated episodes (10 x 6 checkpoints) -- worse than v8's consistent
10-20%, despite the target now being genuinely reachable (verified, not assumed). A per-step
trajectory check (correcting an arm-index bug in an earlier draft of the diagnostic script, which
had accidentally always read arm index 0 regardless of which side the curriculum picked that
episode) shows the policy does get close -- 4.6cm, 5.0cm, and 9.1cm minimum distance across 3
sampled episodes, the same range v8/v9 plateaued at -- it just still doesn't cross into contact.

So the fix was real, verified, and necessary (an actual kinematic impossibility was removed), but
this run's data says reachability was not the dominant blocker after all: fine-motor precision in
the already-close range is still the wall, same as it's looked since v8. The honest caveat stated
before launching this run held: reachability existing doesn't guarantee the policy easily finds it.

One unconfirmed hypothesis for a future iteration: widening `shoulder_roll`'s span (135° -> 170°)
also widens what a fixed unit of policy action/exploration noise corresponds to in absolute
degrees -- the same policy precision now maps to coarser joint control, which could make
final-approach positioning harder without a larger training budget. Not confirmed, flagged only.

Also fixed incidentally this run (found by another contributor mid-session): `training/train_ppo.py`
wasn't wrapping the env in SB3's `Monitor`, so `rollout/ep_rew_mean` was never written to
TensorBoard for v1-v9 -- only `train/*` loss diagnostics were visible there. Fixed; v10 onward logs
proper reward curves to TensorBoard.

Checkpoint: `checkpoints/ppo_state_v10.zip`. v8 remains the only checkpoint across all ten runs to
ever achieve contact. See `training/TRAINING_LOG.md` for the full v1-v10 readable summary.

## Suction pick-place (independent task track)

A second, independent RL task alongside bin-picking -- own scene, own env class, own reward, own
training pipeline -- per "modular so additional objects and tasks can easily be added later"
rather than overloading `BinPickingEnv` with a second mode. Bin-picking's files (`config/env.yaml`,
`config/scene.yaml`, `sim_env/bin_picking_env.py`, `sim_env/rewards.py`,
`training/train_ppo.py`) are untouched by this track.

**Furniture:** one table (`config/pick_place_scene.yaml`), two small open-top boxes on it --
source ("left", where the cube always spawns) and destination ("right", the target). Built by
`scripts/build_model.py`'s `_add_pick_place_furniture`/`_add_open_box` (factored out of the
bin-picking task's inline bin-wall code so both tasks share the box-drawing geometry instead of
duplicating it a third time).

**Single arm, not two:** both box centers (`(0.16, 0.06)` source, `(0.16, -0.06)` destination,
world XY) were verified reachable by the RIGHT arm ALONE via `ikpy` against `humanoid.urdf` before
being committed -- same method `reachability_check.py` uses, run ad hoc for this check (see
scratchpad `check_pickplace_reach.py` for the session's verification script). That means the whole
pick-then-place motion is a single-arm task, not a two-arm handoff, which is materially simpler to
learn. `config/pick_place_env.yaml`'s `active_arm: right` is a real constraint, not an arbitrary
choice -- moving either box outside this verified-reachable pair would reopen the two-arm-handoff
problem.

**Suction, not finger grasping:** the gripper's finger joints are held at a fixed pose
(`gripper_fixed_pos_frac`, not an RL action) and act as a mounting platform; the actual suction
contact point is the gripper base's own collision geom
(`{side}_gripper_base_collision`, already existed for the finger-grasp gripper). Attachment is a
MuJoCo weld equality constraint between `{side}_gripper_base_link` and `object_0`
(`scripts/build_model.py:_add_suction_weld`), compiled **inactive** and toggled per control step
via `data.eq_active` (a plain mutable `MjData` array added in MuJoCo 3.1+ specifically for this
kind of runtime-togglable constraint -- no model recompilation needed, so it's cheap enough to
gate every step during RL training). At the moment of attach, `model.eq_data`'s anchor/relpose is
overwritten with the CURRENT relative pose between gripper and cube
(`SuctionPickPlaceEnv._attach_suction`), so the cube welds on wherever it actually is, not a pose
baked in at compile time. Attachment requires BOTH the action commanding suction on AND real
contact (`_is_suction_touching`, an actual MuJoCo contact pair, not just proximity) AND the EE
within `suction.max_attach_distance_m` of the cube -- an action alone can't attach through open
air. Verified end-to-end (contact detection at near/far offsets, weld rigidity under arm motion,
release-then-fall) in the session's scratchpad `check_suction_mechanism.py` before any training
compute was spent, mirroring this project's standing "verify each milestone before spending
compute" discipline.

**Reward** (`sim_env/pick_place_rewards.py`): adopts the bin-picking task's hard-won "no
continuous farmable bonus" structural lesson (its v2 exploit history) from the start rather than
re-discovering it — distance-to-cube shaping while unattached, one-time `attach_bonus`, continuous
lift/carry-toward-destination shaping while attached (both tied to genuine cube pose, can't be
faked without a real attach), one-time `place_bonus` on success, plus small continuous penalties
for wasted motion (`||action - prev_action||`), arm-vs-furniture collision, and a one-time penalty
for releasing suction while the cube is outside the destination box footprint ("dropping").

**Success/failure:** success = cube at rest (linear speed below `success.max_speed_m_s`) inside the
destination box footprint, released (not attached), sustained for `success.hold_steps` consecutive
control steps. Failure = cube center falls below `table_top - failure.table_edge_margin_m`, or
episode timeout (`episode_max_steps: 300`, longer than bin-picking's 200 -- pick-then-place is a
strictly longer task).

**Domain randomization** (`sim_env/domain_randomization.py`): `randomize_cube_in_box` (pose within
the source box, minus wall keep-out margin) and `randomize_cube_physics` (+/- friction and mass
jitter around the nominal cube; mass jitter also scales `body_inertia` proportionally so the two
stay physically consistent, since MuJoCo doesn't recompute inertia from `body_mass` automatically).

**pp_v1 -> pp_v2 fix (claw removal + larger boxes):** pp_v1 plateaued at 0% pick success with the
policy's action std collapsing fast, and the user caught the real cause by watching the rendered
rollout: the finger-grasp gripper's collision geoms (leftover from the bin-picking task's end
effector -- prong-shaped boxes sticking ~5cm past the gripper base, still physically present and
colliding even though this task never actuates them) could snag on the box walls, invisibly to
both the reward and `_is_arm_collision` (which only checks `upper_arm`/`forearm`). Fixed via
`scripts/build_model.py:_neutralize_gripper_fingers`, called only from the
`task=="suction_pick_place"` branch of `build_spec`: shrinks both sides' finger collision geoms to
near-zero, sets `contype=conaffinity=0` (fully excluded from collision resolution), and zeroes
their `rgba` alpha (no longer rendered). Bin-picking's `build_spec` path never calls this, so its
finger-grasp gripper is untouched. Verified: compiled model shows the expected near-zero
size/zero-contype for all 4 finger geoms; a rollout that deliberately drives the arm into a box
wall recorded 0 finger-vs-furniture contacts over 150 steps (previously uncounted collisions were
real).

Separately, the user asked for the boxes' Y (side-to-side) dimension tripled, `0.08m -> 0.24m`.
Keeping the old box centers would have overlapped the two boxes by ~0.16m and pushed much of the
source box outside the right arm's reach -- caught by re-running the `ikpy` reachability check
(promoted to a permanent gate, `scripts/check_pickplace_reach.py`, checking all 4 corners of both
boxes, mirroring `reachability_check.py`'s role for the bin-picking task) rather than assuming the
old centers would still work. Findings: the right arm's reach envelope at this table height/X tops
out around Y=+0.18 to +0.19 (adduction-limited -- reaching toward/past the body's centerline, the
same shape of constraint that drove the bin-picking task's v10 `shoulder_roll` widening), and fails
consistently from Y=+0.20 on; the destination direction (more negative Y, abduction/away from the
body) has much more headroom, verified reachable past Y=-0.38. New box centers: source
`(0.16, 0.02)` (was `(0.16, 0.06)`), destination `(0.16, -0.26)` (was `(0.16, -0.06)`) -- the
destination box, not the source box, absorbed the extra separation since it has the reach
headroom to spare. 0.04m clearance between the two boxes' facing walls. `table.top_size_xy`
widened `[0.36, 0.30] -> [0.36, 0.60]` to cover the new footprint.

**pp_v2 -> pp_v3 fix (start-attached curriculum):** pp_v2 (post claw/box fix) reached 4/10 pick
success but 0/10 place success, with `mean_episode_length` pinned at the full 300-step timeout
across every eval episode -- the policy attaches, then holds position for the rest of the episode.
Diagnosis: this task had no curriculum at all (full-difficulty cube spawn from step 1) and PPO's
action std was already collapsing (~0.5 by 200k) before the 4-stage chain
(approach -> attach -> carry -> release) could plausibly be discovered by chance -- the same root
cause the bin-picking task hit early on, fixed there via a spawn-radius curriculum (v5).

Fix: `config/pick_place_env.yaml`'s `curriculum` block + `SuctionPickPlaceEnv.reset` --
`start_attached_prob` fraction of episodes (0.5) skip straight to the carry+release stage: the arm
snaps to a fixed `mid_carry_pose_rad` and the cube is welded on immediately via the same
`_attach_suction` mechanism real in-episode attachment uses, rather than requiring a fresh
approach+attach every episode. The remaining episodes still run the full task from scratch, so the
already-learned attach skill keeps getting reinforced rather than forgotten -- deliberately not
100% curriculum, for the same "don't let a shortcut erase an already-learned stage" reason the
bin-picking task keeps both easy and hard episodes in rotation.

Real bug caught before spending training compute on it: the first version of this curriculum
reused `ready_pose_rad` as the attach point, but that pose's own EE sits at world Z=0.740 -- only
1cm above the episode's knockout threshold (`table_top(0.78) - table_edge_margin_m(0.05) = 0.73`)
and off to the side, not actually over the table at all. Curriculum episodes were failing in 1-2
steps regardless of what the policy did. Caught by running a random-action sanity rollout and
noticing curriculum episodes terminating almost immediately (before assuming the curriculum config
change was correct and moving on). Fixed with a purpose-solved `mid_carry_pose_rad`: `ikpy` against
`humanoid.urdf` for world `(0.16, -0.12, 0.85)` (the Y-midpoint between the source and destination
boxes, well above the table) -- 0.0 residual, all 3 joints within range. Re-ran the random-action
check after the fix: found a genuine success (17 steps, +22 reward) in 1 of 4 curriculum episodes,
confirming placement is now reachable by exploration alone, not merely theoretically possible.

**pp_v3/pp_v4 -> pp_v5 -> pp_v6 fix (reward exploit, then overcorrection + eval methodology):**
the start-attached curriculum's continuous `lift_bonus_weight` turned out to be exploitable --
attach once via the curriculum, then hold still, collecting height-based reward every step
indefinitely (`mean_reward` climbed 135 -> 290 across checkpoints while `place_success_rate` stayed
0.0 and no episode ever terminated early). Fixed (Copilot's change, verified correct) by making the
lift reward a one-time milestone (`lift_bonus` + `stage_transition_bonus`) plus a progress-gated
`attached_idle_penalty` that only fires when cube-to-destination distance fails to improve --
pp_v5's reward returned to a realistic -142.72, confirming the exploit closed. But pp_v5 then
showed `mean_suction_cmd_rate: 0.006` -- the raw `carry_distance_weight_after_lift` term
(-12.0/m) alone cost more per step while attached (~-1 to -3, simply for being far from the
destination) than staying unattached (~-0.16/step), making any attach attempt a losing bet before
the policy had a working carry skill. Fixed by cutting `carry_distance_weight`/`_after_lift`
roughly 4x and raising `attach_bonus`/`lift_bonus`, so attempting isn't punished before it's had a
chance to learn. Separately found and fixed a methodology bug: `evaluate_checkpoint`/
`render_checkpoint_video` built a plain `SuctionPickPlaceEnv()`, still curriculum-enabled -- every
reported success rate since the curriculum was added was a mix of genuine solves and
curriculum-assisted starts. Added an `eval_mode` constructor flag that forces the curriculum off
for eval/video only. Also annealed `curriculum.start_attached_prob` (0.6 -> 0.15 over the run,
via `PeriodicArtifactCallback`'s periodic `env_method` calls) instead of holding it fixed.

**pp_v6 -> pp_v7 fix (stall penalty, wall tunneling, network size, video overlay):** pp_v6's
rendered rollout showed the arm driving into a box wall and staying jammed there for the rest of
the episode, and the cube being pushed hard enough to tunnel clean through a wall on one
checkpoint. Fixed: (1) `SuctionPickPlaceEnv._update_stall_counter` -- collision AND near-zero arm
joint velocity sustained for `stall_steps_threshold` steps triggers `stall_penalty` (-0.6/step,
distinct from the flat `collision_penalty`), same shape as bin-picking's `reward.stuck`; (2)
`boxes.wall_thickness` 0.004 -> 0.01 m -- MuJoCo's discrete collision detection can miss contacts
above roughly wall_thickness/timestep (2 m/s at the old thickness, physics_hz=500), a geometry fix
not a reward one; (3) `policy_kwargs.net_arch: {pi:[128,128], vf:[128,128]}` in
`config/train_pick_place_ppo.yaml` (every prior run used SB3's default 64x64, untried on this
4-stage sequential task); (4) `render_checkpoint_video` now burns a per-frame telemetry overlay
(Pillow) reading from the same `info` dict the reward uses, so what's on screen can't drift from
what's actually happening -- required expanding `info` with `is_arm_collision`/`is_stalled`/
`ee_to_cube_dist`/`carry_dist`/`cube_height`.

**pp_v7 -> pp_v8 additions (self-monitoring pipeline, checkpoint continuation, gentleness
penalty):** pp_v7 (stall penalty + wall fix + bigger network) showed a real, sustained
pick_success_rate trend (0% -> 60%, 200k -> 1.2M) with place_success still 0%. Per request, the
pipeline was made self-monitoring rather than requiring a human to watch TensorBoard by hand:
`training/pick_place/self_monitor.py` adds a continuous CSV metrics log (survives an
early-terminated run), a periodic (every 400k steps, deliberately infrequent) trend analysis with
automated stalled-learning detection (flat reward+success AND early-collapsed entropy, sustained
over a 300k-step window -- either alone is normal PPO noise, both together is treated as stuck and
stops training automatically), and trajectory-based behavior classification (does the policy enter
the box, approach the cube, reach-without-grasping, grasp-without-lifting,
lift-without-transporting, oscillate, or show a lateral bias -- answered from full per-step
EE/cube trajectories, not just aggregate reward). Also added: `episode_max_steps` 300->600 (more
budget per episode for the full 4-stage chain); a `cube_disturbance_weight` penalty for pushing the
cube around while touching-but-not-attached (user's direct observation: the policy was bulldozing
the cube rather than gripping it, and nothing previously penalized that); and `--init-checkpoint`
support in `train_ppo_pick_place.py` (`PPO.load(path, env=env)`) so a promising run's weights can
carry forward into the next iteration instead of always retraining from scratch -- used
immediately: pp_v8 continues from pp_v7's strongest checkpoint (60% pick success) rather than
discarding that trend for a fresh random init.

**Training pipeline** (`training/pick_place/train_ppo_pick_place.py`): every `eval_freq` timesteps
(200,000 by request), `PeriodicArtifactCallback` saves a checkpoint, runs `n_eval_episodes`
deterministic evaluations (reporting `success_rate`/`pick_success_rate` separately, so "never
attaches" vs. "attaches but can't place" stays distinguishable the same way bin-picking's
contact_rate/grasp_rate split has been useful), renders one evaluation episode to `.mp4`, and
regenerates a self-contained dashboard HTML (`scripts/generate_pick_place_dashboard.py`) with a
checkpoint dropdown (embedded base64 video + metrics per entry, no external file references) next
to a `manifest.json` recording every checkpoint's metrics. Runs live under
`training/pick_place/runs/<run_name>/{checkpoints,videos,logs}/`, kept separate from
bin-picking's flat `training/checkpoints/` layout. First run: `pp_v1`,
`config/train_pick_place_ppo.yaml` (2,000,000 timestep budget, stock 64x64 MLP, same PPO
hyperparameters as bin-picking's `state` profile as a starting point -- no tuning history exists
for this task yet).
