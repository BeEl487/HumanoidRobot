import unittest

import numpy as np
import torch

from simulation.training.camera_pick_place.live_camera_bin_sorter import (
    draw_dashboard,
    image_to_tensor,
)


class LiveCameraBinSorterTests(unittest.TestCase):
    def test_camera_frame_is_converted_to_model_tensor(self):
        frame_bgr = np.zeros((120, 160, 3), dtype=np.uint8)
        image = image_to_tensor(frame_bgr, torch.device("cpu"))
        self.assertEqual(tuple(image.shape), (1, 3, 64, 64))
        self.assertEqual(image.dtype, torch.float32)

    def test_dashboard_keeps_camera_frame_shape(self):
        frame_bgr = np.zeros((240, 320, 3), dtype=np.uint8)
        dashboard = draw_dashboard(
            frame_bgr,
            "recycling",
            0.9,
            np.array([0.1, 0.2, 0.3]),
            np.array([0.4, 0.5, 0.6]),
            12.0,
            30.0,
        )
        self.assertEqual(dashboard.shape, frame_bgr.shape)
        self.assertGreater(int(dashboard.sum()), 0)


if __name__ == "__main__":
    unittest.main()
