import pathlib
import sys
import unittest

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from train_camera_pick_place import make_env, build_model


class CameraPickPlaceTrainingTests(unittest.TestCase):
    def test_make_env_and_model(self):
        env = make_env(seed=0)
        obs = env.reset()
        self.assertIn("rgb", obs)
        self.assertEqual(obs["rgb"].shape[-1], 3)

        action = np.zeros(env.action_space.shape[0], dtype=np.float32)
        obs, reward, terminated, truncated = env.step(action)
        self.assertTrue(np.isfinite(reward).all())
        env.close()

        model = build_model(env, total_timesteps=8, seed=0)
        self.assertIsNotNone(model)


if __name__ == "__main__":
    unittest.main()
