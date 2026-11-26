# Plan: jvePilot features in suspi/sunnypilot, behind one feature flag

## Context

The user's van is a 2020 Pacifica Hybrid Limited with a comma 3X. jvePilot (retired 2025-09) has features the user
relies on that sunnypilot lacks: ACC that follows openpilot's plan, Auto Follow, ACC on at startup, and more (research:
suspipilot `docs/research/2026-11-26_1352_jvepilot-vs-sunnypilot-fca.md`).

The user's sunnypilot build (`suspi/sunnypilot`, branch `suspi`, from the 3X fork-switch plan) should gain all of them
behind a **"jvePilot features" master toggle**, with jvePilot's own per-feature settings under it. Master off means
plain sunnypilot.

The user decided:
- **Jeep-only features are left out.** Brake Hold and Jeep openpilot longitudinal control (forged DAS_3 brake and
  torque) go to AGENTS.md Next actions.
- **Where sunnypilot already has the feature, the flag configures sunnypilot's version** rather than porting
  jvePilot's.

Reference code: jvePilot as vendored in `/workspace/repos/suspipilot` (jvePilot-beta 1508b2a). Target:
`/workspace/repos/sunnypilot` (fork of sunnypilot master 6732fcc, opendbc b928e4a).

## What gets ported, and how (all Chrysler-only, all gated by the master flag)

| jvePilot feature | jvePilot source | Port into sunnypilot |
|---|---|---|
| ACC set speed follows openpilot's plan, coasting at vEgo − 4 mph when throttle is not allowed, ratchet hysteresis | `carcontroller.py:231-265,294-300` `hybrid_acc_button` | A new ICBM target mode. `IntelligentCruiseButtonManagement.update_calculations` (`openpilot/sunnypilot/selfdrive/car/intelligent_cruise_button_management/controller.py`) takes its target from `longitudinalPlan` (speeds, accels, allowThrottle or its 0.11 equivalent) instead of `LongitudinalPlanSP.vTarget`. The planner already publishes the plan without openpilot long (`selfdrive/controls/lib/longitudinal_planner.py:84-88`). The button sending in `opendbc/sunnypilot/car/chrysler/icbm.py` is reused unchanged. |
| ACC Eco 0/1/2 (keep-ahead mph, reduction rate) and its onroad button | `carcontroller.py:233-256`, `selfdrive/ui/qt/onroad/buttons.cc:62-86` | Caps inside the same ICBM target. A Raylib onroad button cycles the level, with jvePilot's PNG assets. |
| Personality from ACC distance bars and Eco (`DRIVE_PERSONALITY`), custom follow times (relaxed 1.8, standard 1.4, aggressive 1.0 s) | `carcontroller.py:145-152`, `values.py:139-143`, `long_mpc.py:78-82` | The openpilot side writes `LongitudinalPersonality` from carstate bars and Eco. MPC `get_T_FOLLOW` uses the custom times when the flag is on. |
| **Auto Follow**: distance bars by speed bands (15/30/65 mph); a long press on a distance button toggles it; "start with Auto Follow enabled" | `carcontroller.py:92-104,267-292` | The decision is made on the openpilot side (a new module next to ICBM). It sends a desired bar count in a new `CarControlSP` field. carstate reports the current bars (DAS_4 `ACC_DISTANCE_CONFIG_2`) in `CarStateSP`. opendbc's Chrysler `carcontroller_ext` presses `ACC_Distance_Inc`/`Dec` with the ICBM counter pattern. Onroad Auto Follow indicator. |
| **ACC Ready on Start**: press ACC_OnOff in the first 500 frames | `carcontroller.py:219-224` | A `ChryslerFlagsSP` bit set from the param at car init. `carcontroller_ext` presses `ACC_OnOff`. |
| Slow in Curves (speed ratio, drop-off) | `longitudinal_planner.py:184-226` | A new source in `LongitudinalPlannerSP.update_targets` (`openpilot/sunnypilot/selfdrive/controls/lib/longitudinal_planner.py:60-66`), so ICBM and the plan both see it. |
| WP speed-spoof signal (`WP_CONTROL`, `WP_ACTIVE` in LKAS_COMMAND) | `chryslercan.py:58-67`, DBC lines 241-242 | Add the two signals to the generator DBC (`opendbc/dbc/generator/chrysler/chrysler_pacifica_2017_hybrid.dbc`). `create_lkas_command` sets them when a `ChryslerFlagsSP` bit is on. The existing `NO_MIN_STEERING_SPEED` detection (0x4FF) stays. |
| PID steering, Vision only, Reverse radar X axis | `interface.py`, `radar_interface.py:46-49` | PID: a `CarParams` lateral-tuning override where sunnypilot applies param-driven CP changes (`openpilot/sunnypilot/selfdrive/car/interfaces.py`). Radar: `CP_SP` flags read in opendbc `radar_interface.py`. |
| Audio alert on steering loss (engaged, below min steer speed) | `selfdrive/selfdrived/events.py:245` | A sunnypilot event, played when the toggle is on. |
| Blindspot lane highlight (adjacent lane line drawn red) | `selfdrive/ui/qt/onroad/model.cc:16-100` | A Raylib model-renderer option next to `blind_spot_indicators.py`. |
| Always-On Lateral, LKAS-button toggle, Device Offset, Selected Car, Reverse ACC ± | various | **Not ported.** Turning the master flag on sets MADS on, Main Cruise Allowed and Steering Mode on Brake = Remain Active. The settings page points to sunnypilot's camera offset, Vehicle Selector and custom ACC increments. |

