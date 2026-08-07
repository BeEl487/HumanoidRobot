# Self-monitoring analysis @ step 800,000
generated: 2026-08-07T16:16:51.702640+00:00

## Metrics trend (this window)
- reward now: -66.82
- reward trend slope: -0.0168 /log-tick (relative change over window: -1.5%)
- success rate now: 0.61
- success rate trend slope: -0.00094
- entropy: 2.279 (run start) -> 2.411 (now)
- value_loss std: 1.850, policy_loss std: 0.0031

## Simulation performance
- fps: 634.0
- estimated remaining time: 0.53 hours (32 min)

## Behavior analysis (trajectory-based)
- entered the source box: 100% of episodes
- approached the cube (<5cm): 90% of episodes
- reached the cube but never grasped: 30% of episodes
- grasped but never lifted: 60% of episodes
- lifted but never transported toward the goal: 0% of episodes
- oscillating end-effector motion: 10% of episodes
- stuck at a collision (stalled): 0% of episodes
- lateral bias: toward +Y (source/left side)
- mean closest EE-to-cube approach: 0.031 m

## Stall verdict
Not stalled -- training continues.