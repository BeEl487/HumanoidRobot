# Self-monitoring analysis @ step 400,000
generated: 2026-08-07T16:42:04.606982+00:00

## Metrics trend (this window)
- reward now: -77.97
- reward trend slope: +1.5914 /log-tick (relative change over window: +122.5%)
- success rate now: 0.45
- success rate trend slope: +0.00186
- entropy: 5.658 (run start) -> 5.045 (now)
- value_loss std: 10.549, policy_loss std: 0.0010

## Simulation performance
- fps: 2100.6
- estimated remaining time: 0.21 hours (13 min)

## Behavior analysis (trajectory-based)
- entered the source box: 100% of episodes
- approached the cube (<5cm): 0% of episodes
- reached the cube but never grasped: 0% of episodes
- grasped but never lifted: 0% of episodes
- lifted but never transported toward the goal: 0% of episodes
- oscillating end-effector motion: 70% of episodes
- stuck at a collision (stalled): 40% of episodes
- lateral bias: toward +Y (source/left side)
- mean closest EE-to-cube approach: 0.106 m

## Stall verdict
Not stalled -- training continues.