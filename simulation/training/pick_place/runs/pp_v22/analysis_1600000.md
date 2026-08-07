# Self-monitoring analysis @ step 1,600,000
generated: 2026-08-07T17:19:37.435018+00:00

## Metrics trend (this window)
- reward now: -141.95
- reward trend slope: +0.1986 /log-tick (relative change over window: +8.4%)
- success rate now: 0.25
- success rate trend slope: +0.00125
- entropy: 5.565 (run start) -> 3.524 (now)
- value_loss std: 2.745, policy_loss std: 0.0012

## Simulation performance
- fps: 1814.9
- estimated remaining time: 0.06 hours (4 min)

## Behavior analysis (trajectory-based)
- entered the source box: 100% of episodes
- approached the cube (<5cm): 50% of episodes
- reached the cube but never grasped: 30% of episodes
- grasped but never lifted: 0% of episodes
- lifted but never transported toward the goal: 0% of episodes
- oscillating end-effector motion: 10% of episodes
- stuck at a collision (stalled): 30% of episodes
- lateral bias: toward +Y (source/left side)
- mean closest EE-to-cube approach: 0.048 m

## Stall verdict
Not stalled -- training continues.