# Self-monitoring analysis @ step 1,600,008
generated: 2026-08-07T11:49:33.920659+00:00

## Metrics trend (this window)
- reward now: 175.33
- reward trend slope: -2.2269 /log-tick (relative change over window: -76.2%)
- success rate now: 0.26
- success rate trend slope: +0.00038
- entropy: 1.497 (run start) -> 0.009 (now) -- COLLAPSED EARLY
- value_loss std: 80.992, policy_loss std: 0.0054

## Simulation performance
- fps: n/a

## Behavior analysis (trajectory-based)
- entered the source box: 100% of episodes
- approached the cube (<5cm): 90% of episodes
- reached the cube but never grasped: 40% of episodes
- grasped but never lifted: 50% of episodes
- lifted but never transported toward the goal: 0% of episodes
- oscillating end-effector motion: 30% of episodes
- stuck at a collision (stalled): 20% of episodes
- lateral bias: toward +Y (source/left side)
- mean closest EE-to-cube approach: 0.028 m

## Stall verdict
Not stalled -- training continues.