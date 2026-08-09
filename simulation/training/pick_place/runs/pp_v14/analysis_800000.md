# Self-monitoring analysis @ step 800,000
generated: 2026-08-07T14:02:00.884790+00:00

## Metrics trend (this window)
- reward now: -77.35
- reward trend slope: -0.2741 /log-tick (relative change over window: -21.3%)
- success rate now: 0.39
- success rate trend slope: -0.00175
- entropy: 2.386 (run start) -> 2.439 (now)
- value_loss std: 1.717, policy_loss std: 0.0026

## Simulation performance
- fps: 679.1
- estimated remaining time: 0.49 hours (29 min)

## Behavior analysis (trajectory-based)
- entered the source box: 100% of episodes
- approached the cube (<5cm): 100% of episodes
- reached the cube but never grasped: 80% of episodes
- grasped but never lifted: 10% of episodes
- lifted but never transported toward the goal: 10% of episodes
- oscillating end-effector motion: 60% of episodes
- stuck at a collision (stalled): 0% of episodes
- lateral bias: toward +Y (source/left side)
- mean closest EE-to-cube approach: 0.033 m

## Stall verdict
Not stalled -- training continues.