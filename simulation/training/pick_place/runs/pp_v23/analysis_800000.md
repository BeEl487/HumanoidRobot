# Self-monitoring analysis @ step 800,000
generated: 2026-08-07T17:31:44.513496+00:00

## Metrics trend (this window)
- reward now: -43.42
- reward trend slope: -0.0380 /log-tick (relative change over window: -5.3%)
- success rate now: 0.52
- success rate trend slope: -0.00121
- entropy: 2.736 (run start) -> 2.197 (now)
- value_loss std: 2.624, policy_loss std: 0.0016

## Simulation performance
- fps: 1779.0
- estimated remaining time: 0.19 hours (11 min)

## Behavior analysis (trajectory-based)
- entered the source box: 100% of episodes
- approached the cube (<5cm): 70% of episodes
- reached the cube but never grasped: 30% of episodes
- grasped but never lifted: 0% of episodes
- lifted but never transported toward the goal: 0% of episodes
- oscillating end-effector motion: 60% of episodes
- stuck at a collision (stalled): 0% of episodes
- lateral bias: toward +Y (source/left side)
- mean closest EE-to-cube approach: 0.042 m

## Stall verdict
Not stalled -- training continues.