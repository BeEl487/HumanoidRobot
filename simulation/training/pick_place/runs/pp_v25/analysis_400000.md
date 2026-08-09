# Self-monitoring analysis @ step 400,000
generated: 2026-08-07T18:03:30.584483+00:00

## Metrics trend (this window)
- reward now: -20.59
- reward trend slope: -0.1864 /log-tick (relative change over window: -54.3%)
- success rate now: 0.72
- success rate trend slope: -0.00093
- entropy: 0.753 (run start) -> 0.715 (now)
- value_loss std: 3.514, policy_loss std: 0.0034

## Simulation performance
- fps: 1862.5
- estimated remaining time: 0.24 hours (14 min)

## Behavior analysis (trajectory-based)
- entered the source box: 100% of episodes
- approached the cube (<5cm): 100% of episodes
- reached the cube but never grasped: 40% of episodes
- grasped but never lifted: 0% of episodes
- lifted but never transported toward the goal: 0% of episodes
- oscillating end-effector motion: 40% of episodes
- stuck at a collision (stalled): 0% of episodes
- lateral bias: toward +Y (source/left side)
- mean closest EE-to-cube approach: 0.029 m

## Stall verdict
Not stalled -- training continues.