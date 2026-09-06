# CLAUDE.md — BlueBoat Aspect-Aware SSS Survey (superproject)

Root guidance for the superproject that carries five git submodules. This file describes
**how the modules relate to each other**: the merged interface contract, the rules that
hold across module boundaries, the workspace and git architecture.

It is not a backlog. This project tracks open work only inside each submodule's own
`TODO.md`, and this file does not restate it.

**Authority order.** `project_synthesis.md` (project files) is the single source of truth
for scope, system architecture (§5), data structures (§5.2), and every ⚠-marked rule. Where
a module's `CLAUDE.md` contradicts it, §6 below records the disagreement rather than
resolving it silently. Below that, each submodule's `CLAUDE.md` is authoritative for its own
internals. This file is authoritative only for cross-module relationships.

## Verification markers

| Marker | Meaning |
|---|---|
| **VERIFIED** | Stated in `project_synthesis.md`, or in a module `CLAUDE.md` section that module itself marks VERIFIED. |
| **HISTORICAL** | Carried from module documents written from design sessions rather than a scan of the current tree. |
| **UNCERTAIN** | Ambiguous, contested between modules, or never established. |

Markers are carried forward, not upgraded. A fact that `sssCLAUDE.md` marks HISTORICAL is
HISTORICAL here.

---

## 1. System overview

A BlueRobotics BlueBoat USV runs autonomous aspect-aware side-scan sonar survey in shallow
enclosed water. Sonar and navigation stream to a basestation laptop; the basestation returns
waypoint missions. All perception and planning computation is ashore, so the operational
constraint is wireless link bandwidth and latency, not on-board compute. **VERIFIED**
(`project_synthesis.md` §1, §5.1.)

```
BOAT                                    BASESTATION (laptop)
├─ Cerulean Omniscan 450 SS ×2 ──┐      ├─ Mission Control Station  (supervise, command, E-STOP)
├─ GPS / IMU / compass           │      ├─ BlueBoat GCS             (mosaic, overlays, recording)
├─ Water Linked USBL receiver    │      ├─ SSS-Dataset-Aug-Studio   (offline, no ROS)
├─ ArduPilot / MAVROS            │      └─ [detector · belief layer · replanner]  not implemented
└─ blueboat_control stack ◄──────┘
      ▲                                 SIMULATION
      └─ blueboat_sss_sim serves the identical sonar interface, Gazebo owns hull dynamics
```

Boundary of each module's responsibility:

| Module | Runs on | Produces |
|---|---|---|
| **BlueBoat-Control** | boat | Vehicle motion, pose, thrust, trajectories; owns `blueboat_interfaces` |
| **BlueBoat-SSS** — `blueboat_sss` | boat | Sonar acquisition, slant-range correction, bottom tracking, `.svlog` |
| **BlueBoat-SSS** — `blueboat_gcs` | basestation | Live mosaic, overlays, recording sessions, seabed images |
| **BlueBoat-MCS** | basestation | Mission launch/supervision, pattern designer, safe shutdown |
| **BlueBoat-SSS-Sim** | either | GPS-anchored Gazebo worlds (World Builder GUI over MCS anchored paths) + a drop-in replacement for the real sonar interface + the **sea state** (current/waves into Gazebo, `sea_state_node`) |
| **SSS-Dataset-Aug-Studio** | basestation | Physics-informed augmentation of YOLO datasets (offline, file-level only) |

