# Self-monitoring analysis @ step 400,000
generated: 2026-08-07T18:20:32.194412+00:00

## Metrics trend (this window)
- reward now: -9.62
- reward trend slope: -0.1196 /log-tick (relative change over window: -74.5%)
- success rate now: 0.8
- success rate trend slope: -0.00040
- entropy: 0.419 (run start) -> 0.344 (now)
- value_loss std: 2.962, policy_loss std: 0.0030

## Simulation performance
- fps: 1821.5
- estimated remaining time: 0.24 hours (15 min)

## Behavior analysis (trajectory-based)
- entered the source box: 100% of episodes
- approached the cube (<5cm): 100% of episodes
- reached the cube but never grasped: 50% of episodes
- grasped but never lifted: 0% of episodes
- lifted but never transported toward the goal: 0% of episodes
- oscillating end-effector motion: 50% of episodes
- stuck at a collision (stalled): 0% of episodes
- lateral bias: toward +Y (source/left side)
- mean closest EE-to-cube approach: 0.028 m

## Stall verdict
Not stalled -- training continues.