# Self-monitoring analysis @ step 1,200,000
generated: 2026-08-07T14:43:26.548320+00:00

## Metrics trend (this window)
- reward now: -146.08
- reward trend slope: +0.4439 /log-tick (relative change over window: +18.2%)
- success rate now: 0.29
- success rate trend slope: +0.00028
- entropy: 2.461 (run start) -> 1.816 (now)
- value_loss std: 1.208, policy_loss std: 0.0023

## Simulation performance
- fps: 654.7
- estimated remaining time: 0.34 hours (20 min)

## Behavior analysis (trajectory-based)
- entered the source box: 100% of episodes
- approached the cube (<5cm): 80% of episodes
- reached the cube but never grasped: 20% of episodes
- grasped but never lifted: 60% of episodes
- lifted but never transported toward the goal: 0% of episodes
- oscillating end-effector motion: 20% of episodes
- stuck at a collision (stalled): 0% of episodes
- lateral bias: toward +Y (source/left side)
- mean closest EE-to-cube approach: 0.035 m

## Stall verdict
Not stalled -- training continues.