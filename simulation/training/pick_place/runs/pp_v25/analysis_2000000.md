# Self-monitoring analysis @ step 2,000,000
generated: 2026-08-07T18:15:38.230339+00:00

## Metrics trend (this window)
- reward now: -37.69
- reward trend slope: -0.0439 /log-tick (relative change over window: -7.0%)
- success rate now: 0.64
- success rate trend slope: +0.00029
- entropy: 0.751 (run start) -> 0.404 (now)
- value_loss std: 5.089, policy_loss std: 0.0027

## Simulation performance
- fps: 4239.3
- estimated remaining time: 0.00 hours (0 min)

## Behavior analysis (trajectory-based)
- entered the source box: 100% of episodes
- approached the cube (<5cm): 100% of episodes
- reached the cube but never grasped: 30% of episodes
- grasped but never lifted: 0% of episodes
- lifted but never transported toward the goal: 0% of episodes
- oscillating end-effector motion: 30% of episodes
- stuck at a collision (stalled): 0% of episodes
- lateral bias: toward +Y (source/left side)
- mean closest EE-to-cube approach: 0.027 m

## Stall verdict
Not stalled -- training continues.