# Self-monitoring analysis @ step 2,000,010
generated: 2026-08-07T11:57:44.612080+00:00

## Metrics trend (this window)
- reward now: 287.39
- reward trend slope: +4.2843 /log-tick (relative change over window: +89.4%)
- success rate now: 0.12
- success rate trend slope: -0.00088
- entropy: 1.492 (run start) -> -0.461 (now) -- COLLAPSED EARLY
- value_loss std: 128.096, policy_loss std: 0.0059

## Simulation performance
- fps: n/a

## Behavior analysis (trajectory-based)
- entered the source box: 100% of episodes
- approached the cube (<5cm): 100% of episodes
- reached the cube but never grasped: 10% of episodes
- grasped but never lifted: 80% of episodes
- lifted but never transported toward the goal: 10% of episodes
- oscillating end-effector motion: 20% of episodes
- stuck at a collision (stalled): 20% of episodes
- lateral bias: toward +Y (source/left side)
- mean closest EE-to-cube approach: 0.024 m

## Stall verdict
Not stalled -- training continues.