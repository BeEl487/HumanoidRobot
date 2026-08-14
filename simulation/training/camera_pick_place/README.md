# Camera-based pick-place experiment series

This folder is the new home for the camera-based pick-and-place experiments. It is structured like the existing pick-place experiment area so you can keep the same documentation and run-tracking pattern while exploring a different perception stack.

## First-principles plan

The first version should be deliberately conservative and should solve one problem at a time.

### Chosen camera

Use an Intel RealSense D435i for the first experiments. It is the best fit here because it is compact, RGB-D, well-supported, and well suited to a head-like mount above the robot body. It also has good community support for depth alignment, point-cloud processing, and simple integration with ROS/OpenCV/Python.

### MuJoCo implementation path

The first implementation milestone is now anchored in MuJoCo and uses the existing simulation environment plus a camera wrapper:
- [simulation/training/camera_pick_place/train_camera_pick_place.py](simulation/training/camera_pick_place/train_camera_pick_place.py)
- [simulation/config/camera_pick_place_train.yaml](simulation/config/camera_pick_place_train.yaml)
- [simulation/training/camera_pick_place/IMPLEMENTATION_PLAN.md](simulation/training/camera_pick_place/IMPLEMENTATION_PLAN.md)

### Phase 1: perception-only baseline

Focus:
- capture RGB and depth from the camera,
- align RGB and depth,
- segment a known object from RGB,
- project the mask into 3D,
- estimate a simple grasp candidate from the segmented point cluster.

### Phase 2: grasp and reachability

Focus:
- add reachability-aware grasp ranking,
- use the current arm geometry and joint limits to reject grasps that would force the arm into the camera line of sight or into a blocked pose,
- prefer a side or slightly elevated approach instead of a direct forward-then-down motion,
- add a fallback policy if the view becomes occluded during approach.

### Phase 3: pick-and-place execution

Focus:
- calibrate the camera-to-robot transform before using depth-based grasp poses,
- map the grasp pose from camera frame to robot frame,
- execute a pick motion,
- use motor-current telemetry (Iq) as a grasp-contact signal during the grasp itself,
- re-capture the scene after the move to verify the object left its original cluster,
- then move to the destination bin.

## Key design constraint

Your note about the arm blocking the camera is the main constraint for the first experiments. Because the arm appears to be unable to approach the cube from a direct forward-and-down path without occluding the camera or colliding with the motion envelope, the first experiments should bias the planner toward:
- a side approach,
- a slightly elevated approach,
- a grasp that is visible to the camera during approach,
- and a pose that avoids the arm moving straight into the camera frustum.

## Proposed experiment order

1. Baseline RGB-D segmentation and point-cloud projection
2. Reachability-aware grasp selection with a conservative approach direction
3. Closed-loop pick verification and destination placement
4. Optional extension to multiple object classes or simple bin sorting

## Open questions

The first implementation still needs a few decisions before the first script can be written:
- Is the object a known cube or a small set of known objects?
- Is the first grasp intended to be top-down, side-grasp, or a slight oblique approach?
- Is the object workspace a table surface, a bin, or a fixed shelf-like position?

### Clarification on the earlier question 5

When I asked whether the first version should use a side-approach policy, I meant this: yes, the first version should intentionally use a conservative side or slightly elevated approach rather than trying a direct forward-and-down motion if that blocks the camera or conflicts with the arm's reachability.

## Recommended first milestone

The first milestone should be narrow:
- detect and segment one object reliably,
- produce one 3D grasp candidate,
- move to it without blocking the camera,
- and execute a single successful pick-and-place cycle.

## Live camera sorter dashboard

After training `CameraBinSorter` with `train_camera_bin_sorter.py`, validate it with the
camera-only dashboard before connecting it to any robot command path. It overlays the predicted
pick end-effector XYZ, predicted destination bin and confidence, calibrated place end-effector
XYZ, inference latency, and camera FPS. It never sends motion or gripper commands.

Create a calibrated bin-pose JSON file from `bin_poses.example.json`, then run:

```powershell
.\.venv\Scripts\python.exe .\simulation\training\camera_pick_place\live_camera_bin_sorter.py `
  .\simulation\training\camera_pick_place\runs\camera_bin_sorter.pt `
  .\simulation\training\camera_pick_place\bin_poses.json
```

The positions in the JSON must be measured in the calibrated robot-base frame; do not use the
example values to move hardware.

For the current simulation-only stage, use the MuJoCo virtual head-camera dashboard instead. It
reads exactly the `VisionWrapper` RGB observation used in training, steps the simulated world, and
shows the same prediction/latency/FPS overlay:

```powershell
.\.venv\Scripts\python.exe .\simulation\training\camera_pick_place\live_mujoco_camera_sorter.py `
  .\simulation\training\camera_pick_place\runs\camera_bin_sorter.pt `
  .\simulation\training\camera_pick_place\bin_poses.json
```
