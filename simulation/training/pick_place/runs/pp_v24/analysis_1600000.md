# Self-monitoring analysis @ step 1,600,000
generated: 2026-08-07T17:55:36.819112+00:00

## Metrics trend (this window)
- reward now: -55.30
- reward trend slope: -0.0940 /log-tick (relative change over window: -10.2%)
- success rate now: 0.56
- success rate trend slope: -0.00119
- entropy: 1.019 (run start) -> 0.645 (now)
- value_loss std: 3.635, policy_loss std: 0.0024

## Simulation performance
- fps: 1790.2
- estimated remaining time: 0.06 hours (4 min)

## Behavior analysis (trajectory-based)
- entered the source box: 100% of episodes
- approached the cube (<5cm): 40% of episodes
- reached the cube but never grasped: 20% of episodes
- grasped but never lifted: 0% of episodes
- lifted but never transported toward the goal: 0% of episodes
- oscillating end-effector motion: 60% of episodes
- stuck at a collision (stalled): 0% of episodes
- lateral bias: toward +Y (source/left side)
- mean closest EE-to-cube approach: 0.051 m

## Stall verdict
Not stalled -- training continues.