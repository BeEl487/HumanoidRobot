# Self-monitoring analysis @ step 1,600,000
generated: 2026-08-07T13:44:59.141862+00:00

## Metrics trend (this window)
- reward now: -102.13
- reward trend slope: -0.4376 /log-tick (relative change over window: -25.7%)
- success rate now: 0.22
- success rate trend slope: -0.00077
- entropy: 2.557 (run start) -> 2.500 (now)
- value_loss std: 1.280, policy_loss std: 0.0027

## Simulation performance
- fps: 652.8
- estimated remaining time: 0.17 hours (10 min)

## Behavior analysis (trajectory-based)
- entered the source box: 100% of episodes
- approached the cube (<5cm): 100% of episodes
- reached the cube but never grasped: 70% of episodes
- grasped but never lifted: 20% of episodes
- lifted but never transported toward the goal: 10% of episodes
- oscillating end-effector motion: 0% of episodes
- stuck at a collision (stalled): 0% of episodes
- lateral bias: toward +Y (source/left side)
- mean closest EE-to-cube approach: 0.033 m

## Stall verdict
Not stalled -- training continues.