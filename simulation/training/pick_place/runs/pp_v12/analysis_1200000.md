# Self-monitoring analysis @ step 1,200,000
generated: 2026-08-07T13:11:08.010208+00:00

## Metrics trend (this window)
- reward now: -150.20
- reward trend slope: -0.2254 /log-tick (relative change over window: -9.0%)
- success rate now: 0.11
- success rate trend slope: -0.00121
- entropy: 5.638 (run start) -> 4.215 (now)
- value_loss std: 1.677, policy_loss std: 0.0011

## Simulation performance
- fps: 2328.8
- estimated remaining time: 0.10 hours (6 min)

## Behavior analysis (trajectory-based)
- entered the source box: 100% of episodes
- approached the cube (<5cm): 90% of episodes
- reached the cube but never grasped: 90% of episodes
- grasped but never lifted: 0% of episodes
- lifted but never transported toward the goal: 0% of episodes
- oscillating end-effector motion: 10% of episodes
- stuck at a collision (stalled): 0% of episodes
- lateral bias: toward +Y (source/left side)
- mean closest EE-to-cube approach: 0.031 m

## Stall verdict
Not stalled -- training continues.