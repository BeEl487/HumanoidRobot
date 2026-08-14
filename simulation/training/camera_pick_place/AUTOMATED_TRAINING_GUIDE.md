# Camera pick-and-place implementation plan

This guide turns the earlier camera-based planning notes into a concrete implementation roadmap for training an AI policy in MuJoCo with a camera-based pick-and-place task.

## Goal

Build a first working vision-based pick-and-place pipeline in MuJoCo that uses a head-like camera observation, learns a policy from image input, and is structured so it can later be ported to the real robot.

## Phase 1 — environment and camera baseline

The first milestone is a minimal vision-based environment that can be trained and tested reliably.

### Deliverables
- a MuJoCo environment that exposes RGB observations from the head camera,
- a simple observation wrapper that returns the rendered image alongside the task state,
- a trainer entrypoint that can build and run a PPO policy from those image observations,
- and a smoke-test suite that proves the environment can be stepped and the policy can be built.

### Implementation notes
- Use the existing MuJoCo simulation stack and the existing vision wrapper pattern.
- Start with a single known cube/object and a simple workspace.
- Keep the camera mount and pitch aligned with the head-like camera concept already used in the simulation config.

## Phase 2 — scripted perception baseline

Before full RL training, add a scripted perception baseline that uses the rendered RGB image and a simple object mask.

### Deliverables
- a simple object detector or segmentation proxy from the camera image,
- a point-cloud-style grasp estimate from the segmented object,
- a conservative side-approach grasp policy,
- and a scriptable grasp loop that can be tested without needing full RL training yet.

### Why this matters
This establishes the camera-to-grasp pipeline in a deterministic way before the policy learning step is asked to solve perception and control at the same time.

## Phase 3 — PPO training with vision

Once the environment and scripted baseline are stable, train a policy directly from RGB observations.

### Training target
- use the camera image as the main visual observation,
- keep the action space small and interpretable at first,
- and learn a simple pick-and-place policy that moves toward the object, makes contact, and completes the placement step.

### Initial training recipe
- start with a small, stable PPO setup,
- use the existing MuJoCo environment as the training backend,
- keep the task simple and single-object first,
- and use scripted diagnostics to monitor whether the policy is actually seeing the object and moving toward it.

## Phase 4 — real-robot transfer path

The MuJoCo version should stay compatible with the eventual hardware stack.

### Transfer requirements
- keep the observation interface simple and camera-centric,
- preserve the concept of a head-like camera mount,
- and keep the action/output structure compatible with the later scripted or learned controller.

## Milestones

1. Environment + camera wrapper working
2. PPO policy buildable from RGB observations
3. Scripted perception baseline working
4. Learned policy showing meaningful progress on the pick-and-place task
5. Transfer path documented for the real robot

## Verification checklist

Each milestone should be verified with an explicit check:
- environment can reset and step,
- RGB observation is present and shaped correctly,
- policy can be built and updated for a small number of steps,
- and the scripted or learned policy produces a valid action that moves the arm toward the object.

## Notes for the implementation

The implementation should remain conservative and should not try to solve the full real-world manipulation stack at once. The first realistic target is a single-object, single-bin, camera-driven MuJoCo policy that demonstrates the end-to-end loop from vision to action.
