# Self-monitoring analysis @ step 400,000
generated: 2026-08-07T17:46:11.601657+00:00

## Metrics trend (this window)
- reward now: -27.33
- reward trend slope: -0.0102 /log-tick (relative change over window: -2.2%)
- success rate now: 0.7
- success rate trend slope: -0.00047
- entropy: 1.135 (run start) -> 0.940 (now)
- value_loss std: 3.782, policy_loss std: 0.0024

## Simulation performance
- fps: 1848.1
- estimated remaining time: 0.24 hours (14 min)

## Behavior analysis (trajectory-based)
- entered the source box: 100% of episodes
- approached the cube (<5cm): 80% of episodes
- reached the cube but never grasped: 40% of episodes
- grasped but never lifted: 0% of episodes
- lifted but never transported toward the goal: 0% of episodes
- oscillating end-effector motion: 50% of episodes
- stuck at a collision (stalled): 0% of episodes
- lateral bias: toward +Y (source/left side)
- mean closest EE-to-cube approach: 0.037 m

## Stall verdict
Not stalled -- training continues.