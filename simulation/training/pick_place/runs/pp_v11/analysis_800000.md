# Self-monitoring analysis @ step 800,000
generated: 2026-08-07T12:54:22.122261+00:00

## Metrics trend (this window)
- reward now: -66.63
- reward trend slope: -0.2444 /log-tick (relative change over window: -22.0%)
- success rate now: 0.39
- success rate trend slope: -0.00173
- entropy: 2.675 (run start) -> 4.239 (now)
- value_loss std: 2.440, policy_loss std: 0.0016

## Simulation performance
- fps: 820.7
- estimated remaining time: 0.41 hours (24 min)

## Behavior analysis (trajectory-based)
- entered the source box: 100% of episodes
- approached the cube (<5cm): 100% of episodes
- reached the cube but never grasped: 30% of episodes
- grasped but never lifted: 60% of episodes
- lifted but never transported toward the goal: 10% of episodes
- oscillating end-effector motion: 10% of episodes
- stuck at a collision (stalled): 0% of episodes
- lateral bias: toward +Y (source/left side)
- mean closest EE-to-cube approach: 0.030 m

## Stall verdict
Not stalled -- training continues.