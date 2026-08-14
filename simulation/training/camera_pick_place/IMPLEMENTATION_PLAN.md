# Camera pick-and-place implementation plan

This document is the working implementation roadmap for the camera-based pick-and-place effort.

## 1. Environment setup

- Reuse the existing MuJoCo simulation environment and vision wrapper pattern.
- Add a small camera-based training entrypoint that exposes RGB observations from the head camera.
- Keep the first task single-object and single-destination.

## 2. Observation stack

- Use the rendered RGB image from the camera as the main visual input.
- Keep the task state available as auxiliary observations if needed for debugging.
- Start with a simple observation contract: image + basic state values.

## 3. Lightweight trainable camera sorter

A simple supervised baseline should be added before the full RL loop:
- use a small CNN regressor that maps RGB images to a 3D end-effector target $(x, y, z)$,
- train it on a few hundred labeled images of the actual object and target poses,
- keep the model lightweight so it can train quickly on CPU or a small GPU,
- and make the output directly usable as a grasp target for a downstream motion planner.

The implementation uses a small PyTorch regressor in [simulation/training/camera_pick_place/vision_grasp_model.py](simulation/training/camera_pick_place/vision_grasp_model.py).

For bin sorting, `CameraBinSorter` has two learned outputs from one RGB frame:
- a 3D pick end-effector target $(x, y, z)$ in the calibrated robot-base frame, and
- destination-bin logits for the known set of bins.

The destination placement target is deliberately not regressed from the image. The winning bin
class indexes a measured `bin_poses_robot` table, yielding a calibrated 3D place end-effector
target. This keeps the training labels simple (`image_path,x,y,z,bin_label`) and means that bin
placement remains deterministic, inspectable, and safe to validate against the scripted pipeline.

Train it with `train_camera_bin_sorter.py <manifest.csv>`. The model checkpoint stores the
bin-label mapping together with its weights. This is the initial trainable baseline; upgrade to
YOLOv8-seg or Mask R-CNN only when fixed-object RGB classification and the current mask/depth
baseline stop meeting the measured success requirement in `WORKFLOW.md`.

## 4. Policy training

- Use PPO with a MultiInputPolicy because the observation space is a dict-based image observation.
- Keep the policy network small at first for fast iteration.
- Train on a simple pick-and-place task rather than a broad multi-object setup.

## 5. Scripted baseline

- Add a scripted baseline that can estimate a grasp from the image.
- Use a simple object-mask or centroid-based approach for the earliest version.
- Keep the baseline deterministic so it can be used as a debugging tool.

## 6. Verification and rollout

- Run smoke tests that confirm the environment resets, renders an RGB frame, and builds a policy.
- Record a few rollout videos or screenshots to confirm the policy is reacting to the object.
- Treat the scripted baseline as a sanity check before RL training is trusted.

## 7. Next implementation steps

1. Add a small camera-based config for the training run.
2. Add a trainer entrypoint that can run a short PPO training loop.
3. Add a scripted baseline that uses the camera image.
4. Add rollout logging and evaluation output.
5. Expand to a more realistic grasp-and-place setup once the first baseline is stable.

## 8. RGB-D source-to-destination cube transfer

The first learned full-task baseline now reuses `SuctionPickPlaceEnv`, the existing source-box to
destination-box task with its staged reward, curriculum, suction command, checkpointing and
evaluation discipline. `RGBDVisionWrapper` replaces the policy's simulator-only `cube_pos` and
`dest_pos` inputs with a rendered head-camera RGB-D frame. The remaining observation keys are
signals a real robot can obtain: joint encoders, joint velocity, forward-kinematic end-effector
pose, suction command and suction/vacuum state.

`RGBDProprioExtractor` trains PPO on the four camera channels and those proprioceptive signals.
`rgbd_point_cloud.py` supplies RGB-D projection and robust cluster-centroid primitives for the
parallel scripted perception diagnostic; it does not leak MuJoCo object coordinates into training.
The initial cube task does not need YOLO: the policy is trained end-to-end from rendered RGB-D.
Add YOLOv8-seg only when multi-object/category selection is introduced, then feed its mask into
the same point-cloud projection path.