The **belief layer is the only object the replanner reads**; detector, sensor and planner
changes interact only through it (`project_synthesis.md` §5.1 ⚠, echoed as `sssCLAUDE.md`
#15). Nothing in the current tree implements it — see §6, D7.

---

## 2. Workspace layout and build order

**VERIFIED — on-disk directory names.** The superproject repository is
`BlueBoat-SideScanSonar`, and `.gitmodules` gives each submodule a `path` identical to its
repository name, so the table below is both the repository mapping and the on-disk layout:
`BlueBoat-Control`, `BlueBoat-SSS`, `BlueBoat-SSS-Sim`, `BlueBoat-MCS`,
`SSS-Dataset-Aug-Studio`, each directly under the superproject root. A
`.../BlueBoat-SideScanSonar/blueboat_mcs/` path in any older document is history, not the
current tree.

| Submodule repo | Contains | Build system |
|---|---|---|
| `BlueBoat-Control` | ROS 2 packages `blueboat_control`, `blueboat_description`, `blueboat_interfaces` | colcon (ament) |
| `BlueBoat-SSS` | ROS 2 package `blueboat_sss`; standalone app `blueboat_gcs` | colcon for `blueboat_sss`; plain Python for the GCS |
| `BlueBoat-SSS-Sim` | ROS 2 package `blueboat_sss_sim`, nested one level below the git root at `BlueBoat-SSS-Sim/blueboat_sss_sim/` | colcon (ament_python) |
| `BlueBoat-MCS` | `mcs/`, `docs/`, `run.py`, `smoke_test.py`, `build.sh`, `requirements.txt` (plus untracked `ruff.toml` / `requirements-dev.txt`) | standalone Python, no colcon, no `setup.py` |
| `SSS-Dataset-Aug-Studio` | `sss_aug_studio/`, `pyproject.toml`, `tests/`, `docs/` (plus untracked `tools/` and gitignored `.githooks/` / `demo_dataset/`) | pip / `pyproject.toml`, Python ≥ 3.10 |

**ROS workspace — `~/ros2_ws`, VERIFIED.** The superproject is checked out **beneath** it, at
`~/ros2_ws/src/BlueBoat-SideScanSonar/`; it is not itself the colcon workspace. `colcon build`
runs from `~/ros2_ws`, and `~/ros2_ws/install/` currently holds `auv_control`,
`blueboat_control`, `blueboat_description`, `blueboat_interfaces`, `blueboat_sss`,
`blueboat_sss_sim`, `pose_to_tf`, `thruster_manager` and `urdfdom_py`.
`BlueBoat-Control`'s README quotes `~/ros2_ws` and never says `~/blueboat_ws`, so the two
modules agree on the basestation workspace; `/blueboat_ws` is the boat's own workspace and is
named as such in `BlueBoat-MCS`. Two of the five submodules are not colcon packages at all, so
a workspace-root `colcon build` covers only part of the tree.

**Build and dependency order** (ROS side):

1. `blueboat_interfaces` — every ROS module's message and service types resolve here.
   `OmniscanProfile`, `ProcessedSSSPing`, `RequestPath.srv`.
2. `blueboat_control` + `blueboat_description` — the platform stack and the URDF/world launch
   that `blueboat_sss_sim` includes.
3. `blueboat_sss` and `blueboat_sss_sim` — both additive; `blueboat_sss_sim` modifies no
   other package (`simCLAUDE.md` NC #8).

`blueboat_gcs`, `BlueBoat-MCS` and `SSS-Dataset-Aug-Studio` do not participate in the colcon
build. The GCS and MCS import `rclpy` from a sourced workspace at runtime and both degrade to
a GUI-only mode when it is absent. The Aug Studio has no ROS dependency in any mode; the one file in it that reaches outside its own repository is the untracked developer script `tools/make_demo_dataset.py`, which puts `../BlueBoat-SSS-Sim/blueboat_sss_sim` on `sys.path` to rebuild the demo fixture through the simulator's ROS-free offline path, and is not part of the installed package.

**Package naming in the simulator (VERIFIED, current state).** The name is
`blueboat_sss_sim` everywhere — `package.xml` `<name>`, `setup.py` `package_name`, the ament
resource marker, `setup.cfg`'s `script_dir`, the Python module directory, and all eight
`console_scripts`. Both `ros2 launch blueboat_sss_sim …` and `ros2 run blueboat_sss_sim …`
resolve; the installed `lib/blueboat_sss_sim/` carries `sss_sim_node`,
`mavros_shim_node`, `world_builder`, `generate_world`, `export_scene_maps`,
`mission_metrics`, `sss_calibration_report` and `sss_svlog_compare` (the 2026-09 rework deleted
`dataset_recorder_node`, `sss_path_generation` and `generate_mission`; a stale
install may still carry them until the next `colcon build`).
Offline tools also run as `python3 -m blueboat_sss_sim.<module>` from the package source
root. The rename is done; `simTODO.md` no longer carries a [P0].

**Cross-repo file deployment — resolved; no file is owned twice any more.**
`BlueBoat-MCS/integration/` **no longer exists** (`BlueBoat-MCS/` holds `mcs/`, `docs/`,
`run.py`, `smoke_test.py`, `build.sh` and `requirements.txt`; `ruff.toml` and
`requirements-dev.txt` are present but gitignored). The four files
it used to carry — `path_generation.py`, `yaml_trajectory.py`, `master_control.py`,
`robot_interface.py` — are all committed in `blueboat_control` and installed by its
`CMakeLists.txt`. The interface guarantees §4 attributed to that deployment are therefore
unconditional properties of `blueboat_control` itself: world-frame `/monitoring_data` at all
five capture sites, and the `from_yaml` trajectory branch with its file watch. Nothing
needs copying onto the boat beyond a normal `colcon build` of `BlueBoat-Control`.

---

## 2.1 Git operations — session boundary

**Sessions never run `git commit` or `git push`, in the superproject or in any submodule.**
Make the requested file changes and stop there; the user handles staging, committing and
pushing themselves, everywhere in this tree.

## 3. Git architecture

The top-level repository is a **superproject**. The five module directories are git
submodules, not ordinary nested directories, and this changes what a commit means.

- Each submodule is an **independent repository** with its own history, branches and remote.
  A file change inside a submodule belongs to that submodule's repository and is committed
  there.
- The superproject stores only a **commit pointer** (gitlink) per submodule — a single SHA
  recording which commit of that repo the superproject expects. It stores none of the
  submodule's file contents.
- Committing in the superproject therefore **does not commit the file changes inside a
  submodule**. It records at most that the pointer moved. Edited-but-uncommitted files inside
  a submodule are invisible to a superproject commit; `git status` at the root shows the
  submodule as modified without showing which files.
- The correct sequence for a change to module code: commit (and push) inside the submodule
  first, then stage the submodule path in the superproject and commit the moved pointer.
  Doing only the second half records a pointer to a commit that exists nowhere else.
- A fresh clone needs `git clone --recurse-submodules`, or `git submodule update --init
  --recursive` afterwards; otherwise the module directories are empty.
- `git submodule update` checks each submodule out at the recorded SHA in **detached HEAD**.
  Work committed there without first checking out a branch is easy to strand.
- `git pull` in the superproject moves pointers but does not update working trees; the
  submodules follow only on `git submodule update`.
- Paths in `.gitmodules` are authoritative for the layout, and disagree with §2 where §2 is
  marked UNCERTAIN.

---

## 4. Cross-module interface contract

The merged inventory. Where two modules state different values for the same thing, both
values appear in the row — that disagreement is itself a current cross-module fact, and its
resolution lives in whichever module's `TODO.md` is named.

Names are **absolute** in the source. `master_control` is constructed with
`namespace='blueboat'`, but ROS 2 does not namespace absolute names, so they resolve exactly
as written (`ctrlCLAUDE.md` §2).

### 4.1 Vehicle and control

| Name | Type | Producer | Consumers | QoS | Notes |
|---|---|---|---|---|---|
| `/blueboat/odom` | `nav_msgs/Odometry` | `robot_interface` (real) · Gazebo bridge (sim, `odom_topic` param) | `master_control`, `sss_processor_node`, `sss_sim_node`, GCS, MCS | default 10 | **Disagreement resolved (2026-08-31): both publish local ENU.** Real: position translated at `robot_interface`'s first callback (world origin = boat at launch), axes East/North, yaw **absolute ENU** — no longer re-zeroed. Sim: bridged from Gazebo in ENU with no re-zeroing (`simCLAUDE.md` §8). Only the origin differs. The previous real frame was a *hybrid* (ENU axes, launch-relative yaw), the root cause of the East-only trajectory-following field symptom — see `mcsCLAUDE.md` §2 and `BlueBoat-MCS/docs/03_ros_integration.md` item 00. `sssTODO.md` holds a separate item that this topic reads zero on the real boat. |
| `/blueboat/pinger_coordinates` | `std_msgs/Float32MultiArray` `[x, y, z]` | `robot_interface` | `master_control`, GCS, MCS | default | **Body/vehicle frame, three values.** Seeded from the Water Linked *filtered* (`filaco`) x/y/z and dead-reckoned at odom rate between USBL fixes, so the published array is the full 3-vector; `master_control` reads `[:2]` in its `PID` branch and passes all three to `solve_LoS` in its `LoS` branch. A consumer that assumes length 2 is reading a length-3 array. The 2-element **world-frame** `corrected_pinger` goes out on this same topic only under `robot_interface`'s `fixed_pinger`, hard-coded `False` and settable from no parameter or topic. GCS default `alignment.pinger_frame: robot`. |
| `/blueboat/controller_ready` | `std_msgs/Bool` | `robot_interface` (real, `:94`) · `simulation_interface` (sim, `:41`) | `master_control` (`:94`), MCS — also the **E-STOP acknowledgement** (`False` on latch, 2026-09-04) | **Producer-dependent:** real = default depth 10, VOLATILE; sim = latched (TRANSIENT_LOCAL) | Both consumers subscribe volatile depth 10, which is compatible with either producer (a volatile subscriber does receive from a TRANSIENT_LOCAL publisher), so neither end may be "fixed" to match the other (CM-4). On the real robot, late subscribers are covered by `robot_interface`'s periodic re-publish (`ready_republish_period = 1.0` s) rather than by durability, because one-shot handshakes race DDS discovery. |
| `/thruster_input` | `std_msgs/Float32MultiArray` | `master_control` | `robot_interface`, `simulation_interface`, MCS | default | Order is **`[right, left]`** in Newtons. No longer provisional: `ctrlCLAUDE.md` §5 traces the convention statically end to end (allocation matrix ↔ URDF geometry ↔ `ROV` alphabetical ordering ↔ `simulation_interface` ↔ `solve_LoS` ↔ `manualMove` ↔ CLI), and `ctrlTODO.md` §2 narrows the open question to one link only — whether ArduPilot's `SERVO1` is physically the right thruster. **Never silent while `master_control` runs**: every early return publishes `[0, 0]`, and both interface nodes zero the thrust if it goes quiet for `thruster_input_timeout` (0.5 s). |
| `/controller_target` | `std_msgs/Float32MultiArray` | `master_control` | `robot_interface` | default | Deliberately **body-frame** for the pinger case. Not to be unified with `/monitoring_data` — different signals (`ctrlCLAUDE.md` N9). |
| `/monitoring_data` | `std_msgs/Float32MultiArray` | `master_control` | `robot_interface`, MCS | default | `[t, x, y, psi, x_d, y_d, psi_d, u1, u2]`. `x_d/y_d/psi_d` are **world-frame in every controller branch** — the capture is committed in `BlueBoat-Control` (`master_control.py`, the `--- world-frame monitoring target ---` markers, **five capture sites**: manual, the MPC / PID / LoS path branches, and the pinger branch) and installed by its `CMakeLists.txt`, so the residual risk is a stale boat build, not a missing patch (`mcsTODO.md` A3). **Rate: 20 Hz.** ⚠ How that rate is set differs between `BlueBoat-Control`'s committed SHA (`self.dt = 0.05`, hardcoded, `master_control.py:106`) and its current working tree (`self.dt = dbl('control_dt', 0.05)`, `:263`, a declared ROS parameter, therefore launch-settable). Which the boat runs cannot be told from this repository. MCS `DiagnosticsConfig.expected_hz` and `BlueBoat-MCS/docs/03_ros_integration.md` both assume 20. |
| `/blueboat/input_str` | `std_msgs/String` | MCS `command_center`, operator CLI | **`robot_interface` only** | default | Values: `enable`, `disable`, `stop`, `override`, `default`, `arm`, `disarm`, `move <l> <r> <s>`. Neither `param_set` nor `master_control` subscribes it — `robot_interface` translates `override`/`default` onto `/blueboat/param_str`, which is what `param_set` reads. An unrecognised first token falls through to the move handler, which still requires exactly four whitespace-separated fields; an **empty** message is ignored (it used to raise `IndexError` inside the callback). `stop` **latches** (CM-15 corollary) and `enable` is the only thing that clears it. |
| `/blueboat/manual_target` | `std_msgs/Float32MultiArray` `[x, y]` | MCS, GCS visualisation app | `master_control` | default | **World frame on the wire.** `[0.0, 0.0]` is the resume-original-mission sentinel, not a coordinate; a genuine origin click is nudged by `1e-3`. |
| `/blueboat/param_str` | `std_msgs/String` | `robot_interface` | `param_set` | default | |
| `/blueboat/param_ready` | `std_msgs/Bool` | `param_set` | `robot_interface` | default | Republished periodically. |
| `/blueboat/param_mode` | `std_msgs/String` | `param_set` | `robot_interface`, MCS | default | `'default'` / `'override'`, or `''` = "alive, no mode locked". **Heartbeated at 1 Hz** since 2026-09-04, and published unconditionally rather than only after the first successful apply — previously the topic was silent until then, which is why `robot_interface` logged `current: ''` while `param_set` sat on a latched `busy`. Consumers must treat a repeat as *state*, not as an acknowledgement of a new command: MCS's safe-shutdown requires a **transition** into `default`, and `robot_interface`'s `mode_callback` / `param_callback` are edge-triggered. |
| `/uw_gps_data` | `std_msgs/Float32MultiArray` | `uwgps_log` | `robot_interface`, MCS | default | 19 values: date(7), aco xyz, ant xyz, lat/lon/dep, filaco xyz. |
| `/pose_arrow` | `visualization_msgs/Marker` | `master_control` | RViz / Gazebo | default | Debug only. |
| `/current` | `geometry_msgs/Vector3` | `sea_state_node` (sim, 2026-09-03) — previously nobody | ros_gz bridge → gz `/ocean_current` → the boat's `Hydrodynamics` plugin | default | World-frame water velocity: mean current + Gauss-Markov fluctuation + wave orbital velocity; exact zeros under the null preset. Bridged by both `world_launch.py` and `full_mission_launch.py` |
| `/world/<w>/wrench`, `/world/<w>/wrench/clear` | `ros_gz_interfaces/EntityWrench`, `/Entity` | `sea_state_node` | ros_gz bridge → gz `ApplyLinkWrench` (injected at run time when the world lacks it) | default | One-shot wave wrench per physics step on model `blueboat` (torque about the link origin); nothing published while calm |
| `/sim/sea_state` | `std_msgs/String` (JSON) | `sea_state_node` | MCS (SEA STATE box) | **TRANSIENT_LOCAL, depth 1**, 2 Hz | Presets, bearings, Hs/Tp, η, wrench, schedule, summary — `BlueBoat-SSS-Sim/docs/topics.md` |
| `/sim/sea_state/command` | `std_msgs/String` (JSON) | MCS ("Modify situation…") | `sea_state_node` | default | `{current, waves, ramp_s}` or `{schedule, t0}`; the node ramps, never steps |
| `/set_path` | `nav_msgs/Path` | `path_publisher` (`blueboat_control`) | GCS, RViz | default | **Ownership settled:** `blueboat_control/src/_custom_libraries/path_publisher.py`, installed by its `CMakeLists.txt` and listed in `ctrlCLAUDE.md` §2.1. Node name `path_publisher`, publishing the *relative* name `set_path` in the root namespace. It re-requests the whole path every `refresh_period` (5 s) rather than once, so a `from_yaml` mission deployed after launch appears. Started by `Sim_launch.py` and by the simulator's `full_mission_launch.py`; `BlueBoat_launch.py` does **not** start it, so there is no `/set_path` on the real boat. |

### 4.2 Path service

| Name | Type | Servers | Clients | Notes |
|---|---|---|---|---|
| `/path_request` | `blueboat_interfaces/srv/RequestPath` | `path_generation` (`blueboat_control`) — **the only server** since the 2026-09 sim rework deleted `sss_path_generation` (simulated missions ride the same `from_yaml` branch as real ones) | `master_control`, `path_publisher`, the two standalone `mpc_control` nodes, MCS | **Exactly one server may run.** Request is `Float32MultiArray path_request` — an array of path-parameter values, deliberately parameter-agnostic; response is `nav_msgs/Path`, `frame_id: "world"`, one pose per value. **VERIFIED against `blueboat_interfaces/srv/RequestPath.srv`**, which is exactly `std_msgs/Float32MultiArray path_request` / `---` / `nav_msgs/Path path` and nothing else. `master_control` requests `linspace(tau, tau + path_time, path_steps)`; `path_publisher` requests a *time window* `[0, total_time]` with its own defaults of 1000 s at 0.1 s (10 001 poses), re-requested every `refresh_period` (5 s), so `full_mission_launch` sets `total_time` from the bundle's stored `duration_s`. |
| `/mission/full_path` | `nav_msgs/Path` | *(none — retired with `sss_path_generation`, 2026-09)* | RViz | The full-mission RViz view now comes from `path_publisher`'s `/set_path` alone. |

### 4.3 Sonar acquisition

The real `sss_node.py` and the simulator's `sss_sim_node` both use node name
`side_scan_sonar`, so private topics resolve identically and downstream runs unmodified
against either. **VERIFIED** in both modules.

| Name | Type | Producer | Consumers | QoS | Notes |
|---|---|---|---|---|---|
| `/side_scan_sonar/{port,starboard}/profile` | `blueboat_interfaces/OmniscanProfile` | `sss_node` (real) · `sss_sim_node` (sim) | `sss_processor_node`; **GCS since 2026-09-05** (BEST_EFFORT subscriber, depth 200: the raw bins are cached by `ping_number` and attached to the matching `/sss_processor/processed` row so the live waterfall/AI pictures draw the same native row replay decodes from the `.svlog`) | BEST_EFFORT, KEEP_LAST, **10** | Decoded header including `channel_number`, `transducer_heading_deg`, `ping_number`, `pwr_results`. Marked VERIFIED in `sssCLAUDE.md`, against both `sss_node.py` and the `.msg`. **`pwr_results` is `uint16[]` — settled**, read from the definition itself, `BlueBoat-Control/blueboat_interfaces/msg/OmniscanProfile.msg`, which is the only place the type exists (CM-1). The simulator's reconstructed reference copy, `BlueBoat-SSS-Sim/blueboat_sss_sim/msg_reference/OmniscanProfile.msg`, matches that definition field for field and in order — VERIFIED by direct comparison; it defines no message and is documentation only. Its trailing comment on `pwr_results` still reads "linear echo power", which the per-ping normalisation below contradicts. The full field list is snapshotted in `BlueBoat-Control/.claude/tools/interface_baseline.json`, and its guard fails on any field change. **`pwr_results` is normalised per ping, not absolute counts** — the device rescales every ping onto its own dB axis and reports the endpoints in `min_pwr_db` / `max_pwr_db`, so consumers invert it with `db = min + raw/65535·(max − min)` (`sss_helper.scale_to_db`, applied by `sss_processor_node` and the GCS alike). Measured on **68 948 / 68 948** pings of the Shiraishi-jima corpus: exactly one bin at 65535, minimum exactly 0, span clamped at 90 dB. `blueboat_sss_sim` emits the same three invariants; stacking raw arrays from different pings into a waterfall without converting to dB first is wrong at either end. |
| `/side_scan_sonar/{port,starboard}/raw` | `std_msgs/UInt8MultiArray` | `sss_node` · `sss_sim_node` | `sss_processor_node` only — **the GCS does not subscribe** (VERIFIED; it subscribes to `~/profile` instead) | BEST_EFFORT, KEEP_LAST, 10 | Already-framed Cerulean Ping Protocol packet, republished verbatim. Layout: `'B''R' \| u16 payload_len \| u16 msg_id=2198 \| u8 src \| u8 dst \| 52-byte payload \| u16[num_results] \| u16 checksum`. Frame length `8 + 52 + 2·num_results + 2` (1262 B at 600 bins). The processor rebuilds `.svlog` from this; disabling it produces empty logs. |
| `/side_scan_sonar/ping/enable` | `std_msgs/Bool` | GCS (name VERIFIED in `blueboat_gcs/config/default.yaml`), operator, launch one-shot | `sss_node`, `sss_sim_node` | default 10 | Pinging is **off at startup in both**. The simulator re-reads run-dependent parameters on every enable. |
| `/side_scan_sonar/ground_truth/contacts` | `std_msgs/String` (JSON) | `sss_sim_node` | offline analysis (`mission_metrics --source jsonl` on a dump; the recorder node is deleted) | default 10 | **Simulation-only, additive.** Per ping cycle: `{"t_sim", "contacts":[{"side","object_id","type","slant_range_m","extent_bins","shadow_bins","visible","ping_number","ghost","via"}]}`. `ghost`/`via` mark a multipath image — the same `object_id` down a folded path off the named reflector (`via: "wall:<name>"` for a wall, `via: "surface"` for the optional z = 0 mirror, `""` direct); consumers aggregate on `(object_id, via)`, and both keys default to direct when absent. |
| `/sss_processor/processed` | `blueboat_interfaces/ProcessedSSSPing` | `sss_processor_node` | GCS | BEST_EFFORT, depth **200** at the GCS | Slant-range corrected, water column already removed. Sign of `*_y` encodes side: **+y = port, −y = starboard**. Topic name VERIFIED at both ends (`sss_processor_node.py` publishes `~/processed` under node name `sss_processor`; `blueboat_gcs/config/default.yaml` subscribes the absolute name). |
| `/sss_processor/log/enable` | `std_msgs/Bool` | GCS (Record ON/OFF) | `sss_processor_node` | default | Name VERIFIED at both ends (`~/log/enable` under node name `sss_processor`; `blueboat_gcs/config/default.yaml`). |
| `/sss_ai/seabed_analysis` | `std_msgs/String` (JSON, schema 1) | GCS | *(no consumer in the current tree)* | default | Image metadata + detections, **never pixels**. |
| `/sss_ai/detections` | `vision_msgs/Detection2DArray` | *(none)* | GCS | default | Placeholder; not wired to a model. This is the wire slot a detector would occupy. Name from `blueboat_gcs/config/default.yaml`. |
| `/rosout` | `rcl_interfaces/Log` | all nodes | GCS embedded console | default | The GCS also matches the literal string `sss_processor_node` to sweep orphan processes on STOP, so that executable name and its `output='screen'` are load-bearing. |

**Acquisition parameters** — identical names and semantics across real and simulated nodes
(`range_start_mm`, `range_length_mm`, `msec_per_ping`, `gain_index`, `num_results`,
`pulse_len_percent`), with **two different defaults for the same knob currently in the
tree**:

| Parameter | `blueboat_sss_sim` default | `sss_node.py` default | `SSS_processing_launch.py` default | `project_synthesis.md` §8.5 reserved |
|---|---|---|---|---|
| `range_length_mm` | 15000 | 20000 | 20000 | 30 m coverage pass / 15 m revisit pass |
| `gain_index` | 4 | −1 (device auto) | −1 (device auto) | — |

`BlueBoat-SSS` is internally consistent at 20000 across all three of its declaration sites
(`sssCLAUDE.md`), chosen as a no-argument default sized from water depth per its NC #5; §8.5's
30 m coverage pass and 15 m revisit pass must be passed explicitly per run. **No file in
`BlueBoat-SSS` passes either**: `terminals.txt`, the operator command sheet, passes
`range_length_mm:=20000` — the default restated — and neither 30000 nor 15000 appears
anywhere in that module.

**Settled: the defaults stay divergent, and comparability is carried by explicitness.**
Aligning them would move the simulator's default off its power-calibration anchor (the 15 m
capture, `simCLAUDE.md` NC #6) onto a value (20000) that matches neither §8.5 pass. Instead,
`blueboat_sss_sim`'s launch files pass all six acquisition parameters to `sss_sim_node` from
the resolved sonar profile (explicit `sonar_config:=` > a legacy bundle's frozen
`sonar.yaml` > the package `config/default_sonar.yaml` — world folders freeze no sonar
copy), each overridable per run as a launch argument, and the node warns when the
acquisition in force differs from what the named profile records; §8.5's
coverage pass ships as `config/coverage_pass_sonar.yaml` (30000). `gain_index: -1` is a
command-only sentinel — `OmniscanProfile.gain_index` is `uint16`, so the device resolves
auto-gain internally and reports a concrete index; the simulator, having no AGC, resolves it
to the calibrated index 4 and reports 4. The simulator's modelled ladder is **0–7**, with
4–7 measured off the corpus (`analog_gain` 74.55 / 142.8 / 242.025 / 464.625) because the
device's auto-gain walks all four inside every recording. `sssCLAUDE.md` NC #5 adds an independent constraint
that range be set from water depth (~4× the deepest expected) rather than from the area to
cover.

**Transducer lateral offset** — a shared physical value the two modules do not agree on:
`mount_y_abs_m: 0.20` in the simulator, `TRANSDUCER_Y_OFFSET_PORT_M / _STBD_M = 0.0` in
`sss_processor_node.py`. `simTODO.md` [P1] holds it.

**Ping-rate cap — settled (2026-09-02, VERIFIED on the corpus).** The device period is
`max(50 ms, 2R/c + ~3 ms)` on all seven field recordings (50 ms at 18.4 m and 20 m, 54 ms at
38 m, 131 ms at 95.6 m, 170 ms at 125.6 m), i.e. the spec sheet's "20 pings/s up to 30 m,
thereafter limited by range and speed of sound". The simulator's `ping_period_s` implements
exactly that (`max_ping_rate_hz` 20, `DEVICE_PROCESSING_MS` 3); the earlier "22 ms at 15 m"
figure was wrong. Consequence for sim-vs-real ping counts: a 30 m coverage pass pings at
20 Hz, a 95.6 m survey at 7.6 Hz — compare runs at the same `range_length_mm`.

**Ping assembly** — both stacks now key rows on `ping_number` and emit one-sided rows;
neither pairs by arrival time, and neither withholds a ping while the bottom tracker
bootstraps (`sssCLAUDE.md` NC #2). **Since 2026-09-03 the processor re-bases on a
counter restart** (a key ≥ 128 behind the newest seen = the device or the simulator was
relaunched under a running processor) and judges "stream stopped" on the wall clock
against the last arrival only, never wall time against a message stamp — sonar stamps
are sim time under Gazebo. Before that, relaunching `sss_sim_node` under a running
processor published every ping as two half-rows for the rest of the run (measured:
7464 one-sided rows in one session; the GCS waterfall's "one black row in two per side").
Both the processor and the GCS now warn when > 25 % of recent rows are one-sided. `ProcessedSSSPing.msg`'s own header comment in
`BlueBoat-Control/blueboat_interfaces/` still describes a "10-ping bootstrap before first
publish"; no such gate exists in `sss_processor_node.py`, so the comment is stale and the
message contract is unaffected. The simulator's same-tick rule (`simCLAUDE.md` NC #3)
is therefore **no longer load-bearing for the processor**. It remains in force as the
simulator's own rule until `BlueBoat-SSS-Sim` chooses to relax it — that is its call, not
`BlueBoat-SSS`'s (CM-3).

**Ping counters are per-device.** The two Omniscan 450 units number their pings
independently, with an offset that is constant per power-up but otherwise arbitrary
(**0, −1 and +60 all measured** across the 16 two-sided field logs; see
`BlueBoat-SSS/blueboat_gcs/docs/SONARVIEW_SVLOG_ANALYSIS.md` §9.3). Raw `ping_number` is
therefore **not** a shared key across sides: on a +60 log it merges halves acquired up to
3.0 s apart. Any module that assembles, replays or relabels dual-channel sonar rows must
align the counters first. Consequences for consumers: `port_ping_number` and
`starboard_ping_number` in one `ProcessedSSSPing` **legitimately differ** by that offset,
so a torn row is signalled by the gap *changing*, never by it being non-zero.

### 4.4 MAVROS boundary

| Name | Type | Direction | Module |
|---|---|---|---|
| `/mavros/state` | `mavros_msgs/State` | in | `robot_interface`; MCS (only when `mavros_msgs` imports — absent in simulation) |
| `/mavros/imu/data` | `sensor_msgs/Imu` | in | `robot_interface` |
| `/mavros/local_position/odom` | `nav_msgs/Odometry` | in | `robot_interface` |
| `/mavros/global_position/global` | `sensor_msgs/NavSatFix` | in | `robot_interface`, GCS, MCS — **BEST_EFFORT**; `lat==0 and lon==0` means no fix and is discarded. In a Gazebo run of a GPS-anchored mission, **MCS is the only publisher** (its bridge synthesises the fixes from sim odom, ~5 Hz, and leaves `status` at the ROS 2 Iron+ message default **-2 / STATUS_UNKNOWN**) — so a consumer must not treat every negative status as "no fix"; only `-1` (STATUS_NO_FIX) means that. The GCS gate (`utils/geodesy.navsat_fix_ok`) rejecting all `status < 0` was the "GCS sees no GPS while MCS anchors" bug (fixed 2026-09-01) |
| `/mavros/global_position/compass_hdg` | `std_msgs/Float64` | in | MCS, GCS. Degrees **clockwise from north**; MCS converts as `radians(90 - hdg)`. Preferred heading source; odom yaw (absolute ENU since 2026-08-31) is the fallback |
| `/mavros/rc/override` | `mavros_msgs/OverrideRCIn` | out | `robot_interface` at ~20 Hz, latest-wins |

FCU endpoint is the `fcu_url` **launch argument** of `BlueBoat_launch.py`, defaulting to
`udp://:14550@192.168.2.2:14550`; it is no longer hard-coded. **Port 14550 collides with a
running QGroundControl**, which surfaces as intermittent launch failures (`mavros_router` logs
`link[1000] open failed: DeviceError:udp:bind: Address already in use`). Close QGC, or pass
`fcu_url:=` with another port.

The simulator's `mavros_shim_node` (on by default in its launches) republishes
`/blueboat/odom` as `/mavros/global_position/compass_hdg`, `/mavros/imu/data`,
`/mavros/local_position/pose` and `/mavros/global_position/global` (NavSatFix
about the world's own GPS anchor — `sss_sim_launch.py` reads it from the world
folder's manifest; the odom subscription lost in f489a21 is restored).
It exists for tooling written against MAVROS names — note that it publishes
`local_position/pose` (`PoseStamped`) while `robot_interface` consumes
`local_position/odom` (`Odometry`), and `robot_interface` does not run in simulation anyway.
The sonar interface needs no shim: vehicle heading rides inside every `OmniscanProfile`.

### 4.5 File-level interfaces

The Aug Studio exposes **no ROS interface of any kind**. It integrates through files and CLI
only. Several other handoffs are also file-mediated.

| Artifact | Producer | Consumer(s) | Contract |
|---|---|---|---|
| `.svlog` | `sss_processor_node` (from `~/raw`) | GCS replay window, SonarView | Framed Cerulean Ping Protocol stream; packet ids 10, 12, 150, 2194, 2198; device ids port 1, starboard 2, platform 3. Files roll at 500 MB. Recorded files are **primary field data**. |
| Recording session `data_root/sessions/<stamp>/` | GCS | analysis, dataset build | `mosaic/`, `waterfall/` (`waterfall_raw.npz` = archival raw record; the AI feed is the seabed **pictures**), `detections/`, `seabed_images/`, `metadata.json`, and the adopted `*.svlog` at the session root. Created when Record turns ON; nothing is exported if no session was active. |
| Seabed images `seabed_XXXXX.png` + `metadata/` | GCS | detector training, Aug Studio | **Raw waterfall in the native slant-bin domain** (SonarView convention): one column per device range bin, verbatim values; width adapts to the acquisition, and the dark centre band is the physical water column, darkened by the display model (`core/display_model.py`, one model per window shared with the waterfall and the mosaic; stored in every JSON as `display_model` — losslessly invertible). **Rows are speed-corrected to square pixels since 2026-09-05** (`seabed.row_geometry: square`, PROVISIONAL; each row copies exactly one ping's bins verbatim, `ping_index` per row; revert with `ping`): 256 rows, stride 128, in picture rows. **The AI is fed the pictures plus their JSON metadata** (per-row pose/time/altitude/bottom/source ping, `bin_pitch_m`, the closed-form pixel→world formula) — decided 2026-09-01; the companion `_world.npz` (per-pixel world grids + float dB + model curves) is an auxiliary georeferencing/analysis record, not the training input. |
| World folder `~/worlds/<path_name>/<world_name>/` (`world.sdf`, `seabed.stl`, `scene.npz`, `scene_manifest.yaml` with an additive `geo:` block, `depth.npz`, `preview_objects.png`, `metadata.yaml`, `builder_state.yaml`, optional `depth_source.*`) | `world_builder` GUI / `generate_world` (sim) | Gazebo, `sss_sim_node`, MCS overlays (via `metadata.yaml`'s GPS ground truth) | One directory, **immutable** — every save (Edit-mode re-saves included) takes a fresh silent `_i` suffix. World (0,0) ≡ the source MCS path's `geo_anchor`; the frame is the path's design frame, conversions via the shared equirectangular pair. `scene.npz` + manifest are the ground truth for every simulation-derived metric the thesis reports. (The former mission bundles are retired; existing ones still load everywhere — their frozen `sonar.yaml`/`trajectory.yaml` are the resolver fallbacks.) |
| YOLO dataset (Ultralytics layout) | beach labelling pipeline (real); the sim's `dataset_recorder_node` was **deleted 2026-09** (dataset generation left the simulator's scope) | Aug Studio, detector training | The Aug Studio treats the input directory as **read-only** and writes to a new output directory. |
| `sss_aug_dataset.yaml` | dataset author | Aug Studio | Declares **any `AcquisitionMeta` field** — not just `layout`, `intensity_mapping` and `shadow_included` — each honoured at the top level or inside `meta:`, equivalent positions with the top level winning on conflict, and an unrecognised key at either position warning by name; the reader never raises. **`intensity_mapping` must be declared explicitly.** When absent the Aug Studio assumes `log` (dB waterfall export) and inverts on that basis, which mis-inverts a linear dataset. **Neither in-project producer writes this file**: `dataset_recorder_node` emits only `dataset.yaml`, and the GCS seabed imager emits PNG + JSON + `_world.npz`. **The sim half declares the fields anyway, in the file it does write**: `dataset_recorder_node`'s `dataset.yaml` states `layout: waterfall`, `intensity_mapping: db` and `shadow_included: true` at the top level, and repeats `intensity_mapping: db` inside `meta:` alongside `range_equalised`, `normalisation` and `percentiles`, so the one field whose default is wrong is declared at both positions the reader honours and never falls to that default — its tiles are absolute dB (converted per ping from the endpoints), range-equalised, then stretched per tile at percentiles 1.0 / 99.5, and no log is applied on top. The GCS half still falls to the `log` default while writing dB, and remains wrong in scale because the Aug Studio's `log` inverse uses one fixed `log_range_db` against the GCS's per-image 2.0 / 98.0 stretch. Emitting the file is those modules' call (CM-3). No real (non-synthetic) dataset exists on this machine to audit. |
| Augmented dataset + `generation_manifest.json` + `statistics.md` | `sss-aug-generate` | detector training | Byte-reproducible for a given config + `master_seed`, independent of worker count. |
| Sea-state presets `share/blueboat_sss_sim/config/sea_states.yaml` (`blueboat_sea_state_presets/1`) and timelines `~/.config/blueboat_mcs/sea_states/*.yaml` (`blueboat_sea_schedule/1`) | presets: the simulator; timelines: the MCS sea-state dialog | `sea_state_node` (`sea_schedule:=`, `/sim/sea_state/command`), the MCS launch dialog (reads the presets as a file, never imports — CM-3) | Presets: `current`/`waves` name → strength + `label`/`description`/`reference`; directions are per run. Timeline: `keyframes: [{t_s, current: {preset\|speed_mps…, from\|from_deg}, waves: {…}}]`, `interpolation: linear\|hold`, `seed` |
| Trajectory `<name>.yaml` (`blueboat_trajectory/1`) | MCS Pattern Designer | `path_generation` on the boat (stock — the branch is committed, not patched in) | Dense `[t, x, y, yaw]` samples + `speed`, `loop`, `length_m`, `duration_s`. Selected through the existing launch argument as `trajectory:=from_yaml:/abs/path.yaml` — no launch-file change. The file is **watched**: the robot holds a station-keeping pose at the origin until it appears, which is what makes deferred GPS-anchored deployment possible. `<name>.meta.yaml` is editor-only and the robot never reads it; `.deployed/<name>.yaml` is regenerated every launch and is not hand-edited. |
| Position/pinger CSV `<root>/data/Robot_data/{date}-{note}-poslog.csv` | `robot_interface` | offline analysis, `poslog_report.py`, `BlueBoat-Control/…/docs/controllers/replay.py` | **Raw field record.** Two layouts, selected by `use_UWgps`; `target_*` columns exist only in the no-pinger layout and read `/monitoring_data[4:6]`, world-frame in every branch. **Path is no longer relative to the launch working directory** — see the `<root>` note below. Note `replay.py` cannot actually read it (it looks for columns no revision ever had); `poslog_report.py` is the reader that can. |
| Mission report folder `<root>/data/Robot_data/<csv stem>/` | `robot_interface`'s shutdown hook, via the ROS-free `poslog_report.py` (also a CLI: `ros2 run blueboat_control poslog_report.py <csv\|dir --all>`) | the operator, offline analysis | Created when the run ends; the poslog CSV, its `-origin.yaml` sidecar and a `<csv stem>.png` report are **moved** into it. Moving a field record is allowed, rewriting one is not (CM-7): an existing folder is never touched and re-running is a no-op. The PNG carries the GPS track (robot vs target, no tiles, true metric aspect), robot→target distance, ground speed, per-side commanded thrust with the `actuation_state` strip beneath it, and a summary table. matplotlib is imported lazily, so a boat without it still gets the folder and the files. |
| Controller `.npy` `<root>/data/{ctrl}_data/{date}-{ctrl}_{sim}_data.npy` | `master_control` | offline analysis, `replay.py` | Schema `['t','x','y','psi','x_d','y_d','psi_d','u1','u2']`, target columns world-frame. The header row is appended as strings, so `np.save` coerces the whole array to strings — cast back on load. `robot_interface` does not write this file. |

**`<root>` for the two `BlueBoat-Control` run artifacts** is resolved at node start by
`custom_functions.data_root`, first match wins: the node's `data_dir` parameter when non-empty
→ `$BLUEBOAT_DATA_DIR` → the sourced workspace (parent of the first `$COLCON_PREFIX_PATH`
entry) → the process working directory. In normal use the third branch answers and both files
land under `~/ros2_ws/data/`, **independently of the directory the launch was invoked from** —
which is what keeps a run started by the Mission Control Station out of the station's own
repository. `BlueBoat_launch.py` and `Sim_launch.py` both expose `data_dir:=`. An unwritable
root is a launch failure naming the path, not a silent fallback, and names are claimed with
`O_EXCL`, so two runs inside the same second get `-2`, `-3`, … rather than one overwriting the
other (CM-7).

### 4.6 Shared conventions

| Convention | Statement |
|---|---|
| Side identity | `channel_number` 0 = port, 1 = starboard, at **byte 34** of the raw framed packet. Simulator: `Side.PORT.sign = +1` (+y body), `STARBOARD = −1`; transducer heading = vehicle heading ∓ 90°. Processed pings: **+y = port, −y = starboard**. Consistent across modules. |
| Frames | Simulator world is **ENU**, z = 0 at the surface, depths negative. Internal math uses ENU yaw; anything hardware- or user-facing uses compass degrees. MCS: yaw in radians, CCW-positive about +z; the map scene is **local east/north metres about the first GPS fix** — one regime, north-up, never rotates, gated on the GPS anchor (`BlueBoat-MCS/GPS_MAP_ARCHITECTURE.md`). Real `/blueboat/odom` is local ENU with **absolute** yaw (2026-08-31 fix), matching the sim in kind. |
| Frame on the wire | `/blueboat/manual_target` is **world**. `/blueboat/pinger_coordinates` and `/controller_target` are **body**. `/monitoring_data` is **world in every branch**. `master_control` converts the manual target via `inRobotFrame()` before `solve_LoS()` and passes the pinger vector through, so both are robot-frame at the solver — that asymmetry is correct by design. |
| MAVROS twist | `/mavros/local_position/odom` has `child_frame_id: base_link`, so `twist` is already body-frame while `pose` is world-frame. `robot_interface` re-expresses **pose** into a boot-relative frame and passes **twist** through untouched. |
| Gazebo generation | The development machine is ROS 2 **Jazzy** + Gazebo **Harmonic** (`gz sim` 8.11.0, `libgz-sim8-*-system.so`); Fortress is not installed. `blueboat_sss_sim` emits `gz-sim-*` names throughout (shipped config and code-level fallbacks) and its generated worlds load with no deprecation warnings. `blueboat_description` is still uniformly Fortress-named (`ignition-gazebo-*-system` / `ignition::gazebo::systems::*`) and loads only through Harmonic's deprecated-name shim, which warns per plugin and is removed in gz-sim 9. `ctrlTODO.md` §1 holds the port. |
| TF | `project_synthesis.md` §5.2 specifies `map → odom → base_link → sss_link` with lever-arm offsets. **No module publishes or consumes that tree**, and no module reads TF at all. The one TF publisher anywhere in the project is the external `pose_to_tf` node that `blueboat_description/launch/upload_rov_launch.py` starts **in simulation only**, emitting a single `world → blueboat/base_link` transform for RViz; there is no `map`, no `odom` and no `sss_link` frame. Geometry is handled per-module, and the lever-arm point surfaces instead as the transducer-offset disagreement in §4.3. |

---

## 5. Project-wide non-negotiables

Promoted here only where the constraint is genuinely cross-module — because it governs a
shared boundary, or because two or more modules arrived at it independently. Module-local
rules stay in the module.

**CM-1 — Topic, service and parameter signatures are a cross-repo contract.** No module
changes a name or message type unilaterally. Refactors change file internals only. Converged
independently: `ctrlCLAUDE.md` N1, `simCLAUDE.md` NC #1, and the whole of §4 above depends on
it. `blueboat_interfaces` is the only place a message type is defined; the simulator reuses
it and defines no new type, putting additional simulation data on new additive JSON topics
(`ground_truth/contacts` is the pattern).

**CM-2 — Simulation and real water expose the identical ROS interface.** Same names, types,
QoS (BEST_EFFORT / KEEP_LAST / 10 on the sonar topics), parameter names, node names and
ping-enable semantics. Downstream stacks run unmodified in both; divergence invalidates the
sim-to-real comparison the thesis rests on. Converged: `ctrlCLAUDE.md` N2, `simCLAUDE.md`
NC #1. The default-value divergences recorded in §4.3 are the live exceptions.

**CM-3 — No module modifies a neighbour's package.** Integration happens by serving identical
interfaces. Converged: `simCLAUDE.md` NC #8, `mcsCLAUDE.md` N9, `ctrlCLAUDE.md` N1. **The rule
now holds with no exception:** the `BlueBoat-MCS/integration/` copies of four
`blueboat_control` nodes are gone, their content is committed in `blueboat_control` itself
(§2), and no source file in the project is owned by two submodules.

**CM-4 — QoS is changed at both ends or not at all.** A `RELIABLE` subscriber against a
`BEST_EFFORT` publisher is incompatible and receives *nothing*; a non-latched subscriber
against `TRANSIENT_LOCAL` never sees `/blueboat/controller_ready`. `sssCLAUDE.md` NC #4 states
the first; the latched-readiness row in §4.1 is the second instance of the same failure mode.

**CM-5 — Side identity comes from the packet, never from the topic or the `src` tag.**
`channel_number` at byte 34, falling back to the sign of `transducer_heading_deg`. VERIFIED
against 5250 packets with zero mismatches. Applies to any module that consumes raw frames or
profiles.

**CM-6 — Never drop a ping.** Rows assemble by `ping_number` — **normalised by the
per-device counter offset**, since the two units number independently (§4.3); one-sided
rows are emitted rather than discarded; no ping is withheld because the bottom tracker has
not locked. `sssCLAUDE.md` NC #2. Obeyed by `sss_processor_node` and the GCS replay path
alike; a missing pose is the only sanctioned drop, and it is BlueBoat-Control's to fix.

**CM-7 — Field data and generated ground truth are write-once.** Recorded `.svlog` files,
position CSVs and controller `.npy` logs are primary field record and are never overwritten
or regenerated; mission bundles are immutable snapshots regenerated rather than edited; the
Aug Studio never modifies an input dataset. Converged across four modules: `sssCLAUDE.md`
NC #6, `ctrlCLAUDE.md` §6, `simCLAUDE.md` NC #10, `augCLAUDE.md` #1.

**CM-8 — Monitoring output is world-frame in every controller branch, and no consumer
re-applies a frame correction.** The conversion belongs at the source. Converged:
`ctrlCLAUDE.md` N9 and `mcsCLAUDE.md` N3 state the two halves of the same rule.

**CM-9 — The belief layer is the only object the replanner reads.** Detector, sensor and
planner changes interact only through it. `project_synthesis.md` §5.1 ⚠, `sssCLAUDE.md` #15.

**CM-10 — AI inputs are waterfall-domain and boat-relative, never world-frame mosaic crops.**
World-frame patches distort near turns and introduce intensity-aggregation ambiguity where
cells are revisited. `project_synthesis.md` §5.2 ⚠, `sssCLAUDE.md` #12.

**CM-11 — The headline detector trains on real imagery only.** Synthetic data is for the
policy comparison, the sim-to-real transfer-gap experiment and development. Training the
headline detector on synthetic imagery would inherit aspect sensitivity from the model rather
than measuring it. Converged: `project_synthesis.md` §7.6 ⚠, `sssCLAUDE.md` #11,
`simCLAUDE.md` NC #11, and the Aug Studio's stated role.

**CM-12 — The policy baseline is two-pass orthogonal, and it is tuned seriously.** Single-pass
is a strawman. A deliberately weakened baseline is detected instantly and sinks the
comparison. `project_synthesis.md` §7.3 ⚠ and §8.6 ⚠, `sssCLAUDE.md` #13, `mcsCLAUDE.md` N10.

**CM-13 — Headline results are stated as model-conditional.** "In a calibrated simulation
environment…", never as an unqualified empirical finding, and the caveat leads the
limitations chapter rather than being buried in it. `project_synthesis.md` §4.1 ⚠,
`sssCLAUDE.md` #16, `mcsCLAUDE.md` N10. The evidence architecture in `project_synthesis.md`
§4 governs which layer may support which claim; no layer is used above its evidential weight.

**CM-14 — Perception, control and AI iteration happen offline against recorded rosbags, never
in the water.** Field time is weather-gated and is the project's scarcest resource; needing a
field session to test a change means the replay tooling has a gap. Converged:
`project_synthesis.md` §8.6 ⚠, `ctrlCLAUDE.md` N7, `sssCLAUDE.md` #14.

**CM-15 — Safe shutdown precedes terminating a launch.** Publish `default` on
`/blueboat/input_str`, confirm a matched subscriber, wait for the `/blueboat/param_mode` echo,
flush, then terminate. Killing the launch first can leave the motors in override.
`mcsCLAUDE.md` N1; `ctrlCLAUDE.md` N5 states the robot-side half — the default servo mapping
is restored before shutdown, and a SERVO function is never set to `0`. Since 2026-09-04 both
robot-side nodes also attempt that restore themselves, in independent bounded `try/finally`
blocks; those are best effort (a launch teardown SIGINTs the whole process group, mavros
included) and do not replace the station's sequence.

**Corollary, added 2026-09-04: stopping the motors, releasing the servo mapping and ending
the mission are three separate operator actions and are never re-nested.** The station's
E-STOP publishes `stop` — which robot-side zeroes thrust, closes the `enable_motors` gate,
disarms and **latches** until an explicit `enable` — and touches neither the parameter mode
nor the launch. Leaving override is a *transfer* of authority (the RC channels go back to
whatever else is transmitting), so it can never be part of a panic button. `mcsCLAUDE.md`
N1b carries the table; `ctrlCLAUDE.md` N4b carries the latch.

**CM-16 — `enable_motors` gates all thruster output, and a closed gate holds neutral.**
No **thrust-bearing** PWM reaches the motors unless `enable_motors:=True`. Every write to
`/mavros/rc/override` outside the gate carries neutral 1500/1500 or channel release.
**Reworded 2026-09-04** — it previously read "no code path writes to `/mavros/rc/override`
around that gate", and writing *nothing* turned out to be the unsafe option: `robot_interface`
requests `override` unconditionally at init, so `SERVO1/3_FUNCTION` are on RCIN passthrough
and the ESCs follow RC channels 1 and 3 from any transmitter, with nothing feeding ArduPilot's
`RC_OVERRIDE_TIME` to keep those channels ours. A silent gate therefore left the motors
drivable by a hand transmitter, a QGC joystick or an RC failsafe. The gate now streams true
neutral (0 N is an exact knot of the calibration table) while in override, which pins the
channels and feeds the watchdog. `ctrlCLAUDE.md` N4.

---

## 6. Discrepancies against `project_synthesis.md`

Recorded as current relational facts. `project_synthesis.md` outranks a module `CLAUDE.md` by
project convention; where a module describes something that demonstrably exists and runs, that
is noted with which source is the more reliable guide for the question at hand.

**D1 — Where preprocessing runs.** `project_synthesis.md` §5.1 places SSS preprocessing
(slant-range correction, FBR altitude, geocoding, normalization) on the **basestation**.
`sssCLAUDE.md` describes `sss_processor_node.py` as a `blueboat_sss` node **running on the
robot**, doing exactly that work. *More reliable for the current deployment:* the module —
it describes a node that runs. `project_synthesis.md` remains authoritative for the target
architecture and for the claim that no on-board compute constraint exists. The two are
reconcilable if the synthesis diagram is read as a logical pipeline rather than a placement.

**D2 — SSS ping message schema.** `project_synthesis.md` §5.2 specifies a custom two-sided
message (`sound_speed`, `range_max`, `num_samples`, `uint8[] port_intensities`, `uint8[]
starboard_intensities`, `ping_period`). What exists is `blueboat_interfaces/OmniscanProfile`
— one-sided, one topic per side, mirroring the decoded Cerulean header with `channel_number`,
`transducer_heading_deg`, `ping_number`, `pwr_results` (**`uint16[]`**, not `uint8`, and
normalised per ping onto `[min_pwr_db, max_pwr_db]` rather than absolute — §4.3; read from
the definition in `BlueBoat-Control/blueboat_interfaces/`). *More reliable:* the modules — the
message type exists, three modules consume it, and its field list is marked VERIFIED in
`sssCLAUDE.md` and snapshotted by `BlueBoat-Control`'s interface guard. §5.2's schema reads as a pre-implementation design
sketch. The synthesis's *derived* content in the same section — the three-step ping→world
transform and the slant-range correction `r_ground = sqrt(r_slant² − h²)` — is unaffected and
holds.

**D3 — Maximum ping rate — resolved.** §5.1's 20 Hz is right: the corpus shows exactly 50 ms
at ≤30 m and the range-limited `2R/c + 3 ms` beyond (§4.3). The "22 ms per channel at 15 m"
capture figure was a misreading and is retired from the simulator's documentation.

**D4 — Continuous world-frame mosaic.** §5.3 ⚠ says the world-frame mosaic is generated on
demand or post-mission, not continuously, because it is wasteful and off the critical path.
The GCS `MosaicService` builds one **live** over satellite tiles. *Reading that reconciles
them:* the ⚠ constrains the **detector's** input path, and the GCS mosaic is an operator
display that feeds no detector — CM-10 is what actually protects the perception pipeline, and
it is not violated. If a detector is ever fed from the mosaic, the ⚠ binds directly.

**D5 — Range settings.** §8.5 reserves 30 m per side for coverage passes and 15 m for revisit
passes. `sssCLAUDE.md` NC #5 states an independent constraint — set range from water depth
(~4× the deepest expected), because an 80 m range in shallow water pushed the bottom return
to sample 49/600 and broke bottom detection. Three implemented defaults sit against the
reserved values (§4.3). The two rules are compatible in the harbour band and can conflict in
very shallow water; §8.5 remains authoritative for what the experiments use.

**D6 — TF tree.** §5.2 specifies `map → odom → base_link → sss_link` and notes lever-arm
offsets matter. **No module consumes TF, and none of those four frames exists.** The one
publisher in the project is the external `pose_to_tf` node that `blueboat_description`'s
simulation spawn launch starts, emitting `world → blueboat/base_link` for RViz alone; geometry
is otherwise handled per-module (§4.6). The lever-arm point surfaces instead as the
transducer-offset disagreement in §4.3.

**D7 — Unimplemented interface boundary.** The detector, belief layer (multi-channel Bayesian
grid: `p_target`, `n_observations`, `aspect_coverage`, `last_intensity`, `max_confidence`),
initial CPP, replanner and mission manager are specified in §5 and correspond to deliverables
D3, D4, D6, D7. No submodule implements them, and no submodule is designated to own them. The
GCS's unwired `vision_msgs/Detection2DArray` subscription is the only wire slot that
anticipates any of it. Detector output schema, belief-grid channels, the three replanner rules
(resolution, budget, abandonment) and the confidence-calibration requirement are governed by
`project_synthesis.md` §5.2, §8.1 and §8.2 until a module claims them.

---

## 7. Where the detail lives

The root describes relationships. Each submodule remains authoritative for its own internals
and its own backlog; do not duplicate either here.

| Topic | Read |
|---|---|
| Scope, evidence architecture, headline claim phrasing, design rules | `project_synthesis.md` §§1–4, §8 (project files) |
| Experiment design, target classes, metrics, campaign planning | `project_synthesis.md` §7–§8.4 and `target_families_and_surrogates.md` — **out of scope for this file** |
| Controllers, guidance law, thrust path, trajectory library, MAVROS bridge | `BlueBoat-Control/.claude/CLAUDE.md` · open items `BlueBoat-Control/.claude/TODO.md`. Deeper still, inside the package: `blueboat_control/src/TRAJECTORY_SYSTEM.md` (reference generation, F-series findings) and `blueboat_control/src/CONTROLLERS.md` (measured controller comparison, C-series) |
| Sonar driver, processor, `.svlog` format, GCS internals, measured acquisition settings | `BlueBoat-SSS/.claude/CLAUDE.md` · open items `BlueBoat-SSS/.claude/TODO.md` |
| Acoustic model, world generation, mission bundles, renderer seams, smoke test | `BlueBoat-SSS-Sim/.claude/CLAUDE.md` · open items `BlueBoat-SSS-Sim/.claude/TODO.md` (no [P0] open) |
| Station threading model, map and georeferencing, Pattern Designer | `BlueBoat-MCS/.claude/CLAUDE.md` · open items `BlueBoat-MCS/.claude/TODO.md` |
| Augmentation families, intensity-domain policy, reproducibility contract, extension contract, release gates | `SSS-Dataset-Aug-Studio/.claude/CLAUDE.md` · open items `SSS-Dataset-Aug-Studio/.claude/TODO.md` |

Every module's `CLAUDE.md` and `TODO.md` live under `<module>/.claude/`, not at the module
root. Where a module's `CLAUDE.md` marks its own repo layout UNCERTAIN or its GCS/controller
sections HISTORICAL, the repository outranks the document. Prefer reading a file to trusting
a description of it.

Two modules have lint tooling, both `ruff check .` and both clean at ruff 0.16.5.
`BlueBoat-MCS` configures it in its own `ruff.toml`, needing neither ROS nor a venv — but
`ruff.toml` and `requirements-dev.txt` are in that module's `.gitignore` and untracked, so
like `BlueBoat-Control`'s harness the gate exists only in the working tree, not in a fresh
clone. `SSS-Dataset-Aug-Studio` configures it in `pyproject.toml`, which **is** tracked:
ruff's own default rule set with an enumerated baseline of ignores, `ruff>=0.6` declared in
its `[dev]` extra. No module has a type-checker configured — MCS records a reasoned decline
in its `CLAUDE.md` §7, and the Aug Studio's `CLAUDE.md` records the same for both a
type-checker and CI. The test gates are per-module:
`python3 -m test.smoke_test` (simulator, ~290 checks incl. the 2026-09-03
sections [10] sea state / [11] schema help / objects v3 / walls+pontoons,
~90 s, passing; plus an optional `QT_QPA_PLATFORM=offscreen python3 -m
test.gui_smoke` for its World Builder GUI, not part of the gate),
`QT_QPA_PLATFORM=offscreen python3 smoke_test.py` (MCS, 22 checkpoints incl.
`sea state ok` and `sea box ok`, passing), `pytest` (Aug Studio, 64 tests at v0.4.0,
10 marked `gui`, all passing; a no-PySide6 environment skips the Qt suite and stays green),
`QT_QPA_PLATFORM=offscreen python3 -m pytest` from `BlueBoat-SSS/blueboat_sss/`
(291 tests collected on 2026-09-05: the GCS regression suite needing no ROS — now
including the display-model, live-native and seabed-picture suites — one rclpy-gated
MCS sim-GPS compatibility test, plus the robot-side tests that run only when
`blueboat_interfaces` is on the path — including the 2026-09-03 counter-restart
re-base and wall-vs-stream clock tests; also wired as a pre-commit hook). Every
test that reproduces a MEASURED field number is gated on a `.svlog` corpus at a hard-coded
external mount and skips when it is absent — with neither the corpus nor
`blueboat_interfaces`, 225 pass and 66 skip (globally-sourced Jazzy machine). Like the other modules' harnesses, **this gate
is not in a fresh clone either:** `BlueBoat-SSS/.gitignore` excludes `.githooks/`,
`requirements-dev.txt` and `.claude/specs`, and `blueboat_sss/tests/`,
`blueboat_sss/pytest.ini`, `blueboat_gcs/analysis/` and `.claude/skills/` are untracked.
`BlueBoat-Control` has **no test framework and no committed gate**, but two working-tree gates
that both run: `python3 .claude/tools/interface_inventory.py --check
.claude/tools/interface_baseline.json` (the N1/CM-1 contract surface — 100 pub/sub/service/
client/parameter entries plus the three `blueboat_interfaces` field lists; stdlib only, ~0.15 s,
also wired as a `PostToolUse` hook), and five plain exit-code scripts under
`blueboat_control/src/docs/controllers/` (`check_pid_equivalence`, `check_replay`,
`check_watchdog`, `check_los_hold`, `check_trajectory_library`). **All five pass** (exit 0);
`check_trajectory_library` is sensitive to the scipy build it runs on and has been seen to
exit 1 on a one-ULP quaternion difference that is not a shape change — `ctrlCLAUDE.md` §3
carries the detail. **None of this is committed:**
`.gitignore` excludes `.claude/tools/`, `.claude/settings.json` and `.claude/specs/`, and the
six harness scripts are untracked, so a fresh clone of `BlueBoat-Control` has neither gate.

`BlueBoat-SSS-Sim`'s suite is its **only** gate — no lint, no type-checker, no `pyproject.toml`
or `ruff.toml` anywhere in that repo — and it is wired to run every turn through two hooks in
`.claude/settings.json`, both implemented in `.claude/tools/smoke_gate.py` (stdlib only, no
ROS, no colcon, no Gazebo). **The wiring does not survive a fresh clone:** that module's
`.gitignore` excludes `.claude/tools/`, `.claude/settings.json` and `.claude/specs/`, so a
clone gets `test/smoke_test.py` but neither hook. Its section `[2f]` is gated on a `.svlog`
corpus at `$BLUEBOAT_SSS_CORPUS` (default `~/ros2_ws/data/SSS_data`) and skips when absent, so
a clone still reaches `ALL CHECKS PASSED`. Separately, that module's entire 2026-09
rework — the World Builder (`builder/`), `core/geo.py`, `core/trajectory.py`,
`worldgen/depth/`, `worldgen/world_folder.py`, the catalog/launch/analysis changes and
the deletions of `dataset/`, `mission/`, `sss_path_generation` and the three mission
YAMLs — is present in the working tree but **not yet committed**, so the tracked tree
is well behind what everything above describes.

`SSS-Dataset-Aug-Studio` carries two further gates beyond `pytest` and `ruff`:
`python tools/repro_gate.py` (the CM-7 / non-negotiable #2 byte-reproducibility release
gate — one `GenerationConfig` run at 1 and at 4 workers, hard-comparing images, labels and
`generation_manifest.json`; passes) and `python tools/docs_sync_check.py` (stdlib-only,
wired through `.githooks/pre-commit`, blocking a commit that changes a file under
`augmentations/` without its encyclopedia page and `AUGMENTATION_STRATEGIES.md` section).
**Neither survives a fresh clone either:** that module's `.gitignore` excludes `.githooks/`,
`demo_dataset/` and `.claude/specs/`, and all of `tools/`, `tests/test_gui_smoke.py`,
`tests/test_dataset_metadata.py`, `docs/history/` and the four `docs/demo_*.png` figures are
untracked — so a clone gets no gate scripts, no hooks, no fixture to run them against, and a
`pytest` collecting 47 tests rather than 64. The tracked `demo_dataset/` files are still the
superseded three-image fixture, staged as deletions against the current four-image one.
Separately, in a ROS-sourced shell bare `pytest` fails before collection there: plugin
autoload pulls `launch_testing` from `/opt/ros/jazzy`, which imports `lark`, absent from that
module's venv — `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest` is the workaround, and the module
has no ROS dependency of its own.
