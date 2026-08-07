# Self-monitoring analysis @ step 1,600,000
generated: 2026-08-07T17:37:59.706463+00:00

## Metrics trend (this window)
- reward now: -73.59
- reward trend slope: -0.0760 /log-tick (relative change over window: -6.2%)
- success rate now: 0.45
- success rate trend slope: -0.00001
- entropy: 2.717 (run start) -> 1.641 (now)
- value_loss std: 2.977, policy_loss std: 0.0016

## Simulation performance
- fps: 1763.4
- estimated remaining time: 0.06 hours (4 min)

## Behavior analysis (trajectory-based)
- entered the source box: 100% of episodes
- approached the cube (<5cm): 60% of episodes
- reached the cube but never grasped: 10% of episodes
- grasped but never lifted: 0% of episodes
- lifted but never transported toward the goal: 0% of episodes
- oscillating end-effector motion: 40% of episodes
- stuck at a collision (stalled): 10% of episodes
- lateral bias: toward +Y (source/left side)
- mean closest EE-to-cube approach: 0.040 m

## Stall verdict
Not stalled -- training continues.