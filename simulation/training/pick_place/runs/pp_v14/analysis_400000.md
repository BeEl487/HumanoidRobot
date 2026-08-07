# Self-monitoring analysis @ step 400,000
generated: 2026-08-07T13:54:45.398172+00:00

## Metrics trend (this window)
- reward now: -62.93
- reward trend slope: +0.3034 /log-tick (relative change over window: +28.9%)
- success rate now: 0.5
- success rate trend slope: -0.00136
- entropy: 2.426 (run start) -> 2.320 (now)
- value_loss std: 1.689, policy_loss std: 0.0024

## Simulation performance
- fps: 659.9
- estimated remaining time: 0.67 hours (40 min)

## Behavior analysis (trajectory-based)
- entered the source box: 100% of episodes
- approached the cube (<5cm): 100% of episodes
- reached the cube but never grasped: 70% of episodes
- grasped but never lifted: 30% of episodes
- lifted but never transported toward the goal: 0% of episodes
- oscillating end-effector motion: 60% of episodes
- stuck at a collision (stalled): 10% of episodes
- lateral bias: toward +Y (source/left side)
- mean closest EE-to-cube approach: 0.033 m

## Stall verdict
Not stalled -- training continues.