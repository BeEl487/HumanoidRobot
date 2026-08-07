# Self-monitoring analysis @ step 800,000
generated: 2026-08-07T17:49:21.715006+00:00

## Metrics trend (this window)
- reward now: -22.47
- reward trend slope: +0.0698 /log-tick (relative change over window: +18.6%)
- success rate now: 0.72
- success rate trend slope: -0.00001
- entropy: 1.085 (run start) -> 0.683 (now)
- value_loss std: 3.585, policy_loss std: 0.0030

## Simulation performance
- fps: 1834.5
- estimated remaining time: 0.18 hours (11 min)

## Behavior analysis (trajectory-based)
- entered the source box: 100% of episodes
- approached the cube (<5cm): 80% of episodes
- reached the cube but never grasped: 20% of episodes
- grasped but never lifted: 0% of episodes
- lifted but never transported toward the goal: 0% of episodes
- oscillating end-effector motion: 20% of episodes
- stuck at a collision (stalled): 0% of episodes
- lateral bias: toward +Y (source/left side)
- mean closest EE-to-cube approach: 0.037 m

## Stall verdict
Not stalled -- training continues.