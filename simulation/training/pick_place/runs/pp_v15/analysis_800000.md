# Self-monitoring analysis @ step 800,000
generated: 2026-08-07T14:36:09.231024+00:00

## Metrics trend (this window)
- reward now: -114.11
- reward trend slope: -0.4005 /log-tick (relative change over window: -21.1%)
- success rate now: 0.44
- success rate trend slope: -0.00092
- entropy: 2.494 (run start) -> 1.991 (now)
- value_loss std: 1.228, policy_loss std: 0.0040

## Simulation performance
- fps: 632.6
- estimated remaining time: 0.53 hours (32 min)

## Behavior analysis (trajectory-based)
- entered the source box: 100% of episodes
- approached the cube (<5cm): 90% of episodes
- reached the cube but never grasped: 0% of episodes
- grasped but never lifted: 90% of episodes
- lifted but never transported toward the goal: 0% of episodes
- oscillating end-effector motion: 10% of episodes
- stuck at a collision (stalled): 0% of episodes
- lateral bias: toward +Y (source/left side)
- mean closest EE-to-cube approach: 0.030 m

## Stall verdict
Not stalled -- training continues.