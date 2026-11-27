# jvePilot features (suspi build)

This build of sunnypilot carries jvePilot's Chrysler features behind one switch:
**Vehicle → Chrysler → jvePilot features**. With the switch off, the build is plain sunnypilot. The switch only
works on Chrysler/FCA cars and is settable only offroad.

Turning it on also sets sunnypilot's own versions of jvePilot features that sunnypilot already has:
- MADS on, with Main Cruise Allowed and Steering Mode on Brake = Remain Active. This is jvePilot's always-on
  lateral: the van keeps steering while you use the gas or brake.
- Intelligent Cruise Button Management on. It carries the plan-following set speed below.

Reboot after changing anything marked "after a reboot".

| Setting (param) | What it does | Default |
|---|---|---|
| ACC follows openpilot (`JvePilotPlanAcc`) | ACC set speed tracks openpilot's plan (mean planned speed plus an acceleration look-ahead); coasts at your speed − 4 mph when the model would lift off the throttle; never above your set speed or the curve and speed-limit caps | on |
| ACC Eco level, keep-ahead 1/2, reduction (`JvePilotAccEco*`) | Limits how far ACC is set above your speed; also cycled by the onroad Eco button | 1; 7 / 5 mph; 0.08 |
| Auto Follow, 1→2 / 2→3 / 3→4 bars (`JvePilotAutoFollow*`) | Sets the ACC distance bars by speed. Hold a distance button 0.5 s to turn it on; a short press turns it off. Starts each drive on | on; 15 / 30 / 65 mph |
| Personality from ACC bars and Eco, follow times (`JvePilotPersonality`, `JvePilotFollow*`) | openpilot's lead following uses jvePilot's bars × Eco table and these follow times | on; 1.6 / 1.2 / 1.0 s |
| ACC Ready on Start (`JvePilotAccReadyOnStart`) | Presses ACC On/Off in the first 5 s of a drive, after a reboot | on |
| Slow in Curves, ratio, drop-off (`JvePilotSlowInCurves*`) | Speed for the curve you are in, from a lateral-acceleration limit that falls with speed; off in experimental mode | on; 1.00; 2.00 |
| Audio alert on steering loss (`JvePilotSteerLossAlert`) | Chime when speed drops below the steering minimum | on |
| Blindspot lane highlight (`JvePilotBlindspotHighlight`) | Lane line drawn red while a car is in that blind spot | on |
| WP speed-spoof signal (`JvePilotWpSignal`) | With a white panda detected: tells jvePilot-wp-mod firmware to spoof only while openpilot steers, after a reboot | on |
| PID steering (`JvePilotPidSteering`) | jvePilot's PID gains on Chrysler platforms that default to torque. The Pacifica 2018-2020 already uses them | off |
| Vision only / Reverse radar X axis (`JvePilotVisionOnly`, `JvePilotReverseRadar`) | Ignore the radar, or mirror its lateral position, after a reboot | off |

## Panda safety

Auto Follow and ACC Ready on Start press buttons that sunnypilot's Chrysler safety mode refuses. When either is on,
the car init sets SP safety param bit `JVEPILOT_BUTTONS`, which allows:
- one distance button (optionally with one of accel or decel) while engaged;
- ACC On/Off alone at any time.

Nothing else changes, and without the bit the safety check is sunnypilot's
(`opendbc_repo/opendbc/safety/modes/chrysler.h`; tests in `opendbc/safety/tests/test_chrysler.py`).

## Not included

- jvePilot's Jeep-only Brake Hold and experimental Jeep openpilot longitudinal control.
- jvePilot's own versions of features sunnypilot has. Use these instead: camera offset (Device Offset), the Vehicle
  Selector (Selected Car), custom ACC increments (Reverse ACC ±), and the MADS LKAS-button toggle.

Ported from jvePilot-beta (suspi/jvearchive `jvePilot-beta`). The code is in
`openpilot/sunnypilot/selfdrive/*/jvepilot_*.py`, `opendbc_repo/opendbc/sunnypilot/car/chrysler/`, and the Chrysler
brand settings page. Plan: `docs/plans/2026-11-26_1529_plan-jvepilot-features-in-suspi-sunnypilot-behind-one-featur.md`.
