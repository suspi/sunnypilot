# Plan: Glasses Mode and Head Pose Slack toggles for driver monitoring (suspi/sunnypilot)

## Context

The user's driver monitoring (DM) misreads them in two ways:
1. **Eyes.** With glasses on, the model loses or mistracks their eyes and reports false "eyes closed"
   distraction. Today blink is ignored only when the model is more than 90% sure the driver wears *sunglasses*
   (`openpilot/selfdrive/monitoring/policy.py:278-281`, `_SG_THRESHOLD = 0.9` at `:51`). Clear glasses are
   not covered.
2. **Head pose.** The device is mounted far to the side, so the head pose reads as turned away while the user
   looks at the road. Two limits cause false pose distraction:
   - The learned "natural" head offset is clipped to a narrow range: yaw `[-0.0246, 0.289]` rad and pitch
     `[-0.0881, 0.124]` rad (`policy.py:69-72`, applied at `:223-226`). An offset outside that range can never
     be learned away.
   - The distraction thresholds are pitch 0.3133 and yaw 0.4020 rad (`policy.py:55-60`).

The repo is `/workspace/repos/sunnypilot`, branch `suspi`, remote suspi/sunnypilot. That fork has no DM changes
of its own yet (the last commit on `policy.py` is the upstream sync `2149006ec`).

**Risk the user accepts by approving.** `policy.py:20-23` (comma's note to fork maintainers): "Disabling or
nerfing safety features will get you and your users banned from our servers." Both toggles loosen DM. Both
default **off**, so the stock behaviour is unchanged unless the user turns them on.

## Decisions

- **Two new bool params**, both `PERSISTENT | BACKUP` and default off, in `openpilot/common/params_keys.h`
  next to `AlwaysOnDM`:
  - `DMGlassesMode`
  - `DMHeadPoseSlack`
- **Glasses Mode** zeroes `blink.left` and `blink.right` in `_update_states`. This is the same path the
  sunglasses check already uses, so the `eye` distraction type can never fire. Head pose, phone and sleep
  detection keep working, so DM becomes "head direction only" for the eyes, as asked.
- **Head Pose Slack** adds fixed values to `DRIVER_MONITOR_SETTINGS`:
  - **Wider clip range for the learned offset**, so a side-mounted device's natural offset can be learned:
    yaw `[-0.35, 0.55]` and pitch `[-0.20, 0.25]` rad.
  - **Pose thresholds ×1.5**: yaw 0.402 → 0.603 rad (about 35°) and pitch 0.313 → 0.470 rad. The factor applies
    to the calibrated thresholds (`cfactor_*` scaling stays as is) and to the uncalibrated
    `_PITCH_NATURAL_THRESHOLD`.
  - It is one toggle with fixed amounts, as asked, not a slider. The user can change the numbers at approval.
- **Live reload.** `dmonitoringd.py` re-reads both params every 40 frames, the same way it handles `AlwaysOnDM`
  (`dmonitoringd.py:36-39`). The toggles therefore take effect without a reboot.
- **DriverMonitoring API.** It gets `glasses_mode` and `head_pose_slack` attributes, set from the params at init
  in `dmonitoringd.py` the same way `always_on` is passed. `policy.py` reads only those attributes, never
  Params, so the unit tests stay param-free.
- **UI.** Each toggle sits next to "Always-On Driver Monitoring":
  - tici (comma 3X): a `_toggle_defs` entry in `selfdrive/ui/layouts/settings/toggles.py` with the
    `monitoring.png` icon and no restart.
  - mici (comma four): a `BigParamControl` in `selfdrive/ui/mici/layouts/settings/toggles.py`, added to both
    the scroller and `_refresh_toggles`.

## Files

- `openpilot/common/params_keys.h`: the two keys.
- `openpilot/selfdrive/monitoring/policy.py`: the slack settings, the two attributes, and the blink and pose
  changes.
- `openpilot/selfdrive/monitoring/dmonitoringd.py`: pass the params at init and reload them live.
- `openpilot/selfdrive/monitoring/test_monitoring.py`: two tests, one per behaviour:
  - Glasses Mode with eyes "closed" raises no alert.
  - A yaw between the normal and the slack threshold is distracted without slack and not distracted with it.
- `openpilot/selfdrive/ui/layouts/settings/toggles.py` and `openpilot/selfdrive/ui/mici/layouts/settings/toggles.py`.
- `ARCHITECTURE.md`: one line under monitoring naming the two params.

## Out of scope

- The sunnylink remote-settings schema (`sunnypilot/sunnylink/settings_ui.json`).
- Translations.
- A tunable slack amount.
- Porting to suspipilot or to the Fmstrat build the 3X runs today.
- Checking whether the side mount also confuses the left/right wheel-side detection (`wheelOnRightProb`). That
  is an open question; a drive log with `driverMonitoringState.isRHD` would settle it.

## Steps (one commit each, pushed to `suspi`)

1. Params, policy, dmonitoringd and the two tests.
2. The tici and mici toggles, plus the ARCHITECTURE.md line.

**Subagents.** The change is small (about 60 lines), so I write the code myself. Venice GLM
(`/workspace/tools/ask-venice.sh`) drafts the two tests from the spec above, and `/venice-review` reviews the diff
before I call it done.

**Tool budget.** About 15 tool calls per step, 1 Venice draft plus at most 1 retry, and 1 review pass.

## Done when / verification

- `python3 -m py_compile` passes on every changed `.py` file. Daystrom has no `capnp` module
  (`ModuleNotFoundError` checked this session), so the tests cannot run here.
- `test_monitoring.py` passes on a machine with the openpilot environment. If this fork is not checked out on the
  3X, the result is reported as not run (UNVERIFIED), not claimed.
- With both toggles off, the code path is byte-for-byte the stock logic.
- Both toggles appear under Toggles on tici and mici. That needs the device UI, so it is checked on the car.
