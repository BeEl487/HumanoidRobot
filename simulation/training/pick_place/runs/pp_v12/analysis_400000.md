# Self-monitoring analysis @ step 400,000
generated: 2026-08-07T13:05:14.394574+00:00

## Metrics trend (this window)
- reward now: -148.99
- reward trend slope: +3.5982 /log-tick (relative change over window: +144.9%)
- success rate now: 0.09
- success rate trend slope: +0.00036
- entropy: 5.658 (run start) -> 5.246 (now)
- value_loss std: 7.027, policy_loss std: 0.0015

## Simulation performance
- fps: 2060.3
- estimated remaining time: 0.22 hours (13 min)

## Behavior analysis (trajectory-based)
- entered the source box: 100% of episodes
- approached the cube (<5cm): 90% of episodes
- reached the cube but never grasped: 90% of episodes
- grasped but never lifted: 0% of episodes
- lifted but never transported toward the goal: 0% of episodes
- oscillating end-effector motion: 10% of episodes
- stuck at a collision (stalled): 20% of episodes
- lateral bias: toward +Y (source/left side)
- mean closest EE-to-cube approach: 0.036 m

## Stall verdict
Not stalled -- training continues.