# Self-monitoring analysis @ step 800,000
generated: 2026-08-07T13:08:12.791330+00:00

## Metrics trend (this window)
- reward now: -123.78
- reward trend slope: +0.1908 /log-tick (relative change over window: +9.2%)
- success rate now: 0.19
- success rate trend slope: +0.00147
- entropy: 5.646 (run start) -> 4.582 (now)
- value_loss std: 2.358, policy_loss std: 0.0011

## Simulation performance
- fps: 1980.1
- estimated remaining time: 0.17 hours (10 min)

## Behavior analysis (trajectory-based)
- entered the source box: 100% of episodes
- approached the cube (<5cm): 100% of episodes
- reached the cube but never grasped: 100% of episodes
- grasped but never lifted: 0% of episodes
- lifted but never transported toward the goal: 0% of episodes
- oscillating end-effector motion: 30% of episodes
- stuck at a collision (stalled): 0% of episodes
- lateral bias: toward +Y (source/left side)
- mean closest EE-to-cube approach: 0.027 m

## Stall verdict
Not stalled -- training continues.