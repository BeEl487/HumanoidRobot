# Self-monitoring analysis @ step 400,000
generated: 2026-08-07T16:59:01.374752+00:00

## Metrics trend (this window)
- reward now: -27.28
- reward trend slope: -0.3138 /log-tick (relative change over window: -69.0%)
- success rate now: 0.8
- success rate trend slope: -0.00097
- entropy: 2.657 (run start) -> 2.755 (now)
- value_loss std: 1.422, policy_loss std: 0.0026

## Simulation performance
- fps: 670.1
- estimated remaining time: 0.66 hours (40 min)

## Behavior analysis (trajectory-based)
- entered the source box: 100% of episodes
- approached the cube (<5cm): 80% of episodes
- reached the cube but never grasped: 60% of episodes
- grasped but never lifted: 20% of episodes
- lifted but never transported toward the goal: 0% of episodes
- oscillating end-effector motion: 30% of episodes
- stuck at a collision (stalled): 0% of episodes
- lateral bias: toward +Y (source/left side)
- mean closest EE-to-cube approach: 0.037 m

## Stall verdict
Not stalled -- training continues.