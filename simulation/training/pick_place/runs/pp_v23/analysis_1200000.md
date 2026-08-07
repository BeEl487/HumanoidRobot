# Self-monitoring analysis @ step 1,200,000
generated: 2026-08-07T17:34:52.861376+00:00

## Metrics trend (this window)
- reward now: -68.49
- reward trend slope: -0.3944 /log-tick (relative change over window: -34.6%)
- success rate now: 0.39
- success rate trend slope: -0.00146
- entropy: 2.721 (run start) -> 2.091 (now)
- value_loss std: 2.480, policy_loss std: 0.0019

## Simulation performance
- fps: 1759.6
- estimated remaining time: 0.13 hours (8 min)

## Behavior analysis (trajectory-based)
- entered the source box: 100% of episodes
- approached the cube (<5cm): 10% of episodes
- reached the cube but never grasped: 0% of episodes
- grasped but never lifted: 0% of episodes
- lifted but never transported toward the goal: 0% of episodes
- oscillating end-effector motion: 90% of episodes
- stuck at a collision (stalled): 0% of episodes
- lateral bias: toward +Y (source/left side)
- mean closest EE-to-cube approach: 0.058 m

## Stall verdict
Not stalled -- training continues.