# Self-monitoring analysis @ step 400,000
generated: 2026-08-07T15:10:49.759198+00:00

## Metrics trend (this window)
- reward now: -16.24
- reward trend slope: +0.0857 /log-tick (relative change over window: +31.7%)
- success rate now: 0.81
- success rate trend slope: +0.00365
- entropy: 1.569 (run start) -> 1.720 (now)
- value_loss std: 2.722, policy_loss std: 0.0079

## Simulation performance
- fps: 667.3
- estimated remaining time: 0.67 hours (40 min)

## Behavior analysis (trajectory-based)
- entered the source box: 100% of episodes
- approached the cube (<5cm): 80% of episodes
- reached the cube but never grasped: 80% of episodes
- grasped but never lifted: 0% of episodes
- lifted but never transported toward the goal: 0% of episodes
- oscillating end-effector motion: 20% of episodes
- stuck at a collision (stalled): 0% of episodes
- lateral bias: toward +Y (source/left side)
- mean closest EE-to-cube approach: 0.039 m

## Stall verdict
Not stalled -- training continues.