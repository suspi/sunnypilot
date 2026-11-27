"""
suspi: jvePilot's Slow in Curves speed limit (jvePilot-beta 1508b2a, longitudinal_planner.py:216-226). Pure logic.
"""
import math


def limit_speed_in_curve(v_ego: float, curvature: float, ratio: float = 1.0, drop_off: float = 2.0) -> float:
  """Speed (m/s) for the curve the car is in now, from a lateral-acceleration limit that falls with speed."""
  a_y_max = 2.975 - v_ego * 0.0375  # ~1.85 @ 75mph, ~2.6 @ 25mph
  if a_y_max <= 0:
    return math.inf  # jvePilot took sqrt of a negative number here; above ~178 mph there is no limit to give
  if drop_off != 2:
    a_y_max = math.sqrt(a_y_max) ** drop_off
  return math.sqrt(a_y_max / max(abs(curvature), 1e-4)) * ratio
