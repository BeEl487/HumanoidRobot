# Self-monitoring analysis @ step 1,200,000
generated: 2026-08-07T17:16:32.797359+00:00

## Metrics trend (this window)
- reward now: -145.34
- reward trend slope: +0.2967 /log-tick (relative change over window: +12.3%)
- success rate now: 0.23
- success rate trend slope: +0.00233
- entropy: 5.618 (run start) -> 3.795 (now)
- value_loss std: 2.008, policy_loss std: 0.0013

## Simulation performance
- fps: 2022.1
- estimated remaining time: 0.11 hours (7 min)

## Behavior analysis (trajectory-based)
- entered the source box: 100% of episodes
- approached the cube (<5cm): 10% of episodes
- reached the cube but never grasped: 10% of episodes
- grasped but never lifted: 0% of episodes
- lifted but never transported toward the goal: 0% of episodes
- oscillating end-effector motion: 50% of episodes
- stuck at a collision (stalled): 50% of episodes
- lateral bias: toward +Y (source/left side)
- mean closest EE-to-cube approach: 0.069 m

## Stall verdict
Not stalled -- training continues.