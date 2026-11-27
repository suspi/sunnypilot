"""
Copyright (c) 2021-, Haibin Wen, sunnypilot, and a number of other contributors.

This file is part of sunnypilot and is licensed under the MIT License.
See the LICENSE.md file in the root directory for more details.
"""
from openpilot.selfdrive.ui.sunnypilot.layouts.settings.vehicle.brands.base import BrandSettings
from openpilot.sunnypilot.mads.helpers import MadsSteeringModeOnBrake
from openpilot.selfdrive.ui.ui_state import ui_state
from openpilot.system.ui.lib.multilang import tr
from openpilot.system.ui.sunnypilot.widgets.list_view import option_item_sp, toggle_item_sp

# suspi: turning jvePilot features on also sets up sunnypilot's own versions of jvePilot features it already has:
# MADS = Always-On Lateral (steer with ACC ready, keep steering through brake and gas), and ICBM, which carries the
# plan-following ACC set speed.
JVEPILOT_PRESET = {"Mads": True, "MadsMainCruiseAllowed": True, "IntelligentCruiseButtonManagement": True}
JVEPILOT_PRESET_INT = {"MadsSteeringMode": MadsSteeringModeOnBrake.REMAIN_ACTIVE}


def _float_label(scale=100.0, fmt="%.2f"):
  return lambda v: fmt % (v / scale)


class ChryslerSettings(BrandSettings):
  def __init__(self):
    super().__init__()
    self.master = toggle_item_sp(tr("jvePilot features"),
                                 tr("jvePilot's Chrysler features on top of sunnypilot. Turning it on also enables "
                                    "MADS (always-on steering, kept through brake and gas) and Intelligent Cruise "
                                    "Button Management; turning it off leaves those two as they are. Takes effect after "
                                    "a reboot."),
                                 param="JvePilotEnabled", callback=self._on_master)

    self.sub = [
      toggle_item_sp(tr("ACC follows openpilot"), tr("Move the ACC set speed with openpilot's plan: slow for lead "
                     "cars and curves, coast when it would lift off the throttle."), param="JvePilotPlanAcc"),
      option_item_sp(tr("ACC Eco level"), "JvePilotAccEco", 0, 2,
                     tr("0 = off. 1 and 2 limit how far ACC is set above your current speed (also set from the "
                        "onroad Eco button).")),
      option_item_sp(tr("Keep ahead at Eco 1 (mph)"), "JvePilotAccEcoSpeedAhead1", 1, 100, inline=True),
      option_item_sp(tr("Keep ahead at Eco 2 (mph)"), "JvePilotAccEcoSpeedAhead2", 1, 100, inline=True),
      option_item_sp(tr("Eco reduction per mph above 20"), "JvePilotAccEcoReductionRate", 0, 100, value_change_step=1,
                     use_float_scaling=True, label_callback=_float_label(), inline=True),
      toggle_item_sp(tr("Auto Follow"), tr("Set the ACC follow distance by speed. Start each drive with it on; "
                     "hold a distance button to toggle it."), param="JvePilotAutoFollow"),
      option_item_sp(tr("1 → 2 bars above (mph)"), "JvePilotAutoFollowSpeed12", 0, 300, inline=True),
      option_item_sp(tr("2 → 3 bars above (mph)"), "JvePilotAutoFollowSpeed23", 0, 300, inline=True),
      option_item_sp(tr("3 → 4 bars above (mph)"), "JvePilotAutoFollowSpeed34", 0, 300, inline=True),
      toggle_item_sp(tr("Personality from ACC bars and Eco"), tr("Drive personality follows the ACC distance bars and "
                     "Eco level, with the follow times below."), param="JvePilotPersonality"),
      option_item_sp(tr("Relaxed follow time (s)"), "JvePilotFollowRelaxed", 100, 200, value_change_step=5,
                     use_float_scaling=True, label_callback=_float_label(), inline=True),
      option_item_sp(tr("Standard follow time (s)"), "JvePilotFollowStandard", 100, 200, value_change_step=5,
                     use_float_scaling=True, label_callback=_float_label(), inline=True),
      option_item_sp(tr("Aggressive follow time (s)"), "JvePilotFollowAggressive", 100, 200, value_change_step=5,
                     use_float_scaling=True, label_callback=_float_label(), inline=True),
      toggle_item_sp(tr("ACC Ready on Start"), tr("Press ACC On/Off for you when the car starts. Takes effect after a "
                     "reboot."), param="JvePilotAccReadyOnStart"),
      toggle_item_sp(tr("Slow in Curves"), tr("Slow for the curve you are in, scaled by the values below."),
                     param="JvePilotSlowInCurves"),
      option_item_sp(tr("Curve speed ratio"), "JvePilotSlowInCurvesRatio", 10, 200, value_change_step=5,
                     use_float_scaling=True, label_callback=_float_label(), inline=True),
      option_item_sp(tr("Curve speed drop-off"), "JvePilotSlowInCurvesDropOff", 100, 300, value_change_step=10,
                     use_float_scaling=True, label_callback=_float_label(), inline=True),
      toggle_item_sp(tr("Audio alert on steering loss"), tr("Chime when speed drops below the steering minimum."),
                     param="JvePilotSteerLossAlert"),
      toggle_item_sp(tr("Blindspot lane highlight"), tr("Draw the lane line red while a car is in that blind spot."),
                     param="JvePilotBlindspotHighlight"),
      toggle_item_sp(tr("ADVANCED: WP speed-spoof signal"), tr("Tell a jvePilot-firmware white panda when to spoof "
                     "speed (only while steering). Takes effect after a reboot."), param="JvePilotWpSignal"),
      toggle_item_sp(tr("ADVANCED: PID steering"), tr("Use the PID controller instead of torque. Takes effect after a "
                     "reboot."), param="JvePilotPidSteering"),
      toggle_item_sp(tr("ADVANCED: Vision only"), tr("Ignore the radar for the lead car. Takes effect after a reboot."),
                     param="JvePilotVisionOnly"),
      toggle_item_sp(tr("ADVANCED: Reverse radar X axis"), tr("For a lead marker that is mirrored. Takes effect after "
                     "a reboot."), param="JvePilotReverseRadar"),
    ]
    self.items = [self.master] + self.sub

  @staticmethod
  def _on_master(enabled):
    if enabled:
      for key, value in JVEPILOT_PRESET.items():
        ui_state.params.put_bool(key, value)
      for key, value in JVEPILOT_PRESET_INT.items():
        ui_state.params.put(key, value)

  def update_settings(self):
    enabled = ui_state.params.get_bool("JvePilotEnabled")
    offroad = ui_state.is_offroad()
    self.master.action_item.set_enabled(offroad)
    for item in self.sub:
      item.set_visible(enabled)
      item.action_item.set_enabled(offroad)
