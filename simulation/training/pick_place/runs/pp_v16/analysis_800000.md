# Self-monitoring analysis @ step 800,000
generated: 2026-08-07T15:18:10.227862+00:00

## Metrics trend (this window)
- reward now: -59.85
- reward trend slope: -0.2823 /log-tick (relative change over window: -28.3%)
- success rate now: 0.63
- success rate trend slope: -0.00070
- entropy: 1.590 (run start) -> 2.049 (now)
- value_loss std: 1.151, policy_loss std: 0.0093

## Simulation performance
- fps: 660.1
- estimated remaining time: 0.50 hours (30 min)

## Behavior analysis (trajectory-based)
- entered the source box: 100% of episodes
- approached the cube (<5cm): 90% of episodes
- reached the cube but never grasped: 30% of episodes
- grasped but never lifted: 60% of episodes
- lifted but never transported toward the goal: 0% of episodes
- oscillating end-effector motion: 30% of episodes
- stuck at a collision (stalled): 0% of episodes
- lateral bias: toward +Y (source/left side)
- mean closest EE-to-cube approach: 0.030 m

## Stall verdict
Not stalled -- training continues.