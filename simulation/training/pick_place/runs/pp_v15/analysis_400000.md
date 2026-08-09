# Self-monitoring analysis @ step 400,000
generated: 2026-08-07T14:28:48.780936+00:00

## Metrics trend (this window)
- reward now: -83.86
- reward trend slope: -0.0766 /log-tick (relative change over window: -5.5%)
- success rate now: 0.53
- success rate trend slope: -0.00139
- entropy: 2.510 (run start) -> 2.232 (now)
- value_loss std: 1.423, policy_loss std: 0.0019

## Simulation performance
- fps: 666.8
- estimated remaining time: 0.67 hours (40 min)

## Behavior analysis (trajectory-based)
- entered the source box: 100% of episodes
- approached the cube (<5cm): 90% of episodes
- reached the cube but never grasped: 90% of episodes
- grasped but never lifted: 0% of episodes
- lifted but never transported toward the goal: 0% of episodes
- oscillating end-effector motion: 60% of episodes
- stuck at a collision (stalled): 0% of episodes
- lateral bias: toward +Y (source/left side)
- mean closest EE-to-cube approach: 0.036 m

## Stall verdict
Not stalled -- training continues.