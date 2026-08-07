# Self-monitoring analysis @ step 400,000
generated: 2026-08-07T12:47:56.319539+00:00

## Metrics trend (this window)
- reward now: -69.08
- reward trend slope: +0.1331 /log-tick (relative change over window: +11.6%)
- success rate now: 0.44
- success rate trend slope: -0.00113
- entropy: 2.595 (run start) -> 3.307 (now)
- value_loss std: 3.157, policy_loss std: 0.0015

## Simulation performance
- fps: 806.9
- estimated remaining time: 0.55 hours (33 min)

## Behavior analysis (trajectory-based)
- entered the source box: 100% of episodes
- approached the cube (<5cm): 100% of episodes
- reached the cube but never grasped: 80% of episodes
- grasped but never lifted: 20% of episodes
- lifted but never transported toward the goal: 0% of episodes
- oscillating end-effector motion: 60% of episodes
- stuck at a collision (stalled): 0% of episodes
- lateral bias: toward +Y (source/left side)
- mean closest EE-to-cube approach: 0.033 m

## Stall verdict
Not stalled -- training continues.