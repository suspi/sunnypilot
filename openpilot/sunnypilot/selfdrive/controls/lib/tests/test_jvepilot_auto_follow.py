"""suspi: jvePilot Auto Follow (pure logic)."""
import unittest

from openpilot.sunnypilot.selfdrive.controls.lib.jvepilot_auto_follow import LONG_PRESS_FRAMES, MPH_TO_MS, AutoFollow

BANDS = (15, 30, 65)


class TestAutoFollow(unittest.TestCase):
  def test_bars_by_speed(self):
    for mph, bars in ((10, 0), (20, 1), (50, 2), (70, 3)):
      self.assertEqual(AutoFollow(True).update(mph * MPH_TO_MS, -1, False, BANDS), bars)

  def test_no_request_when_already_there(self):
    self.assertEqual(AutoFollow(True).update(50 * MPH_TO_MS, 2, False, BANDS), -1)

  def test_lock_holds_near_crossover(self):
    af = AutoFollow(True)
    self.assertEqual(af.update(31 * MPH_TO_MS, 1, False, BANDS), 2)  # crossed 30 mph: go to 2 bars, lock it
    self.assertEqual(af.update(29 * MPH_TO_MS, 2, False, BANDS), -1)  # 1 mph back below: held by the lock
    self.assertEqual(af.update(26 * MPH_TO_MS, 2, False, BANDS), 1)   # more than 3 mph below: back to 1 bar

  def test_disabled_makes_no_request(self):
    self.assertEqual(AutoFollow(False).update(70 * MPH_TO_MS, 0, False, BANDS), -1)

  def test_short_press_turns_off_long_press_turns_on(self):
    af = AutoFollow(True)
    for _ in range(10):
      af.update(50 * MPH_TO_MS, 2, True, BANDS)
    af.update(50 * MPH_TO_MS, 2, False, BANDS)
    self.assertFalse(af.enabled)
    for _ in range(LONG_PRESS_FRAMES):
      af.update(50 * MPH_TO_MS, 2, True, BANDS)
    self.assertTrue(af.enabled)
    af.update(50 * MPH_TO_MS, 2, False, BANDS)  # releasing the long press does not turn it off again
    self.assertTrue(af.enabled)


if __name__ == "__main__":
  unittest.main()
