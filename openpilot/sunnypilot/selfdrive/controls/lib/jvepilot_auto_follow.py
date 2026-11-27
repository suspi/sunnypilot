"""
suspi: jvePilot's Auto Follow, which sets the ACC follow distance (bars) by speed.

Ported from jvePilot-beta 1508b2a, opendbc/car/chrysler/carcontroller.py:92-104 (toggle) and 267-292
(auto_follow_button). Runs on the openpilot side at 100 Hz; the car code presses the distance buttons. Pure logic.
"""
MPH_TO_MS = 0.44704
LOCK_MARGIN = 3 * MPH_TO_MS  # once a bar count is chosen, keep it until speed is this far from its crossover
LONG_PRESS_FRAMES = 50       # 0.5 s at 100 Hz, as jvePilot's pressedFrames


class AutoFollow:
  def __init__(self, start_enabled: bool):
    self.enabled = start_enabled
    self.lock = None
    self.press_frames = 0
    self.long_press_handled = False

  def _buttons(self, pressed: bool) -> None:
    """A short press of a distance button turns Auto Follow off (the driver takes over); a long press turns it on."""
    if pressed:
      self.press_frames += 1
      if not self.enabled and self.press_frames >= LONG_PRESS_FRAMES and not self.long_press_handled:
        self.enabled = True
        self.long_press_handled = True
    else:
      if self.enabled and 0 < self.press_frames < LONG_PRESS_FRAMES:
        self.enabled = False
      self.press_frames = 0
      self.long_press_handled = False

  def update(self, v_ego: float, current_bars: int, distance_button_pressed: bool, crossovers_mph) -> int:
    """Desired bar count 0-3, or -1 for no request."""
    self._buttons(distance_button_pressed)
    if not self.enabled:
      self.lock = None
      return -1

    crossover = [0.0] + [c * MPH_TO_MS for c in crossovers_mph]  # speeds where 1->2, 2->3 and 3->4 bars start
    if v_ego < crossover[1]:
      target = 0
    elif v_ego < crossover[2]:
      target = 1
    elif v_ego < crossover[3]:
      target = 2
    else:
      target = 3

    if self.lock is not None and abs(crossover[self.lock] - v_ego) > LOCK_MARGIN:
      self.lock = None

    # As in jvePilot: `(lock or target) == target`, so a lock of 0 behaves like no lock.
    if current_bars != target and (self.lock or target) == target:
      self.lock = target
      return target
    return -1
