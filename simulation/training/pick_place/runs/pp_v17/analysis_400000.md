# Self-monitoring analysis @ step 400,000
generated: 2026-08-07T15:38:20.756372+00:00

## Metrics trend (this window)
- reward now: -26.33
- reward trend slope: -0.1873 /log-tick (relative change over window: -42.7%)
- success rate now: 0.77
- success rate trend slope: -0.00105
- entropy: 2.059 (run start) -> 2.330 (now)
- value_loss std: 1.590, policy_loss std: 0.0027

## Simulation performance
- fps: 667.2
- estimated remaining time: 0.67 hours (40 min)

## Behavior analysis (trajectory-based)
- entered the source box: 100% of episodes
- approached the cube (<5cm): 70% of episodes
- reached the cube but never grasped: 50% of episodes
- grasped but never lifted: 20% of episodes
- lifted but never transported toward the goal: 0% of episodes
- oscillating end-effector motion: 20% of episodes
- stuck at a collision (stalled): 0% of episodes
- lateral bias: toward +Y (source/left side)
- mean closest EE-to-cube approach: 0.040 m

## Stall verdict
Not stalled -- training continues.