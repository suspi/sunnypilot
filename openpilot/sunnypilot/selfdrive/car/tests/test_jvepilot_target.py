"""suspi: jvePilot plan-following ACC target (pure logic, no cereal)."""
import unittest

from openpilot.sunnypilot.selfdrive.car.intelligent_cruise_button_management.jvepilot_target import (
  COAST_OFFSET, EXTEND_FUTURE_MAX, HYSTERESIS_DOWN, KPH_TO_MS, MPH_TO_MS, PlanAccTarget, allow_throttle, to_cluster_units)

HIGH = 40.0  # m/s, a driver set speed that never caps


class TestPlanAccTarget(unittest.TestCase):
  def test_follows_mean_planned_speed_plus_half_kph(self):
    t = PlanAccTarget().update(20.0, [18.0, 20.0, 22.0], [0.0, 0.0, 0.0], True, HIGH)
    self.assertAlmostEqual(t, 20.0 + KPH_TO_MS / 2)

  def test_accel_lookahead_is_capped(self):
    t = PlanAccTarget().update(20.0, [20.0], [10.0], True, HIGH)
    self.assertAlmostEqual(t, 20.0 + EXTEND_FUTURE_MAX + KPH_TO_MS / 2)

  def test_coasts_below_vego_when_throttle_not_allowed(self):
    tgt = PlanAccTarget()
    tgt.last_target = 0.0
    self.assertAlmostEqual(tgt.update(25.0, [26.0], [0.0], False, HIGH), 25.0 - COAST_OFFSET)

  def test_hysteresis_holds_small_drops_and_follows_large_ones(self):
    tgt = PlanAccTarget()
    first = tgt.update(20.0, [20.0], [0.0], True, HIGH)
    self.assertAlmostEqual(tgt.update(20.0, [20.0 - HYSTERESIS_DOWN / 2], [0.0], True, HIGH), first)
    low = 20.0 - 2 * HYSTERESIS_DOWN
    self.assertAlmostEqual(tgt.update(20.0, [low], [0.0], True, HIGH), low + KPH_TO_MS / 2)

  def test_driver_set_speed_caps(self):
    self.assertAlmostEqual(PlanAccTarget().update(20.0, [30.0], [0.0], True, 25.0), 25.0)

  def test_eco_keeps_target_near_vego(self):
    v = 15.0  # below 20 mph-equivalent reduction kicks in later; rate 0 here
    t = PlanAccTarget().update(v, [30.0], [0.0], True, HIGH, eco_level=1, eco_ahead1_mph=7, eco_rate=0.0)
    self.assertAlmostEqual(t, v + 7 * MPH_TO_MS)
    t2 = PlanAccTarget().update(v, [30.0], [0.0], True, HIGH, eco_level=2, eco_ahead2_mph=5, eco_rate=0.0)
    self.assertAlmostEqual(t2, v + 5 * MPH_TO_MS)

  def test_eco_reduction_above_20mph_floors_at_2(self):
    v = 30.0
    rate = 1.0  # diff = (30 - 8.94) * 1 = 21.06, not < 7 -> no reduction applied (as in jvePilot)
    t = PlanAccTarget().update(v, [40.0], [0.0], True, HIGH, eco_level=1, eco_ahead1_mph=7, eco_rate=rate)
    self.assertAlmostEqual(t, v + 7 * MPH_TO_MS)
    rate = 0.2  # diff = 4.21 -> limit 7 - 4.21 = 2.79 mph
    t = PlanAccTarget().update(v, [40.0], [0.0], True, HIGH, eco_level=1, eco_ahead1_mph=7, eco_rate=rate)
    self.assertAlmostEqual(t, v + (7 - (v - 20 * MPH_TO_MS) * rate) * MPH_TO_MS)

  def test_empty_plan_targets_zero(self):
    self.assertEqual(PlanAccTarget().update(20.0, [], [], True, HIGH), 0.0)

  def test_allow_throttle(self):
    self.assertTrue(allow_throttle(20.0, []))            # no model output: never coast
    self.assertFalse(allow_throttle(20.0, [0.9, 0.1]))
    self.assertTrue(allow_throttle(20.0, [0.9, 0.5]))
    self.assertTrue(allow_throttle(2.0, [0.9, 0.1]))     # crawling: always allowed

  def test_cluster_units_floor(self):
    self.assertEqual(to_cluster_units(29.9 * MPH_TO_MS, False), 29)
    self.assertEqual(to_cluster_units(50.5 / 3.6, True), 50)


if __name__ == "__main__":
  unittest.main()
