# Self-monitoring analysis @ step 800,000
generated: 2026-08-07T16:45:13.295878+00:00

## Metrics trend (this window)
- reward now: -106.93
- reward trend slope: -0.1533 /log-tick (relative change over window: -8.6%)
- success rate now: 0.38
- success rate trend slope: +0.00007
- entropy: 5.632 (run start) -> 4.270 (now)
- value_loss std: 5.170, policy_loss std: 0.0009

## Simulation performance
- fps: 1945.3
- estimated remaining time: 0.17 hours (10 min)

## Behavior analysis (trajectory-based)
- entered the source box: 100% of episodes
- approached the cube (<5cm): 10% of episodes
- reached the cube but never grasped: 10% of episodes
- grasped but never lifted: 0% of episodes
- lifted but never transported toward the goal: 0% of episodes
- oscillating end-effector motion: 10% of episodes
- stuck at a collision (stalled): 0% of episodes
- lateral bias: toward +Y (source/left side)
- mean closest EE-to-cube approach: 0.077 m

## Stall verdict
Not stalled -- training continues.