"""
suspi: jvePilot's onroad ACC Eco button (tap cycles off/1/2) and Auto Follow indicator, from jvePilot-beta
selfdrive/ui/qt/onroad/buttons.cc, with jvePilot's own icons.
"""
import time

import pyray as rl

from openpilot.selfdrive.ui.ui_state import ui_state
from openpilot.system.ui.lib.application import gui_app

SIZE = 160
MARGIN = 30
ECO_ICONS = ("icons/jvepilot/img_acc_eco_off.png", "icons/jvepilot/img_acc_eco_1.png", "icons/jvepilot/img_acc_eco_2.png")
FOLLOW_ICONS = ("icons/jvepilot/auto_follow_off.png", "icons/jvepilot/auto_follow_on.png")


class JvePilotButtons:
  def __init__(self):
    self._enabled = False
    self._eco = 0
    self._checked = -1.0
    self.eco_rect = rl.Rectangle(0, 0, 0, 0)

  def _refresh(self) -> None:
    now = time.monotonic()
    if now - self._checked > 0.5:
      self._checked = now
      p = ui_state.params
      self._enabled = p.get_bool("JvePilotEnabled")
      self._eco = int(p.get("JvePilotAccEco", return_default=True) or 0)

  def render(self, rect: rl.Rectangle) -> None:
    self._refresh()
    if not self._enabled or not ui_state.started:
      self.eco_rect = rl.Rectangle(0, 0, 0, 0)
      return

    self.eco_rect = rl.Rectangle(rect.x + rect.width - SIZE - MARGIN, rect.y + rect.height - SIZE - MARGIN, SIZE, SIZE)
    eco_tex = gui_app.texture(ECO_ICONS[min(max(self._eco, 0), 2)], SIZE, SIZE)
    rl.draw_texture(eco_tex, int(self.eco_rect.x), int(self.eco_rect.y), rl.WHITE)

    auto_follow = ui_state.sm['carControlSP'].jvePilot.autoFollow
    follow_tex = gui_app.texture(FOLLOW_ICONS[1 if auto_follow else 0], SIZE, SIZE)
    rl.draw_texture(follow_tex, int(self.eco_rect.x - SIZE - MARGIN), int(self.eco_rect.y), rl.WHITE)

  def handle_press(self, mouse_pos) -> bool:
    """Cycle ACC Eco when the button is tapped; True if the tap was ours."""
    if self.eco_rect.width == 0 or not rl.check_collision_point_rec(mouse_pos, self.eco_rect):
      return False
    self._eco = (self._eco + 1) % 3
    ui_state.params.put("JvePilotAccEco", self._eco)
    return True
