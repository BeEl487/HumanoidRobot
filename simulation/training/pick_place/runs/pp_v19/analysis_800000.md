# Self-monitoring analysis @ step 800,000
generated: 2026-08-07T16:36:31.749080+00:00

## Metrics trend (this window)
- reward now: -43.42
- reward trend slope: -0.0089 /log-tick (relative change over window: -1.2%)
- success rate now: 0.7
- success rate trend slope: -0.00122
- entropy: 2.408 (run start) -> 2.586 (now)
- value_loss std: 1.702, policy_loss std: 0.0029

## Simulation performance
- fps: 627.1
- estimated remaining time: 0.53 hours (32 min)

## Behavior analysis (trajectory-based)
- entered the source box: 100% of episodes
- approached the cube (<5cm): 90% of episodes
- reached the cube but never grasped: 20% of episodes
- grasped but never lifted: 70% of episodes
- lifted but never transported toward the goal: 0% of episodes
- oscillating end-effector motion: 30% of episodes
- stuck at a collision (stalled): 0% of episodes
- lateral bias: toward +Y (source/left side)
- mean closest EE-to-cube approach: 0.030 m

## Stall verdict
Not stalled -- training continues.