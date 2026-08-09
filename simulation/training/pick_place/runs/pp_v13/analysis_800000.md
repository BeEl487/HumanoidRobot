# Self-monitoring analysis @ step 800,000
generated: 2026-08-07T13:30:19.774107+00:00

## Metrics trend (this window)
- reward now: -75.50
- reward trend slope: -0.5686 /log-tick (relative change over window: -45.2%)
- success rate now: 0.41
- success rate trend slope: -0.00149
- entropy: 2.539 (run start) -> 2.564 (now)
- value_loss std: 3.004, policy_loss std: 0.0021

## Simulation performance
- fps: 684.9
- estimated remaining time: 0.49 hours (29 min)

## Behavior analysis (trajectory-based)
- entered the source box: 100% of episodes
- approached the cube (<5cm): 90% of episodes
- reached the cube but never grasped: 30% of episodes
- grasped but never lifted: 60% of episodes
- lifted but never transported toward the goal: 0% of episodes
- oscillating end-effector motion: 0% of episodes
- stuck at a collision (stalled): 0% of episodes
- lateral bias: toward +Y (source/left side)
- mean closest EE-to-cube approach: 0.035 m

## Stall verdict
Not stalled -- training continues.