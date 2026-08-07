# Self-monitoring analysis @ step 1,200,006
generated: 2026-08-07T11:43:37.189638+00:00

## Metrics trend (this window)
- reward now: 194.85
- reward trend slope: -0.1290 /log-tick (relative change over window: -4.0%)
- success rate now: 0.29
- success rate trend slope: -0.00138
- entropy: 1.518 (run start) -> 0.345 (now) -- COLLAPSED EARLY
- value_loss std: 100.992, policy_loss std: 0.0067

## Simulation performance
- fps: n/a

## Behavior analysis (trajectory-based)
- entered the source box: 100% of episodes
- approached the cube (<5cm): 90% of episodes
- reached the cube but never grasped: 50% of episodes
- grasped but never lifted: 30% of episodes
- lifted but never transported toward the goal: 10% of episodes
- oscillating end-effector motion: 80% of episodes
- stuck at a collision (stalled): 30% of episodes
- lateral bias: toward +Y (source/left side)
- mean closest EE-to-cube approach: 0.033 m

## Stall verdict
Not stalled -- training continues.