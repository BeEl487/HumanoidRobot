# Self-monitoring analysis @ step 400,000
generated: 2026-08-07T12:31:45.011044+00:00

## Metrics trend (this window)
- reward now: -120.00
- reward trend slope: -0.3529 /log-tick (relative change over window: -17.6%)
- success rate now: 0.48
- success rate trend slope: -0.00047
- entropy: -0.214 (run start) -> 1.239 (now) -- COLLAPSED EARLY
- value_loss std: 8.144, policy_loss std: 0.0026

## Simulation performance
- fps: 826.3
- estimated remaining time: 0.54 hours (32 min)

## Behavior analysis (trajectory-based)
- entered the source box: 100% of episodes
- approached the cube (<5cm): 100% of episodes
- reached the cube but never grasped: 30% of episodes
- grasped but never lifted: 60% of episodes
- lifted but never transported toward the goal: 10% of episodes
- oscillating end-effector motion: 10% of episodes
- stuck at a collision (stalled): 10% of episodes
- lateral bias: toward +Y (source/left side)
- mean closest EE-to-cube approach: 0.026 m

## Stall verdict
Not stalled -- training continues.