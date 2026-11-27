"""suspi: jvePilot personality from ACC bars and Eco (pure logic)."""
import unittest

from openpilot.sunnypilot.selfdrive.controls.lib.jvepilot_personality import (
  AGGRESSIVE, RELAXED, STANDARD, personality, t_follow)


class TestJvePilotPersonality(unittest.TestCase):
  def test_table_matches_jvepilot(self):
    # jvePilot values.py DRIVE_PERSONALITY, raw: [[0,0,1,2],[0,1,1,2],[0,1,2,2]]
    self.assertEqual([personality(0, b) for b in range(4)], [0, 0, 1, 2])
    self.assertEqual([personality(1, b) for b in range(4)], [0, 1, 1, 2])
    self.assertEqual([personality(2, b) for b in range(4)], [0, 1, 2, 2])

  def test_enum_matches_cereal(self):
    self.assertEqual((AGGRESSIVE, STANDARD, RELAXED), (0, 1, 2))  # log.capnp LongitudinalPersonality

  def test_out_of_range_inputs_clamp(self):
    self.assertEqual(personality(5, 9), RELAXED)
    self.assertEqual(personality(-1, -1), AGGRESSIVE)

  def test_follow_times(self):
    self.assertEqual(t_follow(RELAXED, 1.6, 1.2, 1.0), 1.6)
    self.assertEqual(t_follow(STANDARD, 1.6, 1.2, 1.0), 1.2)
    self.assertEqual(t_follow(AGGRESSIVE, 1.6, 1.2, 1.0), 1.0)


if __name__ == "__main__":
  unittest.main()
