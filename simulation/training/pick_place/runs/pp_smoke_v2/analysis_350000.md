# Self-monitoring analysis @ step 350,000
generated: 2026-08-07T11:21:21.819752+00:00

## Metrics trend (this window)
- reward now: -50.10
- reward trend slope: +0.0006 /log-tick (relative change over window: +0.1%)
- success rate now: 0.0
- success rate trend slope: +0.00000
- entropy: 0.050 (run start) -> 0.050 (now)
- value_loss std: 0.000, policy_loss std: 0.0000

## Simulation performance
- fps: 800.0
- estimated remaining time: 0.57 hours (34 min)

## Behavior analysis (trajectory-based)
- entered the source box: 0% of episodes
- approached the cube (<5cm): 0% of episodes
- reached the cube but never grasped: 0% of episodes
- grasped but never lifted: 0% of episodes
- lifted but never transported toward the goal: 0% of episodes
- oscillating end-effector motion: 0% of episodes
- stuck at a collision (stalled): 0% of episodes
- lateral bias: toward -Y (destination/right side)
- mean closest EE-to-cube approach: 0.343 m

## Stall verdict
STALLED -- see below.

## Diagnosis (metrics-based, preliminary)
Training was stopped automatically: reward and success rate showed no meaningful improvement over the analysis window, and policy entropy had already collapsed early relative to the run's own start -- the combination this project treats as 'stuck', not just normal PPO noise.

This report is metrics-only. A visual review of the rendered rollout video (checkpoints/videos in this run directory) is needed to confirm which failure mode the behavior-analysis fractions above point to before deciding the next fix -- see the agent's follow-up message/log for that visual pass.