# Self-monitoring analysis @ step 1,200,000
generated: 2026-08-07T18:09:32.585472+00:00

## Metrics trend (this window)
- reward now: -26.00
- reward trend slope: -0.0365 /log-tick (relative change over window: -8.4%)
- success rate now: 0.66
- success rate trend slope: -0.00035
- entropy: 0.753 (run start) -> 0.444 (now)
- value_loss std: 3.744, policy_loss std: 0.0027

## Simulation performance
- fps: 1858.1
- estimated remaining time: 0.12 hours (7 min)

## Behavior analysis (trajectory-based)
- entered the source box: 100% of episodes
- approached the cube (<5cm): 100% of episodes
- reached the cube but never grasped: 30% of episodes
- grasped but never lifted: 0% of episodes
- lifted but never transported toward the goal: 0% of episodes
- oscillating end-effector motion: 20% of episodes
- stuck at a collision (stalled): 0% of episodes
- lateral bias: toward +Y (source/left side)
- mean closest EE-to-cube approach: 0.024 m

## Stall verdict
Not stalled -- training continues.