## Decisions

- **Params.** One master param, `JvePilotEnabled`, plus jvePilot's settings under new names: `JvePilot<Feature>` /
  `JvePilot<Feature><Setting>`, with jvePilot's defaults. They are registered in `openpilot/common/params_keys.h`.
  The UI is a new "jvePilot" panel in `openpilot/selfdrive/ui/sunnypilot/layouts/settings/`, in the style of
  `steering.py` and `cruise.py`. Settings that change car init (safety, flags, PID) are offroad-only, say "takes
  effect after reboot", and are read once at car init.
- **Data path.**
  - The openpilot side decides: selfdrived/controlsd extensions read the params and the plan.
  - opendbc only acts: it sees `CarParamsSP` flags at init and `CarControlSP` fields each frame, as ICBM and MADS
    already do.
  - New `custom.capnp` fields (in sunnypilot's cereal) for desired bars, current bars, and the Eco and Auto Follow
    states.
- **Panda safety** (`opendbc/safety/modes/chrysler.h:160-170`). A new SP safety-param bit, set only when the flag
  and the feature are on, allows:
  - `ACC_Distance_Dec` (byte 0, 0x02) and `ACC_Distance_Inc` (byte 1, bit 0) while `controls_allowed`;
  - `ACC_OnOff` (0x80) while not.
  Everything else stays as sunnypilot has it. With the flag off, safety is byte-for-byte unchanged.
- **New `suspi/opendbc` fork** of `sunnypilot/opendbc`, branch `suspi`. The `opendbc_repo` submodule in
  `suspi/sunnypilot` points at it. The earlier plan put this fork out of scope; car-code changes now need it.
- **No Jeep-only code.** jvePilot's `long_carcontroller*.py`, brake hold and DAS_3 forging are not ported.
- **Subagents.** Venice GLM through `/workspace/tools/ask-venice.sh` drafts each step's code and tests from a written
  spec that includes the jvePilot source excerpt and the sunnypilot target file. I review, fit, test and commit.
  9router is used if a draft is wrong twice. `/venice-review` runs at the end.

## Steps (one commit each; tool budget about 15 calls per step; Venice drafts steps 2-9)

1. **Fork and plumbing.**
   - Fork `suspi/opendbc` and repoint the submodule.
   - Add the params, the cereal fields and the master flag.
   - Add the jvePilot settings panel (toggles and values only, no behaviour yet).
   - Turning the master flag on applies the MADS preset.
2. **Plan-following ACC, coasting and ACC Eco**, as an ICBM target mode, with pure-logic unit tests (Eco caps,
   hysteresis, coast target, the 20 mph minimum).
3. **Personality mapping and custom follow times.**
4. **Slow in Curves** as a planner source, with unit tests on `limit_speed_in_curv`.
5. **Auto Follow:** carstate bars, the decision module (unit tests on bands, lock hysteresis and the long-press
   toggle), the opendbc button presses, and the safety allowance plus opendbc safety tests.
6. **ACC Ready on Start:** the flag bit, the button press and the safety allowance, plus safety tests.
7. **WP signal bits:** DBC and `create_lkas_command`.
8. **PID steering, vision-only and reverse-radar options.**
9. **UI and alerts:** audio alert on steering loss, blindspot lane highlight, onroad ACC Eco button and Auto Follow
   indicator.
10. **Docs:** AGENTS.md in suspipilot (Current focus, Next actions: Brake Hold and Jeep long left out), and a feature
    list in `suspi/sunnypilot` `docs/`.

## Out of scope

- Brake Hold and Jeep openpilot long.
- jvePilot's versions of features sunnypilot already has (see the table).
- Non-Chrysler cars.
- Device install, which is the fork-switch plan's steps 5-7.

## Verification

- **On Daystrom:** the pure-logic unit tests for each feature run with `python3 -m unittest -v`. The logic is kept
  in modules importable without cereal, raylib or compiled opendbc. Everything else is py_compiled.
- **On the 3X** (after the fork-switch install), the first full build:
  - `scons` must succeed;
  - opendbc's own Chrysler safety tests (`opendbc/safety/tests/test_chrysler.py`) must pass. That needs the device
    toolchain; Daystrom has no C compiler.
- **Drive checks**, with the flag on, each read from the UI and `qlog`:
  - the ACC set speed drops behind a slower lead car and when coasting;
  - the distance bars change at 15/30/65 mph with Auto Follow on;
  - ACC is ready at startup;
  - the Slow in Curves target appears in curves;
  - flag off behaves as plain sunnypilot.
- **End:** `/venice-review` over both forks' diffs, and a read of the diff against this plan.
