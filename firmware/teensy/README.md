# Teensy 4.1 — low-level motor controller

Firmware for the Teensy 4.1 that sits between the Jetson and the 8 MKS ODrive Minis.

Responsibilities:
- Drive 3 CAN buses (arm 1, arm 2, torso gimbal — see [../../docs/ARCHITECTURE.md](../../docs/ARCHITECTURE.md#4-low-level-control--teensy-41))
- Speak ODrive CANSimple (+ this fork's encoder/Iq extensions) to each ODrive Mini
- Read the 2 gimbal CANcoders
- Bridge joint commands/telemetry to the Jetson over USB

## Current status

**Milestone 1 (in progress):** single-bus, single-controller CAN listener (`src/main.cpp`).
Receive-only — proves the physical CAN link to one ODrive Mini works before anything is ever
transmitted to it. See the file header for assumptions/limitations/failure modes.

The Teensy↔Jetson host protocol (custom serial vs. micro-ROS) is still an open decision — see
the architecture doc's Open Questions checklist — but is not needed for this milestone.

## Build & flash

Requires [PlatformIO](https://platformio.org/) (CLI or the VS Code extension) and a Teensy 4.1
connected via USB.

```
pio run -e teensy41 -t upload
pio device monitor -b 115200
```

Wire exactly one ODrive Mini's CAN_H/CAN_L to the Teensy's CAN1 pins (with bus termination),
power that ODrive, and watch the monitor for frames. To test a controller on a different bus,
change `CAN1` to `CAN2`/`CAN3` in `src/main.cpp` (`CanBus` typedef and `kBusName`).

## Next milestone

Once this is verified against real hardware (frames observed, node ID confirmed), the next step
is extending to all 3 buses / listening for all 8 controllers — still receive-only — before any
command (Set_Axis_Requested_State, Set_Input_Pos, etc.) is ever transmitted.
