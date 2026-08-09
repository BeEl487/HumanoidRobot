# Self-monitoring analysis @ step 800,000
generated: 2026-08-07T12:38:23.263078+00:00

## Metrics trend (this window)
- reward now: -85.82
- reward trend slope: +0.0260 /log-tick (relative change over window: +1.8%)
- success rate now: 0.4
- success rate trend slope: -0.00159
- entropy: -0.121 (run start) -> 2.459 (now) -- COLLAPSED EARLY
- value_loss std: 5.896, policy_loss std: 0.0016

## Simulation performance
- fps: 782.7
- estimated remaining time: 0.43 hours (26 min)

## Behavior analysis (trajectory-based)
- entered the source box: 100% of episodes
- approached the cube (<5cm): 100% of episodes
- reached the cube but never grasped: 10% of episodes
- grasped but never lifted: 90% of episodes
- lifted but never transported toward the goal: 0% of episodes
- oscillating end-effector motion: 10% of episodes
- stuck at a collision (stalled): 0% of episodes
- lateral bias: toward +Y (source/left side)
- mean closest EE-to-cube approach: 0.029 m

## Stall verdict
STALLED -- see below.

## Diagnosis (metrics-based, preliminary)
Training was stopped automatically: reward and success rate showed no meaningful improvement over the analysis window, and policy entropy had already collapsed early relative to the run's own start -- the combination this project treats as 'stuck', not just normal PPO noise.

This report is metrics-only. A visual review of the rendered rollout video (checkpoints/videos in this run directory) is needed to confirm which failure mode the behavior-analysis fractions above point to before deciding the next fix -- see the agent's follow-up message/log for that visual pass.