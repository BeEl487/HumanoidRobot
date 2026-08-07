# Self-monitoring analysis @ step 1,200,000
generated: 2026-08-07T14:09:16.033460+00:00

## Metrics trend (this window)
- reward now: -82.95
- reward trend slope: +0.4059 /log-tick (relative change over window: +29.4%)
- success rate now: 0.33
- success rate trend slope: +0.00010
- entropy: 2.385 (run start) -> 2.363 (now)
- value_loss std: 1.286, policy_loss std: 0.0027

## Simulation performance
- fps: 660.6
- estimated remaining time: 0.34 hours (20 min)

## Behavior analysis (trajectory-based)
- entered the source box: 100% of episodes
- approached the cube (<5cm): 100% of episodes
- reached the cube but never grasped: 60% of episodes
- grasped but never lifted: 40% of episodes
- lifted but never transported toward the goal: 0% of episodes
- oscillating end-effector motion: 50% of episodes
- stuck at a collision (stalled): 0% of episodes
- lateral bias: toward +Y (source/left side)
- mean closest EE-to-cube approach: 0.030 m

## Stall verdict
Not stalled -- training continues.