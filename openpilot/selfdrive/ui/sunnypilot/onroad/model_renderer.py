"""
Copyright (c) 2021-, Haibin Wen, sunnypilot, and a number of other contributors.

This file is part of sunnypilot and is licensed under the MIT License.
See the LICENSE.md file in the root directory for more details.
"""
import time

from openpilot.common.filter_simple import FirstOrderFilter
from openpilot.selfdrive.ui.ui_state import ui_state
from openpilot.selfdrive.ui.sunnypilot.onroad.blendful import BlendfulRenderer
from openpilot.selfdrive.ui.sunnypilot.onroad.chevron_metrics import ChevronMetrics
from openpilot.selfdrive.ui.sunnypilot.onroad.rainbow_path import RainbowPath
from openpilot.selfdrive.ui.sunnypilot.ui_state import UIStateSP
from openpilot.system.ui.lib.application import gui_app


class ModelRendererSP:
  def __init__(self):
    self.rainbow_path = RainbowPath()
    self.chevron_metrics = ChevronMetrics()
    self.blendful = BlendfulRenderer(readout=False)
    self._width_filter = FirstOrderFilter(0.9, 0.1, 1 / gui_app.target_fps)
    self._jve_highlight = False
    self._jve_highlight_checked = -1.0

  def _blindspot_lane_highlight(self) -> tuple[bool, bool]:
    """suspi: jvePilot 'Blindspot lane highlight' -> (left, right) lane line drawn red. Param read once a second."""
    now = time.monotonic()
    if now - self._jve_highlight_checked > 1.0:
      self._jve_highlight_checked = now
      p = ui_state.params
      chrysler = ui_state.CP is not None and ui_state.CP.brand == "chrysler"
      self._jve_highlight = chrysler and p.get_bool("JvePilotEnabled") and p.get_bool("JvePilotBlindspotHighlight")
    if not self._jve_highlight:
      return False, False
    cs = ui_state.sm['carState']
    return cs.leftBlindspot, cs.rightBlindspot

  @property
  def _lateral_active(self) -> bool:
    return UIStateSP.lateral_active(ui_state)

  def _get_path_half_width(self) -> float:
    target = 0.9 if self._lateral_active else 0.40
    return self._width_filter.update(target)
