# Teensy 4.1 — low-level motor controller

Firmware for the Teensy 4.1 that sits between the Jetson and the 8 MKS ODrive Minis.

Responsibilities:
- Drive 3 CAN buses (arm 1, arm 2, torso gimbal — see [../../docs/ARCHITECTURE.md](../../docs/ARCHITECTURE.md#4-low-level-control--teensy-41))
- Speak ODrive CANSimple (+ this fork's encoder/Iq extensions) to each ODrive Mini
- Read the 2 gimbal CANcoders
- Bridge joint commands/telemetry to the Jetson over USB

No code yet — host communication protocol (custom serial vs. micro-ROS) is still an open
decision, see the architecture doc's Open Questions checklist before starting implementation.
