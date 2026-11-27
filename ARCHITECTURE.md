# Architecture map (suspi fork of sunnypilot)

A jump table for agents: what is responsible for what, and where it lives. Read this before walking the tree.
Mapped at `0af197fe3` (branch `suspi`) on 2026-11-26. Line numbers drift; grep the names given here.

## 0. Orientation in 60 seconds

- **The code lives under `openpilot/`, not at the repo root.** Imports are `openpilot.<pkg>...`. The root holds build,
  packaging, launch scripts and submodules. Upstream moved everything there in comma's `5edc0bd89`
  ("mv root dirs into nested openpilot"). The root `system/` holds only `system/hardware/tici/agnos.json`, a compat
  symlink for old releases.
- **Three layers:**
  1. Upstream openpilot: `openpilot/{selfdrive,system,common,cereal,tools}`.
  2. The sunnypilot add-on layer: `openpilot/sunnypilot/`, plus SP UI in `openpilot/selfdrive/ui/sunnypilot/` and
     `openpilot/system/ui/sunnypilot/`.
  3. Car code in the `opendbc_repo` submodule, with its own `opendbc/sunnypilot/` layer.
- **How sunnypilot hooks in:**
  - The upstream class inherits an SP mixin, named `*SP` or `*Ext`. Example: `class Controls(ControlsExt)` in
    `selfdrive/controls/controlsd.py:34`. The full table is in §5.
  - SP messages are separate `*SP` topics, with structs in `openpilot/cereal/custom.capnp`.
  - SP params sit in the shared `openpilot/common/params_keys.h`.
- **Topic names are the renamed ones** (upstream `6d5d1f691` "Rename live cereal services"). Grep for these, not the
  old names:

  | new name | old name |
  |---|---|
  | `deviceMotion` | livePose |
  | `vehicleParameters` | liveParameters |
  | `lateralTorqueParameters` | liveTorqueParameters |
  | `lateralDelay` | liveDelay |
  | `extrinsicsCalibration` | liveCalibration |
  | `narrowRoadCameraState` | roadCameraState |
  | `cabinCameraState` | driverCameraState |

- **The UI is pure Python raylib** (pyray). There is no Qt. The only C++ under `selfdrive/ui` is
  `installer/installer.cc`.
- **Tests are unittest-based, not pytest.** Run them with `tools/op.sh test <path>`, which is `tools/test_runner.py`.
- **There is no lateral planner.** Lateral control follows `modelV2.action.desiredCurvature`.

## 1. Repo layout and submodules

| path | what |
|---|---|
| `openpilot/cereal/` | message schemas (`log.capnp`, `custom.capnp`), `services.py` (topic → rate), `messaging/` (SubMaster/PubMaster, `bridge.cc`). This is a plain dir, not a submodule. |
| `openpilot/common/` | params, hardware abstraction, realtime, swaglog, filters/PID, transformations |
| `openpilot/selfdrive/` | driving daemons (car, controls, selfdrived, modeld, locationd, monitoring, pandad, navigation), UI, assets, tests |
| `openpilot/sunnypilot/` | sunnypilot features (§4) |
| `openpilot/system/` | manager, hardware daemon, loggerd, camerad, sensord, athena, updated, webrtc, GNSS, UI toolkit |
| `openpilot/tools/` | dev tools: replay, cabana, jotpluggler, plotjuggler, sim, joystick, `lib/logreader.py` |
| `openpilot/third_party/` | vendored binaries (mapd, copyparty) |
| `tools/` (root) | `op.sh` dev CLI, `test_runner.py`, `setup*.sh`, `car_porting/`, `release/` (release-branch builders) |
| `scripts/` | `lint/lint.sh` (ruff + ty + codespell + checks), `apply-pr.sh`, `checkout-pr.sh` |
| `release/ci/` | SP CI helpers: `publish.sh` (version), `squash_and_merge*.py` (master-dev), model generators |
| `docs/` | upstream docs (`contributing/architecture.md`, `how-to/`, `concepts/`); fork plans in `docs/plans/` |

Submodules (`.gitmodules`):

| path | source | checked out in this clone? |
|---|---|---|
| `opendbc_repo` | **suspi/opendbc** branch `suspi` (fork change; upstream uses sunnypilot/opendbc) | **yes**, at `f8f77e5` |
| `panda` | sunnyhaibin/panda: panda firmware + `pandacan` | no |
| `msgq_repo` | sunnypilot/msgq: IPC, VisionIPC | no |
| `rednose_repo` | commaai/rednose: Kalman filters (locationd) | no |
| `teleoprtc_repo` | commaai/teleoprtc: WebRTC | no |
| `tinygrad_repo` | sunnypilot/tinygrad: model runtime | no |
| `openpilot/sunnypilot/neural_network_data` | sunnypilot/neural-network-data: NNLC per-car models | no |

