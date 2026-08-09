# Self-monitoring analysis @ step 1,200,000
generated: 2026-08-07T15:25:29.449178+00:00

## Metrics trend (this window)
- reward now: -62.30
- reward trend slope: -0.0678 /log-tick (relative change over window: -6.5%)
- success rate now: 0.6
- success rate trend slope: -0.00057
- entropy: 1.595 (run start) -> 2.107 (now)
- value_loss std: 1.479, policy_loss std: 0.0025

## Simulation performance
- fps: 662.2
- estimated remaining time: 0.34 hours (20 min)

## Behavior analysis (trajectory-based)
- entered the source box: 100% of episodes
- approached the cube (<5cm): 80% of episodes
- reached the cube but never grasped: 20% of episodes
- grasped but never lifted: 60% of episodes
- lifted but never transported toward the goal: 0% of episodes
- oscillating end-effector motion: 40% of episodes
- stuck at a collision (stalled): 0% of episodes
- lateral bias: toward +Y (source/left side)
- mean closest EE-to-cube approach: 0.033 m

## Stall verdict
Not stalled -- training continues.