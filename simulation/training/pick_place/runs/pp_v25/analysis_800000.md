# Self-monitoring analysis @ step 800,000
generated: 2026-08-07T18:06:30.910047+00:00

## Metrics trend (this window)
- reward now: -36.99
- reward trend slope: -0.0187 /log-tick (relative change over window: -3.0%)
- success rate now: 0.61
- success rate trend slope: -0.00081
- entropy: 0.755 (run start) -> 0.698 (now)
- value_loss std: 4.222, policy_loss std: 0.0032

## Simulation performance
- fps: 1749.8
- estimated remaining time: 0.19 hours (11 min)

## Behavior analysis (trajectory-based)
- entered the source box: 100% of episodes
- approached the cube (<5cm): 100% of episodes
- reached the cube but never grasped: 20% of episodes
- grasped but never lifted: 0% of episodes
- lifted but never transported toward the goal: 0% of episodes
- oscillating end-effector motion: 0% of episodes
- stuck at a collision (stalled): 0% of episodes
- lateral bias: toward +Y (source/left side)
- mean closest EE-to-cube approach: 0.027 m

## Stall verdict
Not stalled -- training continues.