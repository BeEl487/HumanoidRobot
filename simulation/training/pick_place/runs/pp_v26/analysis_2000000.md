# Self-monitoring analysis @ step 2,000,000
generated: 2026-08-07T18:32:32.479568+00:00

## Metrics trend (this window)
- reward now: -42.04
- reward trend slope: +0.0032 /log-tick (relative change over window: +0.5%)
- success rate now: 0.63
- success rate trend slope: +0.00044
- entropy: 0.458 (run start) -> 0.342 (now)
- value_loss std: 3.420, policy_loss std: 0.0035

## Simulation performance
- fps: 4904.4
- estimated remaining time: 0.00 hours (0 min)

## Behavior analysis (trajectory-based)
- entered the source box: 100% of episodes
- approached the cube (<5cm): 100% of episodes
- reached the cube but never grasped: 30% of episodes
- grasped but never lifted: 0% of episodes
- lifted but never transported toward the goal: 0% of episodes
- oscillating end-effector motion: 0% of episodes
- stuck at a collision (stalled): 0% of episodes
- lateral bias: toward +Y (source/left side)
- mean closest EE-to-cube approach: 0.025 m

## Stall verdict
Not stalled -- training continues.