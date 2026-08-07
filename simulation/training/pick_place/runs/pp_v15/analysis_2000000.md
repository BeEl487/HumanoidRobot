# Self-monitoring analysis @ step 2,000,000
generated: 2026-08-07T14:57:59.952136+00:00

## Metrics trend (this window)
- reward now: -205.95
- reward trend slope: -0.1192 /log-tick (relative change over window: -3.5%)
- success rate now: 0.15
- success rate trend slope: +0.00045
- entropy: 2.399 (run start) -> 1.547 (now)
- value_loss std: 1.233, policy_loss std: 0.0085

## Simulation performance
- fps: 5111.1
- estimated remaining time: 0.00 hours (0 min)

## Behavior analysis (trajectory-based)
- entered the source box: 100% of episodes
- approached the cube (<5cm): 80% of episodes
- reached the cube but never grasped: 40% of episodes
- grasped but never lifted: 40% of episodes
- lifted but never transported toward the goal: 0% of episodes
- oscillating end-effector motion: 60% of episodes
- stuck at a collision (stalled): 0% of episodes
- lateral bias: toward +Y (source/left side)
- mean closest EE-to-cube approach: 0.038 m

## Stall verdict
Not stalled -- training continues.