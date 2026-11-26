"""
Copyright (c) 2021-, Haibin Wen, sunnypilot, and a number of other contributors.

This file is part of sunnypilot and is licensed under the MIT License.
See the LICENSE.md file in the root directory for more details.
"""
import os
import subprocess

from openpilot.selfdrive.ui.layouts.settings.software import SoftwareLayout
from openpilot.selfdrive.ui.ui_state import ui_state
from openpilot.common.hardware import HARDWARE
from openpilot.system.ui.lib.application import gui_app
from openpilot.system.ui.lib.multilang import tr, tr_noop
from openpilot.system.ui.widgets import DialogResult
from openpilot.system.ui.widgets.confirm_dialog import ConfirmDialog

from openpilot.system.ui.sunnypilot.widgets.list_view import button_item_sp, toggle_item_sp
from openpilot.system.ui.widgets.confirm_dialog import alert_dialog
from openpilot.system.ui.sunnypilot.widgets.tree_dialog import TreeOptionDialog, TreeNode, TreeFolder


DESCRIPTIONS = {
  'disable_updates_offroad': tr_noop(
    "When enabled, automatic software updates will be off.<br><b>This requires a reboot to take effect.</b>"
  ),
  'disable_updates_onroad': tr_noop(
    "Please enable \"Always Offroad\" mode or turn off the vehicle to adjust these toggles."
  )
}

# fork switcher (tools/fork_switch in suspi/suspipilot): builds installed side by side in /data/builds
FORK_SWITCH = "/data/fork-switch/fork_switch.py"
SWITCH_BUILDS = (("current", "current (Fmstrat)"), ("suspipilot", "suspipilot"), ("sunnypilot", "sunnypilot"))


def _switchable_builds():
  """Other installed builds; this one is whatever /data/openpilot points at."""
  self_dir = os.path.realpath("/data/openpilot")
  out = []
  for name, label in SWITCH_BUILDS:
    path = os.path.join("/data/builds", name)
    if os.path.isfile(os.path.join(path, "launch_openpilot.sh")) and os.path.realpath(path) != self_dir:
      out.append((name, label))
  return out


class SoftwareLayoutSP(SoftwareLayout):
  def __init__(self):
    super().__init__()
    self.disable_updates_toggle = toggle_item_sp(
      lambda: tr("Disable Updates"),
      description="",
      initial_state=ui_state.params.get_bool("DisableUpdates"),
      callback=self._on_disable_updates_toggled,
    )
    self._scroller.add_widget(self.disable_updates_toggle)

    self._switch_btns = []
    for name, label in _switchable_builds():
      btn = button_item_sp(tr("Set %s default") % label, lambda: tr("SWITCH"),
                           tr("Make %s the build that starts, then reboot. If it fails to start or crashes, "
                              "the device falls back to current by itself.") % label,
                           callback=lambda n=name, l=label: self._on_switch_build(n, l))
      self._switch_btns.append(btn)
      self._scroller.add_widget(btn)

  def _on_switch_build(self, name, label):
    if ui_state.engaged:
      gui_app.push_widget(alert_dialog(tr("Disengage to switch builds")))
      return

    def _confirmed(result):
      if result != DialogResult.CONFIRM or ui_state.engaged:
        return
      rc = subprocess.run(["python3", FORK_SWITCH, "set", name], check=False).returncode
      if rc != 0:
        gui_app.push_widget(alert_dialog(tr("Switch to %s failed (fork_switch.py exit %d)") % (label, rc)))
        return
      ui_state.params.put_bool("DoReboot", True)

    gui_app.push_widget(ConfirmDialog(tr("Set %s default and reboot?") % label, tr("Switch"), callback=_confirmed))

  def _handle_reboot(self, result):
    if result == DialogResult.CONFIRM:
      ui_state.params.put_bool("DisableUpdates", self.disable_updates_toggle.action_item.get_state())
      ui_state.params.put_bool("DoReboot", True)
    else:
      self.disable_updates_toggle.action_item.set_state(ui_state.params.get_bool("DisableUpdates"))

  def _on_disable_updates_toggled(self, enabled):
    dialog = ConfirmDialog(tr("System reboot required for changes to take effect. Reboot now?"), tr("Reboot"), callback=self._handle_reboot)
    gui_app.push_widget(dialog)

  def _on_select_branch(self):
    current_git_branch = ui_state.params.get("GitBranch") or ""
    branches_str = ui_state.params.get("UpdaterAvailableBranches") or ""
    branches = [b for b in branches_str.split(",") if b]
    current_target = ui_state.params.get("UpdaterTargetBranch") or ""
    top_level_branches = [current_git_branch, "release-mici", "release-tizi", "staging", "dev", "master"]

    if HARDWARE.get_device_type() == "tici":
      top_level_branches = ["release-tici", "staging-tici"]
      branches = [b for b in branches if b.endswith("-tici")]

    top_level_nodes = [TreeNode(b, {'display_name': b}) for b in top_level_branches if b in branches]
    remaining_branches = [b for b in branches if b not in top_level_branches]
    prebuilt_nodes = [TreeNode(b, {'display_name': b}) for b in remaining_branches if b.endswith("-prebuilt")]
    non_prebuilt_nodes = [TreeNode(b, {'display_name': b}) for b in remaining_branches if not b.endswith("-prebuilt")]

    folders = [
      TreeFolder("", top_level_nodes),
      TreeFolder("Prebuilt Branches", prebuilt_nodes),
      TreeFolder("Non-Prebuilt Branches", non_prebuilt_nodes),
    ]

    def _on_branch_selected(result):
      if result == DialogResult.CONFIRM and self._branch_dialog is not None:
        selection = self._branch_dialog.selection_ref
        if selection:
          ui_state.params.put("UpdaterTargetBranch", selection)
          self._branch_btn.action_item.set_value(selection)
          subprocess.run(["pkill", "-SIGUSR1", "-f", "openpilot.system.updated.updated"], check=False)
      self._branch_dialog = None

    self._branch_dialog = TreeOptionDialog(tr("Select a branch"), folders, current_target, "",
                                           on_exit=_on_branch_selected)

    gui_app.push_widget(self._branch_dialog)

  def _update_state(self):
    super()._update_state()
    show_advanced = ui_state.params.get_bool("ShowAdvancedControls")
    self.disable_updates_toggle.action_item.set_enabled(ui_state.is_offroad())
    for btn in self._switch_btns:
      btn.action_item.set_enabled(ui_state.is_offroad())
    self.disable_updates_toggle.set_visible(show_advanced)

    disable_updates_desc = tr(DESCRIPTIONS["disable_updates_offroad"] if ui_state.is_offroad() else DESCRIPTIONS["disable_updates_onroad"])
    self.disable_updates_toggle.set_description(disable_updates_desc)
