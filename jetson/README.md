# Jetson — high-level compute

Runs on the Jetson (exact model TBD, see [../docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md#5-high-level-compute--jetson-nano)), connected to the Teensy 4.1 over USB.

Responsibilities:
- Camera capture / perception (camera setup TBD)
- Run trained policies for on-device **inference only** — training happens off-device
- Send joint targets to the Teensy, receive telemetry back

No code yet — depends on the Teensy↔Jetson protocol decision and the learning-approach decision,
both tracked in the architecture doc's Open Questions checklist.
