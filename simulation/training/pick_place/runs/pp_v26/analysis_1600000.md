# Self-monitoring analysis @ step 1,600,000
generated: 2026-08-07T18:29:34.132335+00:00

## Metrics trend (this window)
- reward now: -33.99
- reward trend slope: -0.2606 /log-tick (relative change over window: -46.0%)
- success rate now: 0.66
- success rate trend slope: -0.00105
- entropy: 0.457 (run start) -> 0.545 (now)
- value_loss std: 2.963, policy_loss std: 0.0027

## Simulation performance
- fps: 1781.3
- estimated remaining time: 0.06 hours (4 min)

## Behavior analysis (trajectory-based)
- entered the source box: 100% of episodes
- approached the cube (<5cm): 100% of episodes
- reached the cube but never grasped: 40% of episodes
- grasped but never lifted: 0% of episodes
- lifted but never transported toward the goal: 0% of episodes
- oscillating end-effector motion: 40% of episodes
- stuck at a collision (stalled): 0% of episodes
- lateral bias: toward +Y (source/left side)
- mean closest EE-to-cube approach: 0.027 m

## Stall verdict
Not stalled -- training continues.