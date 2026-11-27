"""
suspi: jvePilot settings as read by the openpilot side, refreshed about once a second (jvePilot used a 1 s cache).
"""
import time

from openpilot.common.params import Params

REFRESH_S = 1.0


_STEER_LOSS_CACHE = {"t": -REFRESH_S, "value": True}


def steer_loss_alert_enabled() -> bool:
  """jvePilot 'Audio alert on steering loss'. Default on, and on unless jvePilot features are on and it is off."""
  now = time.monotonic()
  if now - _STEER_LOSS_CACHE["t"] >= REFRESH_S:
    p = Params()
    _STEER_LOSS_CACHE["value"] = not p.get_bool("JvePilotEnabled") or p.get_bool("JvePilotSteerLossAlert")
    _STEER_LOSS_CACHE["t"] = now
  return _STEER_LOSS_CACHE["value"]


class JvePilotSettings:
  def __init__(self, brand: str):
    self.params = Params()
    self.chrysler = brand == "chrysler"
    self._last = -REFRESH_S
    self.refresh(force=True)

  def refresh(self, force: bool = False) -> None:
    now = time.monotonic()
    if not force and now - self._last < REFRESH_S:
      return
    self._last = now
    p = self.params
    self.enabled = self.chrysler and p.get_bool("JvePilotEnabled")
    self.plan_acc = self.enabled and p.get_bool("JvePilotPlanAcc")
    self.acc_eco = int(p.get("JvePilotAccEco", return_default=True) or 0)
    self.eco_ahead1 = float(p.get("JvePilotAccEcoSpeedAhead1", return_default=True))
    self.eco_ahead2 = float(p.get("JvePilotAccEcoSpeedAhead2", return_default=True))
    self.eco_rate = float(p.get("JvePilotAccEcoReductionRate", return_default=True))
    self.personality = self.enabled and p.get_bool("JvePilotPersonality")
    self.slow_in_curves = self.enabled and p.get_bool("JvePilotSlowInCurves")
    self.auto_follow = self.enabled and p.get_bool("JvePilotAutoFollow")
    self.auto_follow_crossovers = tuple(float(p.get(k, return_default=True)) for k in (
      "JvePilotAutoFollowSpeed12", "JvePilotAutoFollowSpeed23", "JvePilotAutoFollowSpeed34"))
    self.curve_ratio = float(p.get("JvePilotSlowInCurvesRatio", return_default=True))
    self.curve_drop_off = float(p.get("JvePilotSlowInCurvesDropOff", return_default=True))
    self.follow_relaxed = float(p.get("JvePilotFollowRelaxed", return_default=True))
    self.follow_standard = float(p.get("JvePilotFollowStandard", return_default=True))
    self.follow_aggressive = float(p.get("JvePilotFollowAggressive", return_default=True))
