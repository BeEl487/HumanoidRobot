import unittest

import torch
import torch.nn.functional as F

from simulation.training.camera_pick_place.vision_grasp_model import SimpleEndEffectorRegressor


class EndEffectorRegressorTests(unittest.TestCase):
    def test_model_outputs_3d_positions(self):
        model = SimpleEndEffectorRegressor(image_size=(64, 64))
        images = torch.rand(4, 3, 64, 64)
        positions = model(images)

        self.assertEqual(tuple(positions.shape), (4, 3))
        self.assertTrue(torch.isfinite(positions).all())

    def test_training_step_runs(self):
        model = SimpleEndEffectorRegressor(image_size=(64, 64))
        images = torch.rand(8, 3, 64, 64)
        targets = torch.rand(8, 3)

        predictions = model(images)
        loss = F.mse_loss(predictions, targets)
        loss.backward()

        self.assertTrue(torch.isfinite(loss))


if __name__ == "__main__":
    unittest.main()
