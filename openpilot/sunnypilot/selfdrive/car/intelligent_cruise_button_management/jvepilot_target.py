"""
suspi: jvePilot's plan-following ACC set speed, for Intelligent Cruise Button Management on Chrysler.

Ported from jvePilot-beta 1508b2a, opendbc/car/chrysler/carcontroller.py `hybrid_acc_button` and `acc_hysteresis`,
and selfdrive/controls/lib/longitudinal_planner.py (allow-throttle). Pure logic: no cereal, no params, so it is
unit-testable anywhere.
"""
import math

MPH_TO_MS = 0.44704
KPH_TO_MS = 1 / 3.6

EXTEND_FUTURE_MAX = 10 * MPH_TO_MS   # cap on the acceleration look-ahead added to the planned speed
COAST_OFFSET = 4 * MPH_TO_MS         # set speed below vEgo while the plan would lift off the throttle
HYSTERESIS_DOWN = 0.75 * MPH_TO_MS   # the target only drops once it is this far below its last value
ALLOW_THROTTLE_THRESHOLD = 0.4       # openpilot 0.10 planner: gas-press probability above which throttle is allowed
MIN_ALLOW_THROTTLE_SPEED = 2.5       # m/s; below this throttle is always allowed


def allow_throttle(v_ego: float, gas_press_probs) -> bool:
  """openpilot 0.10's allowThrottle, which the 0.11 planner no longer publishes."""
  throttle_prob = gas_press_probs[1] if len(gas_press_probs) > 1 else 1.0
  return throttle_prob > ALLOW_THROTTLE_THRESHOLD or v_ego <= MIN_ALLOW_THROTTLE_SPEED


def _mean(values) -> float:
  return sum(values) / len(values) if len(values) else 0.0


class PlanAccTarget:
  def __init__(self):
    self.last_target = 0.0

  def _hysteresis(self, new_target: float) -> float:
    if new_target > self.last_target or new_target < self.last_target - HYSTERESIS_DOWN:
      self.last_target = new_target
    return self.last_target

  def update(self, v_ego: float, speeds, accels, throttle_allowed: bool, v_cruise: float,
             eco_level: int = 0, eco_ahead1_mph: float = 7, eco_ahead2_mph: float = 5, eco_rate: float = 0.0) -> float:
    """ACC set speed (m/s) that moves the stock ACC with openpilot's plan, capped by the driver's set speed."""
    if len(speeds):
      extend = min(max(_mean(accels) * 4, -EXTEND_FUTURE_MAX), EXTEND_FUTURE_MAX)
      target_future = _mean(speeds) + extend + KPH_TO_MS / 2
    else:
      target_future = 0.0

    if not throttle_allowed:  # coasting
      target_future = v_ego - COAST_OFFSET

    target = self._hysteresis(target_future)

    eco_limit = {1: eco_ahead1_mph, 2: eco_ahead2_mph}.get(eco_level)
    if eco_limit:
      # As in jvePilot: vEgo is in m/s here while the limit is in mph, so the rate is per m/s above 20 mph.
      diff = (v_ego - MPH_TO_MS * 20) * eco_rate
      if 0 < diff < eco_limit:
        eco_limit = max(2, eco_limit - diff)
      target = min(target, v_ego + eco_limit * MPH_TO_MS)

    return min(v_cruise, target)


def to_cluster_units(target_ms: float, is_metric: bool) -> int:
  """jvePilot floors the target in cluster units (the set speed only steps in whole units)."""
  return math.floor(target_ms * (3.6 if is_metric else 1 / MPH_TO_MS))
