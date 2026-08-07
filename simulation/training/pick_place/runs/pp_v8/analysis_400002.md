# Self-monitoring analysis @ step 400,002
generated: 2026-08-07T11:30:28.219698+00:00

## Metrics trend (this window)
- reward now: 165.22
- reward trend slope: +3.5392 /log-tick (relative change over window: +128.5%)
- success rate now: 0.48
- success rate trend slope: +0.00286
- entropy: 1.555 (run start) -> 0.987 (now)
- value_loss std: 148.433, policy_loss std: 0.0047

## Simulation performance
- fps: n/a

## Behavior analysis (trajectory-based)
- entered the source box: 100% of episodes
- approached the cube (<5cm): 100% of episodes
- reached the cube but never grasped: 40% of episodes
- grasped but never lifted: 50% of episodes
- lifted but never transported toward the goal: 10% of episodes
- oscillating end-effector motion: 20% of episodes
- stuck at a collision (stalled): 10% of episodes
- lateral bias: toward +Y (source/left side)
- mean closest EE-to-cube approach: 0.027 m

## Stall verdict
Not stalled -- training continues.