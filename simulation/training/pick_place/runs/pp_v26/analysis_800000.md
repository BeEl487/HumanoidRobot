# Self-monitoring analysis @ step 800,000
generated: 2026-08-07T18:23:33.558266+00:00

## Metrics trend (this window)
- reward now: -22.72
- reward trend slope: -0.3283 /log-tick (relative change over window: -86.7%)
- success rate now: 0.74
- success rate trend slope: -0.00182
- entropy: 0.424 (run start) -> 0.458 (now)
- value_loss std: 2.998, policy_loss std: 0.0031

## Simulation performance
- fps: 1751.3
- estimated remaining time: 0.19 hours (11 min)

## Behavior analysis (trajectory-based)
- entered the source box: 100% of episodes
- approached the cube (<5cm): 90% of episodes
- reached the cube but never grasped: 10% of episodes
- grasped but never lifted: 0% of episodes
- lifted but never transported toward the goal: 0% of episodes
- oscillating end-effector motion: 0% of episodes
- stuck at a collision (stalled): 0% of episodes
- lateral bias: toward +Y (source/left side)
- mean closest EE-to-cube approach: 0.028 m

## Stall verdict
Not stalled -- training continues.