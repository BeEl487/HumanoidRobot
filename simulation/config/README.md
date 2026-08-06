# Config conventions

All tunable numeric parameters for the simulation live in this folder as YAML — link/torso
dimensions, joint limits, camera specs, scene/randomization ranges, environment parameters, and
training hyperparameters. Nothing here should be hardcoded in Python, MJCF, or URDF instead.

- **Units:** SI throughout — meters, kilograms, radians, seconds. State units explicitly in each
  file's comments where a value could be ambiguous (e.g. degrees vs. radians for joint ranges).
- **Every new or changed numeric placeholder** (anything not a measured fact about the real robot)
  gets a matching row added to [`../docs/ASSUMPTIONS.md`](../docs/ASSUMPTIONS.md) in the same
  change — this folder holds the *values*, that file holds the *rationale and hardware-confirm
  status* for each one.
- Config files are added incrementally, one per milestone, matching
  [`../README.md`](../README.md)'s build status list — a file listed as "not yet built" there
  doesn't exist yet, by design (iterative build, not built-ahead-of-need).
