"""suspi: jvePilot Slow in Curves (pure logic)."""
import math
import unittest

from openpilot.sunnypilot.selfdrive.controls.lib.jvepilot_curves import limit_speed_in_curve


class TestJvePilotCurves(unittest.TestCase):
  def test_matches_jvepilot_formula(self):
    v, k = 25.0, 0.01
    a = 2.975 - v * 0.0375
    self.assertAlmostEqual(limit_speed_in_curve(v, k), math.sqrt(a / k))

  def test_ratio_scales_and_sign_is_ignored(self):
    self.assertAlmostEqual(limit_speed_in_curve(20.0, -0.02, ratio=0.8), 0.8 * limit_speed_in_curve(20.0, 0.02))

  def test_drop_off_changes_curve(self):
    v, k = 30.0, 0.005
    a = 2.975 - v * 0.0375
    self.assertAlmostEqual(limit_speed_in_curve(v, k, drop_off=1.5), math.sqrt(math.sqrt(a) ** 1.5 / k))

  def test_tiny_curvature_is_clipped(self):
    self.assertAlmostEqual(limit_speed_in_curve(10.0, 1e-9), limit_speed_in_curve(10.0, 1e-4))

  def test_no_limit_at_absurd_speed(self):
    self.assertEqual(limit_speed_in_curve(100.0, 0.01), math.inf)


if __name__ == "__main__":
  unittest.main()
