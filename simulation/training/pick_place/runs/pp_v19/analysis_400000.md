# Self-monitoring analysis @ step 400,000
generated: 2026-08-07T16:29:14.129430+00:00

## Metrics trend (this window)
- reward now: 1.39
- reward trend slope: -0.2363 /log-tick (relative change over window: -1019.0%)
- success rate now: 0.8
- success rate trend slope: -0.00117
- entropy: 2.381 (run start) -> 2.371 (now)
- value_loss std: 1.644, policy_loss std: 0.0028

## Simulation performance
- fps: 654.0
- estimated remaining time: 0.68 hours (41 min)

## Behavior analysis (trajectory-based)
- entered the source box: 100% of episodes
- approached the cube (<5cm): 80% of episodes
- reached the cube but never grasped: 60% of episodes
- grasped but never lifted: 20% of episodes
- lifted but never transported toward the goal: 0% of episodes
- oscillating end-effector motion: 30% of episodes
- stuck at a collision (stalled): 0% of episodes
- lateral bias: toward +Y (source/left side)
- mean closest EE-to-cube approach: 0.037 m

## Stall verdict
Not stalled -- training continues.