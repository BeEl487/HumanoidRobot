# Self-monitoring analysis @ step 2,000,000
generated: 2026-08-07T17:41:04.303927+00:00

## Metrics trend (this window)
- reward now: -72.88
- reward trend slope: +0.0114 /log-tick (relative change over window: +0.9%)
- success rate now: 0.41
- success rate trend slope: +0.00090
- entropy: 2.709 (run start) -> 1.228 (now)
- value_loss std: 4.724, policy_loss std: 0.0033

## Simulation performance
- fps: 5238.5
- estimated remaining time: 0.00 hours (0 min)

## Behavior analysis (trajectory-based)
- entered the source box: 100% of episodes
- approached the cube (<5cm): 80% of episodes
- reached the cube but never grasped: 30% of episodes
- grasped but never lifted: 0% of episodes
- lifted but never transported toward the goal: 0% of episodes
- oscillating end-effector motion: 40% of episodes
- stuck at a collision (stalled): 0% of episodes
- lateral bias: toward +Y (source/left side)
- mean closest EE-to-cube approach: 0.034 m

## Stall verdict
Not stalled -- training continues.