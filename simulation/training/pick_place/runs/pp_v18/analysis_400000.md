# Self-monitoring analysis @ step 400,000
generated: 2026-08-07T16:09:31.856153+00:00

## Metrics trend (this window)
- reward now: -16.81
- reward trend slope: -0.2573 /log-tick (relative change over window: -91.9%)
- success rate now: 0.82
- success rate trend slope: -0.00093
- entropy: 2.337 (run start) -> 2.411 (now)
- value_loss std: 4.088, policy_loss std: 0.0026

## Simulation performance
- fps: 665.6
- estimated remaining time: 0.67 hours (40 min)

## Behavior analysis (trajectory-based)
- entered the source box: 100% of episodes
- approached the cube (<5cm): 80% of episodes
- reached the cube but never grasped: 60% of episodes
- grasped but never lifted: 20% of episodes
- lifted but never transported toward the goal: 0% of episodes
- oscillating end-effector motion: 20% of episodes
- stuck at a collision (stalled): 0% of episodes
- lateral bias: toward +Y (source/left side)
- mean closest EE-to-cube approach: 0.039 m

## Stall verdict
Not stalled -- training continues.