import unittest

import torch

from simulation.training.camera_pick_place.vision_grasp_model import CameraBinSorter, make_sort_plan


class CameraBinSorterTests(unittest.TestCase):
    def test_model_predicts_grasp_and_destination_class(self):
        model = CameraBinSorter(num_bins=3)
        grasp_xyz, bin_logits = model(torch.rand(4, 3, 64, 64))
        self.assertEqual(tuple(grasp_xyz.shape), (4, 3))
        self.assertEqual(tuple(bin_logits.shape), (4, 3))

    def test_sort_plan_uses_calibrated_bin_pose(self):
        grasp_xyz = torch.tensor([[0.1, 0.2, 0.3]])
        bin_logits = torch.tensor([[0.0, 4.0]])
        bin_poses = torch.tensor([[0.4, 0.5, 0.6], [-0.4, 0.5, 0.6]])
        plan = make_sort_plan(grasp_xyz, bin_logits, bin_poses)
        self.assertEqual(plan["bin_index"].item(), 1)
        self.assertTrue(torch.equal(plan["place_end_effector_xyz"], bin_poses[1:2]))


if __name__ == "__main__":
    unittest.main()
