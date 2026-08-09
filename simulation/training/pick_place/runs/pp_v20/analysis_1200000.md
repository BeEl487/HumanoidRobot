# Self-monitoring analysis @ step 1,200,000
generated: 2026-08-07T16:48:19.584056+00:00

## Metrics trend (this window)
- reward now: -93.88
- reward trend slope: -0.2949 /log-tick (relative change over window: -18.8%)
- success rate now: 0.49
- success rate trend slope: +0.00028
- entropy: 5.601 (run start) -> 3.402 (now)
- value_loss std: 3.104, policy_loss std: 0.0014

## Simulation performance
- fps: 2056.8
- estimated remaining time: 0.11 hours (6 min)

## Behavior analysis (trajectory-based)
- entered the source box: 100% of episodes
- approached the cube (<5cm): 10% of episodes
- reached the cube but never grasped: 10% of episodes
- grasped but never lifted: 0% of episodes
- lifted but never transported toward the goal: 0% of episodes
- oscillating end-effector motion: 90% of episodes
- stuck at a collision (stalled): 0% of episodes
- lateral bias: toward +Y (source/left side)
- mean closest EE-to-cube approach: 0.071 m

## Stall verdict
Not stalled -- training continues.