## 2. Processes (`openpilot/system/manager/process_config.py`)

- **How the manager decides what runs:**
  - `manager.py: manager_thread` calls `ensure_running` on every `deviceState`.
  - `started` (onroad) comes from `hardwared`.
  - Each process has a predicate `(started, params, CP)`, built with `only_onroad`, `only_offroad`, `always_run`,
    `and_` and `or_`.
- **Process kinds:** `PythonProcess` (a module), `NativeProcess` (a dir + argv), `DaemonProcess`. They are defined in
  `manager/process.py`.

| when | processes (module under `openpilot.`) |
|---|---|
| **onroad: the driving loop** | `card` (selfdrive.car.card), `selfdrived`, `controlsd` (not in joystick mode), `plannerd` (not in LongitudinalManeuverMode), `radard`, `locationd`, `calibrationd`, `paramsd`, `torqued`, `lagd` (all selfdrive.locationd.*), `dmonitoringd` + `dmonitoringmodeld` (driverview) |
| **onroad: driving model (one of the two)** | `modeld` (selfdrive.modeld.modeld) when `is_stock_model`; `modeld_tinygrad` (native `openpilot/sunnypilot/modeld_v2 ./modeld`) when `is_tinygrad_model`. The active runner comes from `sunnypilot/models/helpers.py: get_active_model_runner`. |
| onroad: sensors and logging | `camerad`, `sensord`, `loggerd`, `encoderd`, `micd`, `proclogd`, `journald`, `qcomgpsd` or `ubloxd` + `pigeond`, `gps_fuser` (SP), `navd` + `mapsd` (if NavigationEnabled) |
| always | `pandad` (flashes the panda, then Popens native `./pandad`), `hardwared`, `ui`, `logmessaged`, `deleter`, `timed`, `tombstoned`, `modem`, `statsd` (SP), `mapd_manager` (SP), `mapd` (SP, external Go binary, if installed) |
| offroad | `updated`, `uploader` (also onroad if OnroadUploads), `models_manager` (SP), `modeld_warmup` (SP), `backup_manager` (SP, sunnylink ready) |
| conditional | `stream_encoderd` + `webrtcd` (livestream), `joystickd` / `joystick`, `maneuversd` / `lateral_maneuversd`, `sunnylink_registration_manager`, `statsd_sp`, `sunnylink_uploader`, `copyparty-sfx` (EnableCopyparty), `bridge` (notCar) |
| **disabled in this fork** | `manage_athenad` and `manage_sunnylinkd` are commented out ("Off on suspi builds", lines ~113 and ~169), so remote access is off |

## 3. The control loop, end to end

1. **CAN in.**
   - `selfdrive/pandad/pandad.cc: pandad_run → can_recv` reads the panda and publishes `can` (100 Hz).
   - `panda_safety.cc: setSafetyMode` waits for param `ControlsReady`, then sets the safety mode from
     CarParams/CarParamsSP.
2. **Car state.** `selfdrive/car/card.py: Car.step → state_update`:
   - `can_capnp_to_list` converts the frames, then `CI.update(can_list)` runs the opendbc `CarInterface`/CarState and
     returns `(CS, CS_SP)`.
   - `RI.update` handles radar.
   - `VCruiseHelper.update_v_cruise` (`car/cruise.py`) sets the set speed.
   - It publishes `carState`, `carStateSP`, `carOutput`, `radarTracks` and `carParams(SP)`.
   - On startup `get_car` fingerprints the car, then `sunnypilot/selfdrive/car/interfaces.py: setup_interfaces` runs.
3. **Perception (20 Hz, in parallel).**
   - modeld turns camera VisionIPC into `modelV2`, `cameraOdometry` and `modelDataV2SP`; `DesireHelper` handles lane
     changes.
   - `locationd` publishes `deviceMotion`. `calibrationd`, `paramsd`, `torqued` and `lagd` publish the learned
     parameters.
   - `radard` (`RadarD`) fuses `radarTracks` and `modelV2` into `radarState`.
4. **Engagement (100 Hz).** `selfdrive/selfdrived/selfdrived.py: SelfdriveD.step`:
   - `update_events` collects `CarEvents`, `CarSpecificEventsSP`, the longitudinalPlanSP events, `mads.update_events`
     and `icbm.run`.
   - `state.py: StateMachine.update` (disabled / preEnabled / enabled / softDisabling / overriding) and `mads.update`
     update the state.
   - `AlertManager` turns the events into alerts.
   - It publishes `selfdriveState(SP)` and `onroadEvents(SP)`.
