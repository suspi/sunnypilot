"""suspi: jvePilot personality from ACC bars and Eco (pure logic)."""
import unittest

from openpilot.sunnypilot.selfdrive.controls.lib.jvepilot_personality import (
  AGGRESSIVE, RELAXED, STANDARD, personality, t_follow)


class TestJvePilotPersonality(unittest.TestCase):
  def test_table_matches_jvepilot(self):
    self.assertEqual([personality(0, b) for b in range(4)], [RELAXED, RELAXED, STANDARD, AGGRESSIVE])
    self.assertEqual([personality(1, b) for b in range(4)], [RELAXED, STANDARD, STANDARD, AGGRESSIVE])
    self.assertEqual([personality(2, b) for b in range(4)], [RELAXED, STANDARD, AGGRESSIVE, AGGRESSIVE])

  def test_out_of_range_inputs_clamp(self):
    self.assertEqual(personality(5, 9), AGGRESSIVE)
    self.assertEqual(personality(-1, -1), RELAXED)

  def test_follow_times(self):
    self.assertEqual(t_follow(RELAXED, 1.6, 1.2, 1.0), 1.6)
    self.assertEqual(t_follow(STANDARD, 1.6, 1.2, 1.0), 1.2)
    self.assertEqual(t_follow(AGGRESSIVE, 1.6, 1.2, 1.0), 1.0)


if __name__ == "__main__":
  unittest.main()
