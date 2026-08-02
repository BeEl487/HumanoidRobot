# HumanoidRobot

Top half of a humanoid robot (torso on a 2-motor gimbal + two 3-actuator arms), built on MKS
ODrive Mini motor controllers and a Teensy 4.1 / Jetson compute stack. Goal: train task-completion
models off-device and deploy them for autonomous on-device inference.

Full hardware/software design, wiring assignments, and open decisions:
**[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** — keep it updated as the build changes.

## Layout

- [docs/](docs/) — architecture and design docs
- [firmware/teensy/](firmware/teensy/) — Teensy 4.1 low-level motor control firmware
- [jetson/](jetson/) — Jetson high-level compute (perception, policy inference)
- [MKS-Odrive-Mini-Firmware/](MKS-Odrive-Mini-Firmware/) — built ODrive Mini firmware binary