5. **Planning (20 Hz on modelV2).** `selfdrive/controls/plannerd.py` calls
   `lib/longitudinal_planner.py: LongitudinalPlanner.update`:
   - `LongitudinalPlannerSP.update_targets` applies the SCC-vision, SCC-map and SLA caps.
   - `LongitudinalMpc.update` solves the MPC.
   - The accel target is the min of the MPC result and `modelV2.action.desiredAcceleration`.
   - It publishes `longitudinalPlan` and `longitudinalPlanSP`. `ldw.py` publishes `driverAssistance`.
6. **Control (100 Hz).** `selfdrive/controls/controlsd.py: Controls.run → update → state_control`:
   - `ControlsExt.get_lat_active` (MADS) decides whether lateral is active.
   - `LongControl.update` produces the accel command.
   - `clip_curvature`, then `LaC.update`, produce the lateral command. `LaC` is LatControlTorque, PID, Angle or
     Curvature, or the SP torque v0 / NNLC swapped in by `ControlsExt.initialize_lateral_control`.
   - It publishes `carControl` and `controlsState`; `run_ext` publishes `carControlSP`.
7. **CAN out.** `card.py: Car.controls_update`:
   - On the first pass it runs `CI.init` and sets `ControlsReady`.
   - `CI.apply(CC, CC_SP)` runs the opendbc CarController, and card publishes the result as `sendcan`.
   - `pandad.cc: can_send_thread` sends it to the panda. The panda heartbeat carries the engaged state and the MADS
     state (`process_mads_heartbeat`).

Topic rates are in `openpilot/cereal/services.py` (`_services`: name → (log, Hz, decimation)). The SP topics are at
lines ~87-98.

## 4. Directory map

### Upstream driving daemons (`openpilot/selfdrive/`)

| path | responsibility | key files |
|---|---|---|
| `pandad/` | USB/SPI link to the panda; flashing; safety mode | `pandad.py` (flash + launch), `pandad.cc`, `panda_safety.cc`, `pandad_api_impl.py` |
| `car/` | car interface process | `card.py: Car`, `cruise.py: VCruiseHelper`, `car_events.py: CarEvents`, `helpers.py` (struct ↔ capnp conversion, incl. `CarControlSP.JvePilot`) |
| `selfdrived/` | engagement state machine, events, alerts | `selfdrived.py: SelfdriveD`, `state.py`, `events.py: EVENTS`, `alertmanager.py`, `alerts_offroad.json` |
| `controls/` | planning + actuation | `controlsd.py`, `plannerd.py`, `radard.py`; `lib/`: `longitudinal_planner.py`, `longitudinal_mpc_lib/long_mpc.py`, `longcontrol.py`, `latcontrol_{pid,angle,curvature,torque}.py`, `drive_helpers.py`, `desire_helper.py`, `ldw.py` |
| `modeld/` | stock driving model + driver-monitoring model | `modeld.py: ModelState`, `fill_model_msg.py`, `parse_model_outputs.py`, `dmonitoringmodeld.py` |
| `locationd/` | localization + online learners (see below) | `locationd.py`, `calibrationd.py`, `paramsd.py`, `torqued.py`, `lagd.py` |
| `monitoring/` | driver attention policy; fork toggles `DMGlassesMode` (ignore blink) and `DMHeadPoseSlack` (wider pose offset clip, thresholds x1.5) | `dmonitoringd.py`, `policy.py: DriverMonitoring` |
| `navigation/` | routing + map tiles | `navd.py: RouteEngine` (navInstruction/navRoute), `mapsd.py` (VisionIPC map stream) |
| `ui/` | on-device UI (§4 UI) | `ui.py`, `ui_state.py`, `soundd.py`, `layouts/`, `onroad/`, `mici/`, `sunnypilot/`, `translations/` |
| `test/` | process replay, onroad tests | `process_replay/{test_processes.py,model_replay.py,process_replay.py}`, `test_onroad.py` |

The locationd learners:

| file | publishes | subscribes |
|---|---|---|
| `locationd.py: LocationEstimator` | deviceMotion | carState, extrinsicsCalibration, cameraOdometry, IMU |
| `calibrationd.py: Calibrator` | extrinsicsCalibration | cameraOdometry, carState |
| `paramsd.py: VehicleParamsLearner` | vehicleParameters | deviceMotion, extrinsicsCalibration, carState |
| `torqued.py: TorqueEstimator` (+ SP `TorqueEstimatorExt`) | lateralTorqueParameters | carControl, carOutput, carState, deviceMotion, lateralDelay |
| `lagd.py: LateralLagEstimator` (+ SP `LagdToggle`) | lateralDelay | deviceMotion, carState, controlsState, carControl |

