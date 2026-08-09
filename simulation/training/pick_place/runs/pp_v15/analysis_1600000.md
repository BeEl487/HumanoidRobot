# Self-monitoring analysis @ step 1,600,000
generated: 2026-08-07T14:50:43.400134+00:00

## Metrics trend (this window)
- reward now: -201.11
- reward trend slope: -0.3283 /log-tick (relative change over window: -9.8%)
- success rate now: 0.12
- success rate trend slope: -0.00184
- entropy: 2.431 (run start) -> 1.822 (now)
- value_loss std: 0.864, policy_loss std: 0.0033

## Simulation performance
- fps: 627.1
- estimated remaining time: 0.18 hours (11 min)

## Behavior analysis (trajectory-based)
- entered the source box: 100% of episodes
- approached the cube (<5cm): 90% of episodes
- reached the cube but never grasped: 70% of episodes
- grasped but never lifted: 10% of episodes
- lifted but never transported toward the goal: 10% of episodes
- oscillating end-effector motion: 30% of episodes
- stuck at a collision (stalled): 0% of episodes
- lateral bias: toward +Y (source/left side)
- mean closest EE-to-cube approach: 0.037 m

## Stall verdict
Not stalled -- training continues.