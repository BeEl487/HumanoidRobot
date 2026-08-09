# Self-monitoring analysis @ step 400,000
generated: 2026-08-07T12:19:34.787173+00:00

## Metrics trend (this window)
- reward now: 201.58
- reward trend slope: +2.7023 /log-tick (relative change over window: +80.4%)
- success rate now: 0.4
- success rate trend slope: +0.00028
- entropy: -0.280 (run start) -> 0.971 (now) -- COLLAPSED EARLY
- value_loss std: 121.950, policy_loss std: 0.0030

## Simulation performance
- fps: 658.2
- estimated remaining time: 0.68 hours (41 min)

## Behavior analysis (trajectory-based)
- entered the source box: 100% of episodes
- approached the cube (<5cm): 100% of episodes
- reached the cube but never grasped: 30% of episodes
- grasped but never lifted: 60% of episodes
- lifted but never transported toward the goal: 10% of episodes
- oscillating end-effector motion: 30% of episodes
- stuck at a collision (stalled): 0% of episodes
- lateral bias: toward +Y (source/left side)
- mean closest EE-to-cube approach: 0.024 m

## Stall verdict
Not stalled -- training continues.