### Message schemas (`openpilot/cereal/`)

- **`log.capnp`:**
  - `OnroadEvent.EventName` is at ~line 20. The `Event` union is at ~2528, and its SP slots are at ~2630-2660.
  - Main structs: SelfdriveState, ControlsState, ModelDataV2, LongitudinalPlan, DeviceMotion, VehicleParameters.
- **`custom.capnp` holds every SP struct:**
  - ModularAssistiveDrivingSystem, IntelligentCruiseButtonManagement.
  - SelfdriveStateSP, LongitudinalPlanSP, CarParamsSP, CarControlSP, CarStateSP.
  - `OnroadEventSP.EventName` (~line 336).
  - LiveMapDataSP, ModelDataV2SP, GpsLocationSP, ModelManagerSP, BackupManagerSP.
  - **Fork additions:** `CarControlSP.jvePilot` (~392) and `CarStateSP.jvePilot` (~465).
- **`car.capnp` (CarState, CarControl, CarParams) comes from `opendbc_repo/opendbc/car/car.capnp`.** Python code uses
  the dataclass mirror `opendbc/car/structs.py`, so a new car field goes in both.

### sunnypilot layer (`openpilot/sunnypilot/`)

| path | feature | key files |
|---|---|---|
| `__init__.py` | shared helpers | `PARAMS_UPDATE_PERIOD = 3` s (SP classes re-read params on this cadence), `get_sanitize_int_param`, `IntEnumBase` |
| `common/version.h` | `SUNNYPILOT_VERSION` | |
| `mads/` | **MADS**: lateral control without longitudinal engagement | `mads.py: ModularAssistiveDrivingSystem`, `state.py`, `helpers.py` (steering-on-brake mode, alt-experience flags) |
| `selfdrive/controls/controlsd_ext.py` | controlsd extension | `ControlsExt`: lateral-controller swap, `get_lat_active`, publishes `carControlSP` |
| `selfdrive/controls/lib/longitudinal_planner.py` | SP long targets | `LongitudinalPlannerSP`: min(cruise, SCC-vision, SCC-map, SLA), publishes `longitudinalPlanSP` |
| `selfdrive/controls/lib/smart_cruise_control/` | **SCC**: slowing for curves | `vision_controller.py` (model curvature), `map_controller.py` (OSM) |
| `selfdrive/controls/lib/speed_limit/` | **speed limit**: source choice + assist | `speed_limit_resolver.py` (car vs map, by `Policy`), `speed_limit_assist.py` (SLA), `common.py` |
| `selfdrive/controls/lib/nnlc/` | **NNLC**: neural-network lateral control | `nnlc.py`, `model.py`, `helpers.py: get_nn_model_path` |
| `selfdrive/controls/lib/latcontrol_torque_*` | torque controller extensions | `_ext.py` (NNLC + overrides), `_jerk_aware.py`, `_v0.py`, `latcontrol_torque_versions.json` |
| `selfdrive/controls/lib/` (other) | lane-change and lateral helpers | `auto_lane_change.py`, `lane_turn_desire.py`, `relc.py` (road-edge lane-change block), `blinker_pause_lateral.py`, `accel_boost.py`, `e2e_alerts_helper.py` (green light, lead depart) |
| `selfdrive/car/` | car-side SP glue | `interfaces.py: setup_interfaces/initialize_params`, `cruise_ext.py: VCruiseHelperSP`, `car_specific.py: CarSpecificEventsSP` |
| `selfdrive/car/intelligent_cruise_button_management/` | **ICBM**: presses cruise buttons to reach a target speed on stock-ACC cars | `controller.py`; **fork:** `jvepilot_params.py` (`JvePilotSettings`), `jvepilot_target.py` (`PlanAccTarget`). The car-side sender is `opendbc/sunnypilot/car/<brand>/icbm.py`. |
| `selfdrive/selfdrived/` | SP events | `events_base.py` (`EventsBase`, `Alert`, `ET`, `Priority`), `events.py: EVENTS_SP`, `button_state_tracker.py` |
| `selfdrive/locationd/` | GPS fusion, torque ext | `gps_fuser.py` (`gpsLocationSP`), `torqued_ext.py` |
| `selfdrive/pandad/` | Rivian long-kit flasher | `rivian_long_flasher.py` |
| `selfdrive/ui/quiet_mode.py` | sound suppression | `QuietMode` (base of `Soundd`) |
| `livedelay/` | live vs cached lateral delay | `helpers.py: get_lat_delay`, `lagd_toggle.py` |
| `models/` | **Model Manager**: choose, download and switch driving models | `manager.py: ModelManagerSP` (process `models_manager`), `fetcher.py`, `helpers.py` (`get_active_bundle`, `get_active_model_runner`) |
| `modeld_v2/` | tinygrad model runner (process `modeld_tinygrad`) | `modeld.py`, `modeld_base.py: ModelStateBase`, `model_adapters.py`, `parse_model_outputs.py`, `fill_model_msg.py`, `warmup.py`, compile tools |
| `mapd/` | OSM data from pfeiferj's Go `mapd` | `mapd_installer.py` (binary), `mapd_manager.py`, `live_map_data/osm_map_data.py` (publishes `liveMapDataSP`) |
| `navd/helpers.py` | geometry and speed helpers for mapd/SCC | |
| `sunnylink/` | sunnylink cloud (its daemon is disabled in this fork) | `api.py`, `athena/sunnylinkd.py`, `backups/manager.py`, `uploader.py`, `settings_ui_src/pages/*.yaml` → `settings_ui.json` (via `tools/compile_settings_ui.py`) |
| `system/` | param migrations, SP stats, sensor drivers | `params_migration.py: run_migration`, `statsd.py`, `sensord/` (C++; its SConscript is not referenced from SConstruct) |
| `tools/` | SP dev tools | `lib/sunnypilot_car_segments.py`, `pull_footage.py` |

