# Self-monitoring analysis @ step 800,004
generated: 2026-08-07T11:36:59.248810+00:00

## Metrics trend (this window)
- reward now: 192.10
- reward trend slope: +2.3287 /log-tick (relative change over window: +72.7%)
- success rate now: 0.43
- success rate trend slope: -0.00101
- entropy: 1.534 (run start) -> 0.902 (now)
- value_loss std: 109.266, policy_loss std: 0.0064

## Simulation performance
- fps: n/a

## Behavior analysis (trajectory-based)
- entered the source box: 100% of episodes
- approached the cube (<5cm): 90% of episodes
- reached the cube but never grasped: 50% of episodes
- grasped but never lifted: 40% of episodes
- lifted but never transported toward the goal: 0% of episodes
- oscillating end-effector motion: 100% of episodes
- stuck at a collision (stalled): 10% of episodes
- lateral bias: toward +Y (source/left side)
- mean closest EE-to-cube approach: 0.035 m

## Stall verdict
Not stalled -- training continues.