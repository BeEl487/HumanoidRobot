# Self-monitoring analysis @ step 400,000
generated: 2026-08-07T17:10:19.208749+00:00

## Metrics trend (this window)
- reward now: -165.76
- reward trend slope: +3.5526 /log-tick (relative change over window: +128.6%)
- success rate now: 0.16
- success rate trend slope: +0.00035
- entropy: 5.663 (run start) -> 4.891 (now)
- value_loss std: 7.512, policy_loss std: 0.0016

## Simulation performance
- fps: 2107.7
- estimated remaining time: 0.21 hours (13 min)

## Behavior analysis (trajectory-based)
- entered the source box: 100% of episodes
- approached the cube (<5cm): 100% of episodes
- reached the cube but never grasped: 100% of episodes
- grasped but never lifted: 0% of episodes
- lifted but never transported toward the goal: 0% of episodes
- oscillating end-effector motion: 20% of episodes
- stuck at a collision (stalled): 10% of episodes
- lateral bias: toward +Y (source/left side)
- mean closest EE-to-cube approach: 0.031 m

## Stall verdict
Not stalled -- training continues.