Not present: Dynamic Experimental Control. Only `DynamicExperimentalControlDEPRECATED` remains in `custom.capnp`.

### System (`openpilot/system/`)

| path | responsibility | key files |
|---|---|---|
| `manager/` | init, param defaults, process lifecycle | `manager.py` (`manager_init`, `manager_thread`), `process_config.py`, `process.py`, `build.py` |
| `hardware/` | `hardwared` publishes `deviceState` (thermals, power, onroad/ignition) | `hardwared.py`, `fan_controller.py`, `power_monitoring.py` |
| `loggerd/` | rlog/qlog segments, video encode, upload, disk cleanup | `loggerd.cc`, `encoderd.cc`, `uploader.py`, `deleter.py` |
| `camerad/` | Qualcomm camera ISP (C++) | `cameras/camera_qcom2.cc`, `spectra.cc`; `webcam/camerad.py` for PC |
| `sensord/` | IMU (LSM6DS3) | `sensord.py` |
| `athena/` | comma cloud RPC (**disabled in this fork**) | `athenad.py`, `registration.py` |
| `updated/` | OTA git updates into the `/data/safe_staging` overlay | `updated.py` |
| `webrtc/` | live stream / teleop | `webrtcd.py` |
| `ubloxd/`, `qcomgpsd/` | GNSS | |
| `ui/` | shared raylib UI toolkit | `lib/application.py` (`gui_app`, `big_ui()`), `lib/multilang.py` (`tr`), `widgets/`; SP widgets in `ui/sunnypilot/widgets/` |

### Common (`openpilot/common/`)

- **Params:**
  - Store: one file per key in `/data/params` (`~/.comma/params` on PC).
  - Every key is declared in `params_keys.h` (see §6); the flags are in `params.h`.
  - Python binding: `params.py`, which uses ctypes to load `libparams_c.so`.
- **Hardware abstraction:**
  - `hardware/__init__.py` exports `HARDWARE`: `comma/hardware.py` on device, `pc/hardware.py` elsewhere.
  - `hardware/hw.py: Paths` gives the file locations (`log_root`, `model_root`, `mapd_root`).
  - Note: this is in `common/`, not `system/hardware/`.
- **Utilities:**
  - `realtime.py` (`Ratekeeper`, priorities), `swaglog.py` (`cloudlog`)
  - `filter_simple.py`, `pid.py`, `simple_kalman.py`, `constants.py` (`CV`)
  - `transformations/`, `prefix.py` (`OPENPILOT_PREFIX`, used for test isolation), `test.py: OpenpilotTestCase`

### UI (`openpilot/selfdrive/ui/`)

- **Entry and layouts.** `ui.py` builds `layouts/main.py: MainLayout` for the 3X/tici "BIG" UI, or
  `mici/layouts/main.py` for comma four.
- **Stock vs SP.** `gui_app.sunnypilot_ui()` is true unless `SUNNYPILOT_UI=0`. When it is true, the stock modules
  import SP subclasses: `UIState(UIStateSP)`, `SettingsLayoutSP`, `HomeLayoutSP`, `AugmentedRoadViewSP`,
  `HudRendererSP` and others.
- **Onroad.** `onroad/{augmented_road_view,hud_renderer,alert_renderer,model_renderer}.py`.
  - SP versions and extras are in `sunnypilot/onroad/` (speed limit, SCC, blind spot, road name, `developer_ui/`).
  - The mici versions are in `mici/onroad/` and `sunnypilot/mici/onroad/`.
