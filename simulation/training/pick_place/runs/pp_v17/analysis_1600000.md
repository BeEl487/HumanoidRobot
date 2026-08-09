# Self-monitoring analysis @ step 1,600,000
generated: 2026-08-07T16:00:12.807786+00:00

## Metrics trend (this window)
- reward now: -115.32
- reward trend slope: -1.0927 /log-tick (relative change over window: -56.9%)
- success rate now: 0.49
- success rate trend slope: -0.00320
- entropy: 2.070 (run start) -> 2.369 (now)
- value_loss std: 1.594, policy_loss std: 0.0056

## Simulation performance
- fps: 645.4
- estimated remaining time: 0.17 hours (10 min)

## Behavior analysis (trajectory-based)
- entered the source box: 100% of episodes
- approached the cube (<5cm): 90% of episodes
- reached the cube but never grasped: 50% of episodes
- grasped but never lifted: 20% of episodes
- lifted but never transported toward the goal: 20% of episodes
- oscillating end-effector motion: 10% of episodes
- stuck at a collision (stalled): 0% of episodes
- lateral bias: toward +Y (source/left side)
- mean closest EE-to-cube approach: 0.034 m

## Stall verdict
Not stalled -- training continues.