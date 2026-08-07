# Self-monitoring analysis @ step 2,000,000
generated: 2026-08-07T17:58:37.991755+00:00

## Metrics trend (this window)
- reward now: -53.15
- reward trend slope: -0.0646 /log-tick (relative change over window: -7.3%)
- success rate now: 0.53
- success rate trend slope: -0.00078
- entropy: 1.002 (run start) -> 0.791 (now)
- value_loss std: 3.370, policy_loss std: 0.0026

## Simulation performance
- fps: 4551.6
- estimated remaining time: 0.00 hours (0 min)

## Behavior analysis (trajectory-based)
- entered the source box: 100% of episodes
- approached the cube (<5cm): 90% of episodes
- reached the cube but never grasped: 40% of episodes
- grasped but never lifted: 0% of episodes
- lifted but never transported toward the goal: 0% of episodes
- oscillating end-effector motion: 0% of episodes
- stuck at a collision (stalled): 0% of episodes
- lateral bias: toward +Y (source/left side)
- mean closest EE-to-cube approach: 0.033 m

## Stall verdict
Not stalled -- training continues.