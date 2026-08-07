# Self-monitoring analysis @ step 1,200,000
generated: 2026-08-07T13:37:39.745104+00:00

## Metrics trend (this window)
- reward now: -79.09
- reward trend slope: +0.0233 /log-tick (relative change over window: +1.8%)
- success rate now: 0.33
- success rate trend slope: +0.00145
- entropy: 2.541 (run start) -> 2.631 (now)
- value_loss std: 2.222, policy_loss std: 0.0018

## Simulation performance
- fps: 648.1
- estimated remaining time: 0.34 hours (21 min)

## Behavior analysis (trajectory-based)
- entered the source box: 100% of episodes
- approached the cube (<5cm): 100% of episodes
- reached the cube but never grasped: 60% of episodes
- grasped but never lifted: 30% of episodes
- lifted but never transported toward the goal: 10% of episodes
- oscillating end-effector motion: 10% of episodes
- stuck at a collision (stalled): 10% of episodes
- lateral bias: toward +Y (source/left side)
- mean closest EE-to-cube approach: 0.030 m

## Stall verdict
Not stalled -- training continues.