import unittest

import numpy as np
from numpy.testing import assert_allclose

from simulation.training.camera_pick_place.prototype_pipeline import (
    GraspCandidate,
    apply_hand_eye_transform,
    estimate_grasp_candidate,
    estimate_hand_eye_transform,
    evaluate_grasp_feedback,
    run_scripted_grasp_loop,
)


class CameraPickPlacePipelineTests(unittest.TestCase):
    def test_estimate_grasp_candidate_from_synthetic_rgbd(self):
        rgb = np.zeros((120, 120, 3), dtype=np.uint8)
        depth = np.full((120, 120), 0.0, dtype=np.float32)

        object_mask = np.zeros((120, 120), dtype=bool)
        object_mask[40:80, 40:80] = True
        rgb[40:80, 40:80] = [255, 0, 0]
        depth[40:80, 40:80] = 0.72

        candidate = estimate_grasp_candidate(
            rgb=rgb,
            depth=depth,
            object_mask=object_mask,
            depth_min_range_m=0.28,
            intrinsics=(300.0, 300.0, 60.0, 60.0),
        )

        self.assertIsInstance(candidate, GraspCandidate)
        self.assertGreater(candidate.confidence, 0.5)
        self.assertTrue(candidate.depth_range_ok)
        self.assertAlmostEqual(candidate.xyz_cam[2], 0.72, places=2)

    def test_hand_eye_transform_and_grasp_feedback(self):
        candidate = GraspCandidate(
            xyz_cam=np.array([0.1, 0.2, 0.3]),
            surface_normal=np.array([0.0, 0.0, 1.0]),
            approach_vector=np.array([0.0, 0.0, -1.0]),
            confidence=0.92,
            depth_range_ok=True,
            visible=True,
            reason="ok",
        )

        transform = np.array(
            [[1.0, 0.0, 0.0, 0.05],
             [0.0, 1.0, 0.0, -0.02],
             [0.0, 0.0, 1.0, 0.01],
             [0.0, 0.0, 0.0, 1.0]],
            dtype=float,
        )

        robot_pose = apply_hand_eye_transform(candidate, transform)
        self.assertAlmostEqual(robot_pose[0], 0.15, places=6)
        self.assertAlmostEqual(robot_pose[1], 0.18, places=6)
        self.assertAlmostEqual(robot_pose[2], 0.31, places=6)

        self.assertTrue(evaluate_grasp_feedback([0.0, 0.0, 0.9], threshold_ma=0.5))
        self.assertFalse(evaluate_grasp_feedback([0.0, 0.1, 0.2], threshold_ma=0.5))

    def test_estimate_hand_eye_transform(self):
        camera_points = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
        true_transform = np.array(
            [[0.0, -1.0, 0.0, 0.5],
             [1.0, 0.0, 0.0, -0.2],
             [0.0, 0.0, 1.0, 0.1],
             [0.0, 0.0, 0.0, 1.0]],
            dtype=float,
        )
        robot_points = np.array([true_transform[:3, :3] @ p + true_transform[:3, 3] for p in camera_points])

        estimated_transform = estimate_hand_eye_transform(camera_points, robot_points)
        assert_allclose(estimated_transform[:3, :3], true_transform[:3, :3], atol=1e-8)
        assert_allclose(estimated_transform[:3, 3], true_transform[:3, 3], atol=1e-8)

    def test_run_scripted_grasp_loop(self):
        rgb = np.zeros((120, 120, 3), dtype=np.uint8)
        depth = np.full((120, 120), 0.72, dtype=np.float32)
        object_mask = np.zeros((120, 120), dtype=bool)
        object_mask[40:80, 40:80] = True
        rgb[40:80, 40:80] = [255, 0, 0]

        camera_to_robot = np.eye(4, dtype=float)
        result = run_scripted_grasp_loop(
            rgb=rgb,
            depth=depth,
            object_mask=object_mask,
            intrinsics=(300.0, 300.0, 60.0, 60.0),
            camera_to_robot=camera_to_robot,
            depth_min_range_m=0.28,
            iq_samples=[0.0, 0.8],
            grasp_feedback_threshold_ma=0.5,
        )

        self.assertEqual(result["status"], "ready")
        self.assertTrue(result["grasp_succeeded"])
        self.assertIn("grasp_pose_robot", result)


if __name__ == "__main__":
    unittest.main()
