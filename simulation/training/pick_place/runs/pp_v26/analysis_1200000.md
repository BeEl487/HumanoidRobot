# Self-monitoring analysis @ step 1,200,000
generated: 2026-08-07T18:26:32.380331+00:00

## Metrics trend (this window)
- reward now: -21.89
- reward trend slope: -0.2221 /log-tick (relative change over window: -60.9%)
- success rate now: 0.72
- success rate trend slope: -0.00108
- entropy: 0.447 (run start) -> 0.443 (now)
- value_loss std: 3.840, policy_loss std: 0.0035

## Simulation performance
- fps: 1750.9
- estimated remaining time: 0.13 hours (8 min)

## Behavior analysis (trajectory-based)
- entered the source box: 100% of episodes
- approached the cube (<5cm): 100% of episodes
- reached the cube but never grasped: 10% of episodes
- grasped but never lifted: 0% of episodes
- lifted but never transported toward the goal: 0% of episodes
- oscillating end-effector motion: 10% of episodes
- stuck at a collision (stalled): 0% of episodes
- lateral bias: toward +Y (source/left side)
- mean closest EE-to-cube approach: 0.022 m

## Stall verdict
Not stalled -- training continues.