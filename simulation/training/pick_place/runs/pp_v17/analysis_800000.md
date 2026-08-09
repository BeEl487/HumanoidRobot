# Self-monitoring analysis @ step 800,000
generated: 2026-08-07T15:45:41.782498+00:00

## Metrics trend (this window)
- reward now: -14.05
- reward trend slope: -0.3168 /log-tick (relative change over window: -135.3%)
- success rate now: 0.78
- success rate trend slope: -0.00140
- entropy: 2.071 (run start) -> 2.697 (now)
- value_loss std: 1.065, policy_loss std: 0.0041

## Simulation performance
- fps: 632.3
- estimated remaining time: 0.53 hours (32 min)

## Behavior analysis (trajectory-based)
- entered the source box: 100% of episodes
- approached the cube (<5cm): 90% of episodes
- reached the cube but never grasped: 10% of episodes
- grasped but never lifted: 80% of episodes
- lifted but never transported toward the goal: 0% of episodes
- oscillating end-effector motion: 10% of episodes
- stuck at a collision (stalled): 0% of episodes
- lateral bias: toward +Y (source/left side)
- mean closest EE-to-cube approach: 0.030 m

## Stall verdict
Not stalled -- training continues.