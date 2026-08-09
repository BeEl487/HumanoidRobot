# Self-monitoring analysis @ step 1,200,000
generated: 2026-08-07T17:52:29.013340+00:00

## Metrics trend (this window)
- reward now: -30.10
- reward trend slope: -0.0417 /log-tick (relative change over window: -8.3%)
- success rate now: 0.68
- success rate trend slope: -0.00001
- entropy: 1.051 (run start) -> 0.692 (now)
- value_loss std: 3.519, policy_loss std: 0.0030

## Simulation performance
- fps: 1756.8
- estimated remaining time: 0.13 hours (8 min)

## Behavior analysis (trajectory-based)
- entered the source box: 100% of episodes
- approached the cube (<5cm): 30% of episodes
- reached the cube but never grasped: 10% of episodes
- grasped but never lifted: 0% of episodes
- lifted but never transported toward the goal: 0% of episodes
- oscillating end-effector motion: 80% of episodes
- stuck at a collision (stalled): 0% of episodes
- lateral bias: toward +Y (source/left side)
- mean closest EE-to-cube approach: 0.060 m

## Stall verdict
Not stalled -- training continues.