- **Settings.** Panels are registered in `sunnypilot/layouts/settings/settings.py` (`PanelType` + the panel dict).
  Page files are siblings of it:
  - Pages: `device.py`, `network.py`, `software.py`, `developer.py`, `models.py`, `visuals.py`, `display.py`,
    `osm.py`, `trips.py`, `sunnylink.py`.
  - Steering: `steering.py` + `steering_sub_layouts/`. Cruise: `cruise.py` + `cruise_sub_layouts/`.
  - Stock toggles: `layouts/settings/toggles.py`.
  - **Vehicle pages:** `sunnypilot/layouts/settings/vehicle/brands/<brand>.py`. `factory.py: _BRAND_MAP` maps
    `CP.brand` to a page class.
  - **Fork:** `brands/chrysler.py` (jvePilot master toggle + `JVEPILOT_PRESET`) and `software.py` ("Set <build>
    default" buttons that run `/data/fork-switch/fork_switch.py`, a tool from suspi/suspipilot).
- **Translations.** `translations/` (`app_<lang>.po`). `update_translations.py` does not scan
  `selfdrive/ui/sunnypilot`.

### Car code (`opendbc_repo/opendbc/`, the suspi/opendbc fork)

| path | what |
|---|---|
| `car/<brand>/` | one port per brand: `interface.py`, `carstate.py`, `carcontroller.py`, `<brand>can.py`, `values.py`, `fingerprints.py`, `radar_interface.py` |
| `car/interfaces.py` | `CarInterfaceBase(ABC, CarInterfaceBaseSP)` (`get_params`, `get_params_sp`, `update` → `(CS, CS_SP)`, `apply(CC, CC_SP)`), `CarStateBase`, `RadarInterfaceBase` |
| `car/car_helpers.py` | `get_car` (fingerprinting) |
| `car/structs.py` | dataclass mirror of `car.capnp` + SP structs. **Fork:** `CarControlSP.JvePilot` (~147) and `CarStateSP.JvePilot` (~177) |
| `car/torque_data/` | per-car torque params |
| `sunnypilot/car/<brand>/` | SP per-brand extensions: `carcontroller_ext.py`, `carstate_ext.py`, `icbm.py` (ICBM button sender), `mads.py`, `values_ext.py`, `fingerprints_ext.py` |
| `sunnypilot/car/` | `interfaces.py: CarInterfaceBaseSP`, `intelligent_cruise_button_management_interface_base.py`, `car_list.json`, `platform_list.py` |
| `safety/` | panda safety in C headers: `modes/<brand>.h` (e.g. `chrysler.h`, `chrysler_cusw.h`), `lateral.h`, `longitudinal.h`, `sunnypilot/` |
| `dbc/` | DBC files |

## 5. Hook seams: where upstream calls into sunnypilot

| upstream file (`openpilot/...`) | sunnypilot hook |
|---|---|
| `selfdrive/controls/controlsd.py` | `class Controls(ControlsExt)`: `initialize_lateral_control`, `get_lat_active`, `run_ext` |
| `selfdrive/controls/lib/longitudinal_planner.py` | `class LongitudinalPlanner(LongitudinalPlannerSP)` |
| `selfdrive/controls/plannerd.py` | `sla.update_buttons`; subscribes to `liveMapDataSP`, `carStateSP`, `selfdriveStateSP`, `gpsLocationSP` |
| `selfdrive/controls/lib/latcontrol_torque.py` | `self.extension = LatControlTorqueExt(...)` |
| `selfdrive/controls/lib/desire_helper.py` | `AutoLaneChangeController`, `LaneTurnController` |
| `selfdrive/selfdrived/selfdrived.py` | `ModularAssistiveDrivingSystem`, `IntelligentCruiseButtonManagement`, `CarSpecificEventsSP`, `EventsSP`, `ButtonStateTracker` |
| `selfdrive/selfdrived/events.py` | `class Events(EventsBase)` |
| `selfdrive/car/card.py` | `initialize_params`, `setup_interfaces`, MADS `set_alternative_experience`; carParamsSP/carStateSP/carControlSP |
| `selfdrive/car/cruise.py` | `class VCruiseHelper(VCruiseHelperSP)` |
| `selfdrive/locationd/torqued.py` / `lagd.py` | `TorqueEstimatorExt`, `get_lat_delay` / `LagdToggle` |
| `selfdrive/modeld/modeld.py` | `class ModelState(ModelStateBase)`, `RoadEdgeLaneChangeController`, publishes `modelDataV2SP` |
| `selfdrive/pandad/pandad.py` | `flash_rivian_long` |
| `selfdrive/ui/{ui_state,soundd,layouts/main,layouts/sidebar,onroad/*}.py` | `UIStateSP`, `QuietMode`, `SettingsLayoutSP` / `HomeLayoutSP`, `SidebarSP`, `AugmentedRoadViewSP`, ... |
| `system/ui/lib/application.py` | `class GuiApplication(GuiApplicationExt)` |
| `system/manager/manager.py` | `run_migration(params)` |
| `system/manager/process_config.py` | `get_active_model_runner`, `MAPD_PATH`, sunnylink readiness checks |
| `tools/lib/logreader.py` | `sunnypilot_car_segments_source` |

To find every seam: `rg -l 'from openpilot.sunnypilot' openpilot --glob '!openpilot/sunnypilot/**'`.

## 6. Recipes for common changes

**Add a param**

1. Add one line to `openpilot/common/params_keys.h`: `{"Name", {PERSISTENT | BACKUP, BOOL, "0"}}`.
   - The SP section starts at ~line 151. The fork's `// suspi: jvePilot` block is at ~181-205.
   - The flags are defined in `params.h`.
2. Rebuild. The keys are compiled into `libparams_c`.
3. Read it with `Params().get_bool("Name")`. SP classes usually re-read every `PARAMS_UPDATE_PERIOD`.
4. Optional:
   - A migration goes in `sunnypilot/system/params_migration.py`.
   - To expose it in the sunnylink web settings, edit `sunnylink/settings_ui_src/`. `test_settings_schema.py` checks
     those keys against `Params().all_keys()`.

**Add a settings toggle**

1. Declare the param (above).
2. In the page's item list, add `toggle_item_sp(tr("Title"), tr("Desc"), param="Name")` from
   `openpilot/system/ui/sunnypilot/widgets/list_view.py`.
   - For numbers use `option_item_sp`; for choices use `multiple_button_item_sp`.
3. Gate the item in the page's `_update_state`. For example, the Chrysler page locks its items while onroad.

**Add an onroad alert**

- Stock: add the enum value to `log.capnp` `OnroadEvent.EventName` and the entry to
  `selfdrive/selfdrived/events.py: EVENTS`.
- SP or fork: add the enum value to `custom.capnp` `OnroadEventSP.EventName` and the entry to
  `sunnypilot/selfdrive/selfdrived/events.py`.
- Offroad alerts: `selfdrive/selfdrived/alerts_offroad.json`.

**Add a field passed from controls to the car**

1. Add it to `CarControlSP` in `openpilot/cereal/custom.capnp`.
2. Add the matching dataclass field to `opendbc/car/structs.py`.
3. Convert it in `selfdrive/car/helpers.py`.
4. Fill it in `ControlsExt` or the ICBM controller, and read it in `opendbc/sunnypilot/car/<brand>/carcontroller_ext.py`.

The jvePilot fields are a worked example.

## 7. Build, test, CI, release

- **Build:** `scons` with the root `SConstruct`.
  - SConscript order: `common`, `msgq`, `cereal`, `panda`, `rednose`, `loggerd`, `camerad` (device only),
    `selfdrive/{pandad, longitudinal_mpc_lib, locationd, modeld, ui}`, then the tools (off device).
  - Release branches are detected by the absence of `.gitmodules`.
  - On device, `system/manager/build.py` runs the build; it is skipped when `prebuilt` exists.
- **Python:**
  - Python 3.12 via `uv` (`pyproject.toml`, `uv.lock`). The submodules are installed editable, and opendbc is forced
    to the submodule copy.
  - Lint: ruff (indent 2, line length 160; bans `time.time`), `ty` for types (not mypy), codespell. Run
    `tools/op.sh lint`.
- **Tests:**
  - `tools/op.sh test [path] [-k TEXT] [-j N]` runs `test_*.py` files. Most live in `tests/` next to the code.
  - Base class: `openpilot/common/test.py: OpenpilotTestCase`, which gives each test its own params prefix.
  - Process replay: `selfdrive/test/process_replay/test_processes.py` against `ref_commit`. Forks regenerate the refs
    locally.
- **CI (`.github/workflows/`):**
  - `tests.yaml`: build, lint, unit tests, process replay, sim.
  - `cereal_validation.yaml`: SP cereal vs upstream.
  - `sunnypilot-build-prebuilt.yaml`, `sunnypilot-master-dev-prep.yaml`.
  - The model build workflows.
  - `Jenkinsfile` runs the on-device tests.
- **Release:**
  - `tools/release/build_release.sh` and `release_files.py` inline the submodules and strip the tree.
  - `build_stripped.sh` makes the nightly / CI branch.
  - `release/ci/publish.sh` stamps `sunnypilot/common/version.h`.
- **Boot on device:** `launch_openpilot.sh` → `launch_chffrplus.sh`, which:
  1. Sources `launch_env.sh`.
  2. Swaps in a finalized update from `/data/safe_staging`.
  3. Symlinks the submodule packages.
  4. Runs `agnos_init`.
  5. Runs `openpilot/system/manager/build.py`, then `manager.py`.

## 8. What this fork changes (vs `upstream/master`)

The fork is 5 commits ahead of `upstream/master` (merge base `6732fcc52`):

- **`3699932e5` + `d5bdbbee8`:**
  - Build-switch buttons in Software settings, refused while engaged.
  - athenad and sunnylinkd turned off in `process_config.py`.
- **`d06fe27f3`:** the plan `docs/plans/2026-11-26_1529_plan-jvepilot-features-in-suspi-sunnypilot-behind-one-featur.md`.
  It has 10 steps, and steps 3-10 are still open.
- **`054b06644`:**
  - Submodule `opendbc_repo` → suspi/opendbc.
  - `JvePilotEnabled` plus about 23 `JvePilot*` params.
  - `CarControlSP.jvePilot` / `CarStateSP.jvePilot`.
  - The Chrysler settings page.
- **`0af197fe3`:**
  - ICBM plan-following ACC set speed, coasting and ACC Eco.
  - Code: `intelligent_cruise_button_management/{controller,jvepilot_params,jvepilot_target}.py`.
  - Tests: `sunnypilot/selfdrive/car/tests/test_jvepilot_target.py`.

To list all fork code: `rg -n -i 'jvepilot|suspi|fork_switch' openpilot opendbc_repo/opendbc`.

## 9. To find X, look at Y

| question | look at |
|---|---|
| which daemons run, and when | `openpilot/system/manager/process_config.py` |
| topic name, rate, schema field | `openpilot/cereal/services.py`, `log.capnp`, `custom.capnp` (SP), `opendbc/car/car.capnp` (car structs) |
| why it won't engage or why it disengaged | `selfdrived.py: update_events` → `selfdrived/state.py` |
| MADS behaviour | `sunnypilot/mads/{mads,state}.py`, `controlsd_ext.py: get_lat_active`, `pandad.cc: process_mads_heartbeat` |
| steering feel / tuning | `selfdrive/controls/lib/latcontrol_torque.py`, `sunnypilot/selfdrive/controls/lib/{nnlc/,latcontrol_torque_*}`, `opendbc/car/torque_data/` |
| accel, braking, following | `selfdrive/controls/lib/{longitudinal_planner,longcontrol}.py`, `longitudinal_mpc_lib/long_mpc.py` |
| why the speed target is capped | `sunnypilot/selfdrive/controls/lib/longitudinal_planner.py: update_targets`; inspect `longitudinalPlanSP` in a log |
| speed limits, curve slowdown | `sunnypilot/selfdrive/controls/lib/{speed_limit,smart_cruise_control}/`, `sunnypilot/mapd/` |
| set speed / cruise buttons / ICBM | `selfdrive/car/cruise.py`, `sunnypilot/selfdrive/car/cruise_ext.py`, `.../intelligent_cruise_button_management/controller.py`, `opendbc/sunnypilot/car/<brand>/icbm.py` |
| Chrysler CAN parsing / commands | `opendbc/car/chrysler/{carstate,carcontroller,chryslercan}.py`, `opendbc/sunnypilot/car/chrysler/*_ext.py`, safety `opendbc/safety/modes/chrysler*.h` |
| driving model choice / download | `sunnypilot/models/{manager,helpers}.py`; runner: `selfdrive/modeld/` (stock) or `sunnypilot/modeld_v2/` (tinygrad) |
| settings page or toggle | `selfdrive/ui/sunnypilot/layouts/settings/`; brand pages in `vehicle/brands/` |
| onroad HUD drawing | `selfdrive/ui/sunnypilot/onroad/`, stock `selfdrive/ui/onroad/` |
| device paths, device vs PC | `openpilot/common/hardware/{hw.py,base.py,comma/,pc/}` |
| logs: reading routes | `openpilot/tools/lib/logreader.py`, `openpilot/tools/replay/`, `tools/op.sh juggle` |
| updates / branch switching | `openpilot/system/updated/updated.py`, `launch_chffrplus.sh` |

Not mapped in depth: the inside of `panda`, `msgq`, `tinygrad` and `rednose` (not checked out here), camerad/loggerd
internals, and `openpilot/tools/cabana`.
