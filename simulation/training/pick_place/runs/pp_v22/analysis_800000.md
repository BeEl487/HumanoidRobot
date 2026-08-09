# Self-monitoring analysis @ step 800,000
generated: 2026-08-07T17:13:26.443050+00:00

## Metrics trend (this window)
- reward now: -205.73
- reward trend slope: +0.2788 /log-tick (relative change over window: +8.1%)
- success rate now: 0.16
- success rate trend slope: +0.00256
- entropy: 5.648 (run start) -> 4.326 (now)
- value_loss std: 3.493, policy_loss std: 0.0011

## Simulation performance
- fps: 2064.0
- estimated remaining time: 0.16 hours (10 min)

## Behavior analysis (trajectory-based)
- entered the source box: 100% of episodes
- approached the cube (<5cm): 20% of episodes
- reached the cube but never grasped: 10% of episodes
- grasped but never lifted: 0% of episodes
- lifted but never transported toward the goal: 10% of episodes
- oscillating end-effector motion: 70% of episodes
- stuck at a collision (stalled): 80% of episodes
- lateral bias: toward +Y (source/left side)
- mean closest EE-to-cube approach: 0.058 m

## Stall verdict
Not stalled -- training continues.