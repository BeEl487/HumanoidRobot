# Self-monitoring analysis @ step 2,000,000
generated: 2026-08-07T17:22:33.010559+00:00

## Metrics trend (this window)
- reward now: -105.90
- reward trend slope: +0.3662 /log-tick (relative change over window: +20.7%)
- success rate now: 0.18
- success rate trend slope: +0.00082
- entropy: 5.512 (run start) -> 2.820 (now)
- value_loss std: 2.757, policy_loss std: 0.0013

## Simulation performance
- fps: 4896.8
- estimated remaining time: 0.00 hours (0 min)

## Behavior analysis (trajectory-based)
- entered the source box: 100% of episodes
- approached the cube (<5cm): 90% of episodes
- reached the cube but never grasped: 50% of episodes
- grasped but never lifted: 0% of episodes
- lifted but never transported toward the goal: 0% of episodes
- oscillating end-effector motion: 20% of episodes
- stuck at a collision (stalled): 10% of episodes
- lateral bias: toward +Y (source/left side)
- mean closest EE-to-cube approach: 0.033 m

## Stall verdict
Not stalled -- training continues.