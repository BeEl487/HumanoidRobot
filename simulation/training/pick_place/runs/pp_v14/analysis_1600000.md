# Self-monitoring analysis @ step 1,600,000
generated: 2026-08-07T14:16:30.989708+00:00

## Metrics trend (this window)
- reward now: -114.19
- reward trend slope: -0.0693 /log-tick (relative change over window: -3.6%)
- success rate now: 0.17
- success rate trend slope: -0.00150
- entropy: 2.367 (run start) -> 2.461 (now)
- value_loss std: 2.048, policy_loss std: 0.0027

## Simulation performance
- fps: 674.5
- estimated remaining time: 0.16 hours (10 min)

## Behavior analysis (trajectory-based)
- entered the source box: 100% of episodes
- approached the cube (<5cm): 100% of episodes
- reached the cube but never grasped: 70% of episodes
- grasped but never lifted: 20% of episodes
- lifted but never transported toward the goal: 10% of episodes
- oscillating end-effector motion: 10% of episodes
- stuck at a collision (stalled): 0% of episodes
- lateral bias: toward +Y (source/left side)
- mean closest EE-to-cube approach: 0.031 m

## Stall verdict
Not stalled -- training continues.