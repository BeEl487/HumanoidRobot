# Self-monitoring analysis @ step 400,000
generated: 2026-08-07T13:23:00.997255+00:00

## Metrics trend (this window)
- reward now: -83.06
- reward trend slope: +0.0684 /log-tick (relative change over window: +4.9%)
- success rate now: 0.51
- success rate trend slope: -0.00142
- entropy: 2.519 (run start) -> 2.669 (now)
- value_loss std: 2.931, policy_loss std: 0.0020

## Simulation performance
- fps: 657.8
- estimated remaining time: 0.68 hours (41 min)

## Behavior analysis (trajectory-based)
- entered the source box: 100% of episodes
- approached the cube (<5cm): 90% of episodes
- reached the cube but never grasped: 70% of episodes
- grasped but never lifted: 20% of episodes
- lifted but never transported toward the goal: 0% of episodes
- oscillating end-effector motion: 60% of episodes
- stuck at a collision (stalled): 0% of episodes
- lateral bias: toward +Y (source/left side)
- mean closest EE-to-cube approach: 0.034 m

## Stall verdict
Not stalled -- training continues.