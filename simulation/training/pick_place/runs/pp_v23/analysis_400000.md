# Self-monitoring analysis @ step 400,000
generated: 2026-08-07T17:28:36.200766+00:00

## Metrics trend (this window)
- reward now: -55.94
- reward trend slope: -0.2710 /log-tick (relative change over window: -29.1%)
- success rate now: 0.56
- success rate trend slope: -0.00012
- entropy: 2.724 (run start) -> 2.521 (now)
- value_loss std: 4.398, policy_loss std: 0.0013

## Simulation performance
- fps: 1776.5
- estimated remaining time: 0.25 hours (15 min)

## Behavior analysis (trajectory-based)
- entered the source box: 100% of episodes
- approached the cube (<5cm): 90% of episodes
- reached the cube but never grasped: 40% of episodes
- grasped but never lifted: 0% of episodes
- lifted but never transported toward the goal: 10% of episodes
- oscillating end-effector motion: 60% of episodes
- stuck at a collision (stalled): 20% of episodes
- lateral bias: toward +Y (source/left side)
- mean closest EE-to-cube approach: 0.031 m

## Stall verdict
Not stalled -- training continues.