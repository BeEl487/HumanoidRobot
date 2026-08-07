# Self-monitoring analysis @ step 1,600,000
generated: 2026-08-07T18:12:34.244731+00:00

## Metrics trend (this window)
- reward now: -35.42
- reward trend slope: -0.2515 /log-tick (relative change over window: -42.6%)
- success rate now: 0.66
- success rate trend slope: -0.00074
- entropy: 0.750 (run start) -> 0.447 (now)
- value_loss std: 3.390, policy_loss std: 0.0035

## Simulation performance
- fps: 1832.6
- estimated remaining time: 0.06 hours (4 min)

## Behavior analysis (trajectory-based)
- entered the source box: 100% of episodes
- approached the cube (<5cm): 60% of episodes
- reached the cube but never grasped: 10% of episodes
- grasped but never lifted: 0% of episodes
- lifted but never transported toward the goal: 0% of episodes
- oscillating end-effector motion: 40% of episodes
- stuck at a collision (stalled): 0% of episodes
- lateral bias: toward +Y (source/left side)
- mean closest EE-to-cube approach: 0.042 m

## Stall verdict
Not stalled -- training continues.