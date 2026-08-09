# Self-monitoring analysis @ step 1,200,000
generated: 2026-08-07T15:52:59.683118+00:00

## Metrics trend (this window)
- reward now: -58.26
- reward trend slope: -0.1581 /log-tick (relative change over window: -16.3%)
- success rate now: 0.63
- success rate trend slope: -0.00088
- entropy: 2.064 (run start) -> 2.547 (now)
- value_loss std: 0.819, policy_loss std: 0.0024

## Simulation performance
- fps: 670.0
- estimated remaining time: 0.33 hours (20 min)

## Behavior analysis (trajectory-based)
- entered the source box: 100% of episodes
- approached the cube (<5cm): 80% of episodes
- reached the cube but never grasped: 40% of episodes
- grasped but never lifted: 40% of episodes
- lifted but never transported toward the goal: 0% of episodes
- oscillating end-effector motion: 20% of episodes
- stuck at a collision (stalled): 0% of episodes
- lateral bias: toward +Y (source/left side)
- mean closest EE-to-cube approach: 0.036 m

## Stall verdict
Not stalled -- training continues.