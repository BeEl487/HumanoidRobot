import unittest

import numpy as np

from simulation.sim_env.rgbd_vision_wrapper import RGBDVisionWrapper
from simulation.sim_env.suction_pick_place_env import SuctionPickPlaceEnv
from simulation.training.camera_pick_place.rgbd_point_cloud import (
    depth_to_point_cloud,
    robust_cluster_centroid,
)
from simulation.training.camera_pick_place.train_rgbd_pick_place import build_model, make_env


class RGBDPickPlaceTests(unittest.TestCase):
    def test_rgbd_wrapper_excludes_privileged_poses(self):
        env = RGBDVisionWrapper(SuctionPickPlaceEnv())
        try:
            observation, _ = env.reset(seed=0)
            self.assertEqual(observation["rgb"].shape[0], 3)
            self.assertEqual(observation["depth"].shape[0], 1)
            self.assertTrue(np.isfinite(observation["depth"]).all())
            self.assertNotIn("cube_pos", observation)
            self.assertNotIn("dest_pos", observation)
        finally:
            env.close()

    def test_point_cloud_projection_and_outlier_filter(self):
        depth = np.array([[1.0, 1.0], [1.0, 5.0]], dtype=np.float32)
        points = depth_to_point_cloud(depth, (1.0, 1.0, 0.0, 0.0))
        centroid = robust_cluster_centroid(points)
        self.assertEqual(points.shape, (4, 3))
        self.assertLess(centroid[2], 2.0)

    def test_rgbd_policy_builds_and_steps(self):
        env = make_env(seed=0)
        try:
            observation = env.reset()
            self.assertIn("rgb", observation)
            model = build_model(env, seed=0)
            self.assertIsNotNone(model)
        finally:
            env.close()


if __name__ == "__main__":
    unittest.main()
