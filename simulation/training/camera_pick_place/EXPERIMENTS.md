# Camera-based pick-place: experiment ledger

This file tracks the initial camera-based experiments for the new RGB-D pick-and-place series. The format mirrors the existing suction pick-place experiment ledger so new runs are easy to compare.

| # | Run | Parent checkpoint | Perception changes | Grasp / motion changes | Scene / workspace changes | Success notes | Reason ended |
|---|---|---|---|---|---|---|---|
| 1 | cam_v1 | none (fresh) | Baseline RGB-D segmentation using a simple object mask from RGB and aligned depth with a RealSense D435i | Conservative side-approach grasp candidate from the segmented point cloud | Single cube/object on a flat surface, simple bin or table workspace | Baseline proof-of-concept | Initial setup and sanity check |
| 2 | cam_v2 | cam_v1 | Same perception stack, but add filtering and outlier removal | Add reachability-aware grasp ranking and prefer a side-oblique approach with an occlusion check | Same scene, but with reachability checks enabled | First reachability-aware grasp executed | Gather first motion/perception integration data |
| 3 | cam_v3 | cam_v2 | Add hand-eye calibration and a depth-range safety gate before grasp execution | Add simple pick-then-verify-then-place sequence with Iq-based grasp feedback | Add one destination bin or sorting zone | First full pick-and-place loop with in-grasp feedback | Validate feedback loop and object verification |
