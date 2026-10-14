# CLAUDE.md — BlueBoat Aspect-Aware SSS Survey (superproject)

Root guidance for the superproject carrying five git submodules: **how the modules relate** —
merged interface contract, cross-module rules, workspace and git architecture. Not a backlog:
open work lives only in each submodule's own `TODO.md`, never restated here.

**Authority order.** `project_synthesis.md` (project files) is the single source of truth for
scope, system architecture (§5), data structures (§5.2) and every ⚠-marked rule; where a
module's `CLAUDE.md` contradicts it, §6 records the disagreement rather than resolving it
silently. Below that, each submodule's `CLAUDE.md` is authoritative for its own internals;
this file only for cross-module relationships.

## Verification markers

| Marker | Meaning |
|---|---|
| **VERIFIED** | Stated in `project_synthesis.md`, or in a module `CLAUDE.md` section that module itself marks VERIFIED. |
| **HISTORICAL** | Carried from module documents written from design sessions rather than a scan of the current tree. |
| **UNCERTAIN** | Ambiguous, contested between modules, or never established. |

Markers are carried forward, never upgraded: HISTORICAL in `sssCLAUDE.md` is HISTORICAL here.

---

## 1. System overview

A BlueRobotics BlueBoat USV runs autonomous aspect-aware side-scan sonar survey in shallow
enclosed water. Sonar and navigation stream over the BlueBoat Base Station WiFi link to the
operator laptop, which runs **all** project software and returns the waypoint missions; the
operational constraint is link bandwidth and latency, not on-board compute. **VERIFIED**
(`project_synthesis.md` §1, §5.1; deployment §1.1.)

```
BOAT — hardware + its own firmware only    THIS COMPUTER (operator laptop, ~/ros2_ws) — ALL our code
├─ Cerulean Omniscan 450 SS ×2 (.92/.93)   ├─ MAVROS · blueboat_control (robot_interface, master_control, …)
├─ ArduPilot / BlueOS autopilot (.2)       ├─ blueboat_sss: sss_node.py (sonar driver) · sss_processor_node
├─ GPS / compass                           ├─ Mission Control Station  (supervise, command, E-STOP)
└─ Water Linked USBL (.94)                 ├─ BlueBoat GCS             (mosaic, overlays, recording)
        ▲                                  ├─ SSS-Dataset-Aug-Studio   (offline, no ROS)
        └── BlueBoat Base Station (WiFi) ──┤  [detector · belief layer · replanner]  not implemented
            192.168.2.0/24                 └─ SIMULATION: blueboat_sss_sim serves the identical sonar
                                              interface, Gazebo owns hull dynamics
```

### 1.1 Deployment — **VERIFIED by the owner, 2026-09-28**

**All** code runs on **this computer** (`~/ros2_ws`): every ROS node (MAVROS,
`robot_interface`, `master_control`, `path_generation`, `uwgps_log`, `sss_node.py`,
`sss_processor_node`, the simulator), the Mission Control Station and the GCS. It reaches the
boat through the **BlueBoat Base Station** — Blue Robotics' WiFi radio link, never a name for
the laptop. The boat carries only hardware and its own firmware: ArduPilot/BlueOS autopilot
(MAVROS at `192.168.2.2`), two Omniscan 450 SS (`192.168.2.92` / `.93`, TCP 51200, driven by
`sss_node.py` from here), GPS/compass, Water Linked USBL (`192.168.2.94`, polled by
`uwgps_log` from here). **Nothing of ours runs on the boat. `/blueboat_ws` never existed in
this project** — a months-old artifact never to be expected, suggested or documented again. A
stale deployment is a stale `~/ros2_ws/install` (rebuild with `colcon build`), never a "boat
build". In documents "robot-side" / "on the boat" never locate software: name the node, or say
"in a real-robot run".
**One owner-ordered exception (2026-10-14):** the connection-loss guardian
`link_guardian/autopilot/link_guardian.lua` (superproject, not a submodule) is an ArduPilot
Lua script copied onto the autopilot — autopilot configuration, not a ROS node. While its
session flag `LGRD_ON` is set (by the laptop for every real-robot session; reset at every
autopilot boot) and MAVROS's heartbeat (ROS 2 MAVROS: **sys 1 / comp 191**) has been silent
for `LGRD_TIMEOUT` s, it switches `SERVO1/3_FUNCTION` from passthrough to 74/73, **arms the
autopilot itself** if needed (ArduPilot refuses to arm on passthrough), and enters RTL. Its
laptop companion `link_guardian/laptop/guardian.py` (plain script, not a colcon package) is
started by MCS with every real-robot launch: sets the flag, moves HOME to each run start,
serves MCS's GUARDIAN box over `/link_guardian/status` / `/link_guardian/command`. Design,
setup and test ladder: `link_guardian/README.md`.

| Module | Produces |
|---|---|
| **BlueBoat-Control** | Vehicle motion, pose, thrust, trajectories; per-run ros2bag + kinematic Gazebo replay of a run (v1.1); owns `blueboat_interfaces` — **frozen at tag `v1.0`** (§3) |
| **BlueBoat-SSS** — `blueboat_sss` | Sonar acquisition, slant-range correction, bottom tracking, `.svlog` |
| **BlueBoat-SSS** — `blueboat_gcs` | Live mosaic, overlays, recording sessions, seabed images |
| **BlueBoat-MCS** | Mission launch/supervision (incl. "From a ros2bag" replay launches and the link guardian's GUARDIAN box, v1.1), pattern designer, safe shutdown — **frozen at tag `v1.0`** (§3) |
| **BlueBoat-SSS-Sim** | GPS-anchored Gazebo worlds (World Builder GUI over MCS anchored paths) + a drop-in replacement for the real sonar interface + the **sea state** (current/waves into Gazebo, `sea_state_node`) |
| **SSS-Dataset-Aug-Studio** | Physics-informed augmentation of YOLO datasets (offline, file-level only) |

---

## 2. Workspace layout and build order

**VERIFIED.** Each submodule's `.gitmodules` `path` equals its repository name, directly under
the root; the one surprise is that the simulator's ROS package sits one level below its git
root, at `BlueBoat-SSS-Sim/blueboat_sss_sim/`. A `.../BlueBoat-SideScanSonar/blueboat_mcs/`
path in an older document is history.

`~/ros2_ws` is the project's **only** ROS workspace (§1.1). The superproject is checked out at
`~/ros2_ws/src/BlueBoat-SideScanSonar/` and is not itself the colcon workspace; `colcon build`
runs from `~/ros2_ws`. Build `blueboat_interfaces` first — every ROS module's types resolve
there (`OmniscanProfile`, `ProcessedSSSPing`, `RequestPath.srv`); `blueboat_sss_sim` modifies
no other package (`simCLAUDE.md` NC #8). Two submodules are not colcon packages:
`blueboat_gcs` and `BlueBoat-MCS` import `rclpy` from a sourced workspace at runtime and
degrade to GUI-only without it; `SSS-Dataset-Aug-Studio` has no ROS dependency in any mode
(its dev-only `tools/make_demo_dataset.py` puts `../BlueBoat-SSS-Sim/blueboat_sss_sim` on
`sys.path` for the simulator's ROS-free offline path; not installed).

**No file is owned twice.** `BlueBoat-MCS/integration/` **no longer exists**; its four nodes
are committed in and installed by `blueboat_control` — nothing needs copying beyond a normal
`colcon build`.

---

## 2.1 Git operations — session boundary

**Sessions never run `git commit` or `git push`, in the superproject or in any submodule.**
Make the requested file changes and stop there; the user handles staging, committing and
pushing themselves, everywhere in this tree.

## 3. Git architecture

The five module directories are git **submodules**, each an independent repository; root
`git status` shows a submodule as modified without naming files — inspect inside it.
`.gitmodules` paths are authoritative for the layout.

**Frozen modules (recorded 2026-09-18).** `BlueBoat-Control` and `BlueBoat-MCS` are frozen at
tag `v1.0` (Control `65b15bb` "Dev V1.0 (#1)", MCS `790934f` "V1.0 (#1)", both on
`origin/main`, 2026-09-14). The superproject gitlinks point at the `dev` HEADs `d64ac71` /
`3cfb58c`, trees byte-identical to the tags (`git rev-parse v1.0^{tree}` = `HEAD^{tree}` in
both, verified 2026-09-17); the tag is not an ancestor of `dev`, so `git describe --tags`
fails there by design. **Sessions do not edit these two submodules** unless the user
explicitly orders it; a needed change becomes a post-v1.0 item in the requesting module's
`TODO.md` or a review's update plan. Re-verified online 2026-09-28: `origin/main` = `v1.0`,
`origin/dev` = the gitlink, trees identical. **On 2026-09-28 the user ordered documentation,
comment and UI-text corrections** in both (the §1.1 deployment wording; no behaviour change),
and on 2026-10-08 a split of each `.claude/CLAUDE.md` into a trimmed root plus nested
`CLAUDE.md` files (Control: `blueboat_control/src/`, `blueboat_description/`, `log_reviewer/`;
MCS: `mcs/designer/`) — documentation only. **Also on 2026-10-08 the user ordered the MCS sea-state UI
redesign** (`mcs/core/sea.py`, `gui/dialogs/sea_state_dialog.py`, new
`gui/dialogs/sea_timeline_dialog.py`, `gui/sea_state_box.py`, `gui/theme.py`, the smoke-test
sea blocks and the MCS docs) — a behaviour change of those files only; launch arguments and
topics unchanged. **On 2026-10-09 the user ordered the run-session update in both modules**
(a real-robot launch connects and idles; runs are started / stopped from the station, one
log per run; Update Mission between runs; arrow-key control; Release E-STOP): Control's
`master_control.py`, `robot_interaction/robot_interface.py`, `launch/BlueBoat_launch.py`
and their docs; MCS's station code, smoke test and docs. Additive interface only — new
`/blueboat/run_command`, `/blueboat/run_state`, `/blueboat/run_log`,
`/blueboat/arrow_thrust`, parameters `session_mode`, `arrow_timeout` and launch argument
`session_mode` (default `False`, so the CLI and `Sim_launch.py` keep their behaviour);
nothing renamed or retyped (§4.1). **Also on 2026-10-09 the user opened both modules for the
sea-state follow-ups** ("if there's anything you need to update in control or mcs, you can do
it"): Control's `simulation_interface.py` re-publishes `/blueboat/controller_ready` every 1 s
like `robot_interface` (QoS unchanged); MCS's `launch_manager.companion_command` starts the
sea companion for every empty-world launch, a null sea included, and the SEA STATE box flags
a run on Gazebo's box hull (`mcs/core/sea.py`, `gui/sea_state_box.py`, smoke test, docs). No
interface changed. **On 2026-10-12 the user ordered a Rotation slider in MCS's ARROW CONTROL box**
(3–15 N, default 5; Power default 10 N): `gui/arrow_box.py`, `config/settings.py`, the
`core/arrows.py` docstring, the smoke test and the user guide. No interface changed — the
stream still carries the composed `[right, left]`. **On 2026-10-13 the user ordered v1.1 in both
modules: run bags and bag replay.** Every real-robot run also records a ros2bag of every
non-SSS topic, filed into its `Robot_data/<stem>/` folder (`robot_interface` + the ROS-free
`run_bag.py`: a separate `ros2 bag record` process, pre-armed paused between runs, resumed at
run start); and MCS's Gazebo launch gains Source **"From a ros2bag"** → Control's new
`Replay_launch.py` / `bag_replay` node: the boat moves **kinematically** along the recording
(the force-free `blueboat_description replay:=true` description — no hydrodynamics, collision,
gravity or thrusters, velocity pinned to zero — so sea state, wind and current cannot move it),
in the empty world or a GPS-anchored built world (read-only: `world.sdf` + `metadata.yaml`).
Additive interface only (§4.1): `/replay/state`, `/replay/command`, the `/replay/<name>`
namespace, `robot_interface` parameters `record_bag` / `trajectory`, launch argument
`record_bag` (default `True`, session runs only) and three additive `/blueboat/run_log` fields.
Nothing renamed or retyped; BlueBoat-SSS-Sim untouched. **On 2026-10-14 the user ordered the
link guardian in both modules (MCS v1.1):** Control's `robot_interface` arms the autopilot at
session connection *before* going to override (MANUAL → `default` → arm → `override`; a failed
arm never blocks the session) and gains the `input_str` token `rearm` and parameters
`arm_on_connect` / `arm_timeout` / `arm_default_timeout` (interface baseline re-taken); MCS
gains the GUARDIAN box (top of the left column), starts `guardian.py watch` with every
real-robot launch, asks at Turn Off Connection / exit whether to turn the guardian off and
disarm, moves LAYERS to the right column above MAP TOOLS and drops the robot heading arrow.
Additive interface only: `/link_guardian/status`, `/link_guardian/command`, the `rearm` token.

---

## 4. Cross-module interface contract

Where two modules state different values for one thing, both appear in the row — the
disagreement is itself a cross-module fact, resolved in the named module's `TODO.md`. Names
are **absolute** in the source: `master_control` is constructed with `namespace='blueboat'`,
but ROS 2 does not namespace absolute names (`ctrlCLAUDE.md` §2).

### 4.1 Vehicle and control

QoS is `default` for every row unless the notes say otherwise (`/blueboat/odom`: `default 10`).

| Name | Type | Producer → Consumers | Notes |
|---|---|---|---|
| `/blueboat/odom` | `nav_msgs/Odometry` | `robot_interface` (real) · Gazebo bridge (sim, `odom_topic` param) · `bag_replay` (bag replay: the recorded `/mavros/local_position/odom` with its **full** attitude and body twist, in the replay world frame) → `master_control`, `sss_processor_node`, `sss_sim_node`, GCS, MCS | **Both local ENU since 2026-08-31; only the origin differs.** Real: origin = boat at launch, yaw **absolute ENU**. Sim: Gazebo ENU, no re-zeroing. Documents describing a launch-relative yaw predate the fix. `sssTODO.md`: this topic reads zero in real-robot runs. |
| `/blueboat/pinger_coordinates` | `std_msgs/Float32MultiArray` `[x, y, z]` | `robot_interface` → `master_control`, GCS, MCS | **Body/vehicle frame, three values**: Water Linked *filtered* (`filaco`) x/y/z, dead-reckoned at odom rate between USBL fixes. `master_control` reads `[:2]` in `PID`, passes all three to `solve_LoS` in `LoS`; a consumer assuming length 2 reads a length-3 array. The 2-element **world-frame** `corrected_pinger` goes out here only under `robot_interface`'s `fixed_pinger`, hard-coded `False`, settable from no parameter or topic. GCS default `alignment.pinger_frame: robot`. |
| `/blueboat/controller_ready` | `std_msgs/Bool` | `robot_interface` (real) · `simulation_interface` (sim) → `master_control`, MCS; also the **E-STOP acknowledgement** (`False` on latch) | **QoS producer-dependent:** real default depth 10 VOLATILE, sim latched (TRANSIENT_LOCAL). Both consumers subscribe volatile depth 10, compatible with either, so neither end may be "fixed" to match the other (CM-4). Late subscribers are covered by **both** producers' periodic re-publish (`ready_republish_period = 1.0` s; `simulation_interface` since 2026-10-09, when its latched one-shot left a late `master_control` waiting forever), not durability — one-shot handshakes race DDS discovery. |
| `/thruster_input` | `std_msgs/Float32MultiArray` | `master_control` → `robot_interface`, `simulation_interface`, MCS | **`[right, left]`**, Newtons — traced end to end in `ctrlCLAUDE.md` §5; the only open link (`git -C BlueBoat-Control show d64ac71^:.claude/TODO.md` §2) is whether ArduPilot's `SERVO1` is physically the right thruster. **Never silent while `master_control` runs**: every early return publishes `[0, 0]`; both interface nodes zero thrust after `thruster_input_timeout` (0.5 s) of silence. |
| `/controller_target` | `std_msgs/Float32MultiArray` | `master_control` → `robot_interface` | Deliberately **body-frame** for the pinger case; not to be unified with `/monitoring_data` — different signals (`ctrlCLAUDE.md` N9). |
| `/monitoring_data` | `std_msgs/Float32MultiArray` | `master_control` → `robot_interface`, MCS | `[t, x, y, psi, x_d, y_d, psi_d, u1, u2]`; `x_d/y_d/psi_d` **world-frame in every branch** (`--- world-frame monitoring target ---` markers, five capture sites in `master_control.py`), so the residual risk is a stale `~/ros2_ws/install`. **20 Hz** (MCS `DiagnosticsConfig.expected_hz` assumes it). ⚠ `self.dt` is hardcoded `0.05` in Control's committed SHA but the launch parameter `control_dt` (default 0.05) in its working tree; which one a real-robot run used depends on the last build into `~/ros2_ws/install` — the repository cannot tell. |
| `/blueboat/input_str` | `std_msgs/String` | MCS `command_center`, operator CLI → **`robot_interface` only** | `enable`, `disable`, `stop`, `override`, `default`, `arm`, `disarm`, `rearm` (session only, 2026-10-14: `default` → arm → `override`), `move <l> <r> <s>`. `arm` works only in `default` (ArduPilot refuses on passthrough). MCS publishes `rearm` (GUARDIAN box) and `disarm` (Turn Off choice). Neither `param_set` nor `master_control` subscribes; `robot_interface` translates `override`/`default` onto `/blueboat/param_str`. An unrecognised first token falls through to the move handler (needs exactly four fields); an empty message is ignored. `stop` **latches** (CM-15 corollary); only `enable` clears it (MCS **Release E-STOP**, run session with motors enabled). |
| `/blueboat/manual_target` | `std_msgs/Float32MultiArray` `[x, y]` | MCS, GCS visualisation app → `master_control` | **World frame.** `[0.0, 0.0]` = resume-original-mission sentinel, not a coordinate; a genuine origin click is nudged by `1e-3`. Any manual target also releases arrow control (the MCS "hold where released" publishes the boat's own position). |
| `/blueboat/arrow_thrust` | `std_msgs/Float32MultiArray` `[right, left]` N, or `[]` | MCS (ARROW CONTROL box) → `master_control` | 20 Hz while on, `[]` releases. Highest-priority branch in **every** mode (sim included): goes out through `publish_thrust`, freezes τ like a manual target, logs the last registered target; a gap > `arrow_timeout` (0.5 s) commands zero and **stays** in arrow control. Since 2026-10-09. |
| `/blueboat/run_command` | `std_msgs/String` (JSON) | MCS → `master_control` | **Real-robot run session only** (`session_mode:=true`, every station launch since 2026-10-09). `configure` {controller_type, use_pinger, note, mission} / `start` / `stop`, each with a `seq`. Schema: `BlueBoat-Control/.claude/CLAUDE.md` §2.3. |
| `/blueboat/run_state` | `std_msgs/String` (JSON) | `master_control` → `robot_interface`, MCS | **Run session only.** `seq`/`ok`/`detail` answer the last command; `state` idle / loading / running / error; heartbeated 1 Hz. `robot_interface` opens and closes each run's CSV from it. |
| `/blueboat/run_log` | `std_msgs/String` (JSON) | `robot_interface` → MCS | **Run session only.** The run's CSV and whether it is being written; heartbeated 1 Hz. Additive since v1.1 (2026-10-13): `bag_enabled`, `bag_recording`, `bag` (staging dir while recording, else the last run's filed bag) — MCS's RUN box "Bag" row; a pre-v1.1 producer sends none. |
| `/replay/state` | `std_msgs/String` (JSON) | `bag_replay` → MCS (REPLAY box) | **Bag replay only, TRANSIENT_LOCAL depth 1**, 2 Hz: `{bag, t, duration, rate, paused, finished, frame: empty\|anchored, world, world_offset, pose_source, gazebo}`. |
| `/replay/command` | `std_msgs/String` (JSON) | MCS → `bag_replay` | **Bag replay only.** `{"cmd": "pause"\|"resume"}` / `{"cmd": "rate", "rate": x}` (0.01–50). |
| `/replay/<recorded name>` | as recorded | `bag_replay` → offline analysis | **Bag replay only.** Every recorded topic that is a command or session plumbing (`input_str`, `manual_target`, `arrow_thrust`, `run_*`, `param_*`, `controller_ready`, `/mavros/rc/override`, the raw `/blueboat/odom`) is republished under this prefix — never on its live name, so no consumer acts on it. Telemetry keeps its live name: every other `/mavros/*`, `/thruster_input`, `/controller_target`, `/blueboat/pinger_coordinates`, `/uw_gps_data`; `/monitoring_data` shifted into the replay world frame. Every `header.stamp` is rewritten to the replay's time; the bag's receive times are the timing truth (on the real launch simple_launch gives mavros `use_sim_time:=True` with no `/clock`, so recorded mavros stamps may read 0). |
| `/link_guardian/status` | `std_msgs/String` (JSON) | `guardian.py watch` (superproject `link_guardian/`, started by MCS for every real-robot launch) → MCS (GUARDIAN box) | **Real-robot session only**, 1 Hz: `{connected, armed, mode, want_on, guardian_on, check, home, run_running, messages, busy, ack}`. Since 2026-10-14. |
| `/link_guardian/command` | `std_msgs/String` (JSON) | MCS → `guardian.py watch` | `{cmd: on\|off\|check\|setup\|reclaim, seq}`, answered in the status's `ack`. `on`/`off` set the autopilot's `LGRD_ON`; `reclaim` = HOLD → `param_set`'s servo mapping → MANUAL. |
| `/blueboat/param_str` | `std_msgs/String` | `robot_interface` → `param_set` | |
| `/blueboat/param_ready` | `std_msgs/Bool` | `param_set` → `robot_interface` | Republished periodically. |
| `/blueboat/param_mode` | `std_msgs/String` | `param_set` → `robot_interface`, MCS | `'default'` / `'override'`, or `''` = "alive, no mode locked"; heartbeated at 1 Hz, unconditionally. A repeat is *state*, not an acknowledgement: MCS safe-shutdown requires a **transition** into `default`; `robot_interface`'s `mode_callback` / `param_callback` are edge-triggered. |
| `/uw_gps_data` | `std_msgs/Float32MultiArray` | `uwgps_log` → `robot_interface`, MCS | 19 values: date(7), aco xyz, ant xyz, lat/lon/dep, filaco xyz. |
| `/pose_arrow` | `visualization_msgs/Marker` | `master_control` → RViz / Gazebo | Debug only. |
| `/current` | `geometry_msgs/Vector3` | `sea_state_node` (sim) → ros_gz bridge → gz `/ocean_current` → the boat's `Hydrodynamics` plugin | World-frame water velocity **at the boat**: the configured mean current + its smooth, bounded, seeded variation in time (exactly sampled Gauss-Markov) and space (weak eddies) + wave orbital velocity — a pure function of seed, sim time and position since 2026-10-08; exact zeros under the null preset. Bridged by `world_launch.py` and `full_mission_launch.py`. |
| `/world/<w>/wrench`, `/world/<w>/wrench/clear` | `ros_gz_interfaces/EntityWrench`, `/Entity` | `sea_state_node` → ros_gz bridge → gz `ApplyLinkWrench` (injected at run time when the world lacks it — BlueBoat-Control's stock `ocean`; detected by the system's own `/wrench/persistent`, since the bridge itself advertises `/wrench`) | One-shot hull wrench per physics step on model `blueboat`: since 2026-10-09 the catamaran hydrostatics in **every** run (calm too — one hull model in every scenario; MCS starts the companion for every empty-world run) plus the wave excitation; `hull.hydrostatics: gazebo_box_when_calm` restores the old "nothing while calm". |
| `/sim/sea_state/boat_pose` | `geometry_msgs/TransformStamped` | ros_gz bridge in `sea_state_launch.py` (from gz `/model/blueboat/pose`, `blueboat_description`'s own `PosePublisher`) → `sea_state_node`, `sss_sim_node` | **Simulation-only, additive** (2026-10-09): the boat's pose every physics step (100 Hz), sim-time stamped — what the hull wrench and the sonar use; the 20 Hz `/blueboat/odom` is their fallback. |
| `/sim/sea_state` | `std_msgs/String` (JSON) | `sea_state_node` → MCS (SEA STATE box) | **TRANSIENT_LOCAL, depth 1**, 2 Hz. Schema: `BlueBoat-SSS-Sim/blueboat_sss_sim/docs/topics.md`. Additive since 2026-10-08: the current's variation, the waves' crest/wakes, and `boat{roll/pitch/heave std}` over 30 s (MCS "Boat motion" row). |
| `/sim/sea_state/command` | `std_msgs/String` (JSON) | MCS ("Change sea state…") → `sea_state_node` | `{current, waves, ramp_s}` or `{schedule, t0}`; the node ramps, never steps. Plain-language keys since 2026-10-08 (current `variation`; waves `tp_s: auto`, `crest`, `wakes`; keyframe `ramp_s`) are resolved **by the simulator** (`sea/presets.py`); MCS sends them and now launches every sea as a `sea_schedule:=` scenario file. |
| `/set_path` | `nav_msgs/Path` | `path_publisher` (`blueboat_control`) · `bag_replay` (the run's `-path.yaml` snapshot, every 5 s) → GCS, RViz | Published under the *relative* name `set_path` in the root namespace, re-requesting the whole path every `refresh_period` (5 s). Started by `Sim_launch.py` and the simulator's `full_mission_launch.py`, **not** `BlueBoat_launch.py` — no `/set_path` in a real-robot run. **Truncates** to its `/path_request` window (`total_time`, default 1000 s). So the GCS prefers the station's deployed trajectory (`blueboat_gcs/core/deployed_path.py`: newest `~/.config/blueboat_mcs/trajectories/.deployed/*.yaml`, placed through the designer file's `geo_anchor`) and falls back to this topic — a file-mediated read of an MCS artifact, not a new wire contract. |

### 4.2 Path service

**`/path_request`** (`blueboat_interfaces/srv/RequestPath`: `std_msgs/Float32MultiArray
path_request` / `---` / `nav_msgs/Path path`). Server: `path_generation` (`blueboat_control`)
— **the only one**; **exactly one server may run** (simulated missions ride the same
`from_yaml` branch). Clients: `master_control`, `path_publisher`, the two standalone
`mpc_control` nodes, MCS. Request = an array of path-parameter values (deliberately
parameter-agnostic); response `frame_id: "world"`, one pose per value. `master_control` asks
`linspace(tau, tau + path_time, path_steps)`; `path_publisher` a *time window*
`[0, total_time]`, so `full_mission_launch` sets `total_time` from the bundle's stored
`duration_s`.

### 4.3 Sonar acquisition

Real `sss_node.py` and simulated `sss_sim_node` share node name `side_scan_sonar`, so private
topics resolve identically and downstream runs unmodified against either (**VERIFIED** in
both).

| Name | Type | Producer → Consumers | QoS | Notes |
|---|---|---|---|---|
| `/side_scan_sonar/{port,starboard}/profile` | `blueboat_interfaces/OmniscanProfile` | `sss_node` · `sss_sim_node` → `sss_processor_node`; GCS (BEST_EFFORT, depth 200, raw bins joined to `/sss_processor/processed` rows by `ping_number`) | BEST_EFFORT, KEEP_LAST, **10** | **`pwr_results` is `uint16[]` — settled** from the only definition, `BlueBoat-Control/blueboat_interfaces/msg/OmniscanProfile.msg` (CM-1); the sim's documentation-only copy `msg_reference/OmniscanProfile.msg` matches field for field, but its "linear echo power" comment is wrong. Field list guarded by `BlueBoat-Control/.claude/tools/interface_baseline.json`. **Normalised per ping, not absolute counts**: invert with `db = min_pwr_db + raw/65535·(max_pwr_db − min_pwr_db)` (`sss_helper.scale_to_db`). Every field ping has exactly one bin at 65535, minimum 0, span clamped at 90 dB (68 948 / 68 948 Shiraishi-jima pings); the sim emits the same. Stacking raw arrays from different pings into a waterfall without converting to dB is wrong at either end. |
| `/side_scan_sonar/{port,starboard}/raw` | `std_msgs/UInt8MultiArray` | same → `sss_processor_node` only (the GCS subscribes `~/profile`, not this) | BEST_EFFORT, KEEP_LAST, 10 | Already-framed Cerulean Ping Protocol packet (msg_id 2198), republished verbatim; length `8 + 52 + 2·num_results + 2`. The processor rebuilds `.svlog` from it; disabling it produces empty logs. |
| `/side_scan_sonar/ping/enable` | `std_msgs/Bool` | GCS, operator, launch one-shot → `sss_node`, `sss_sim_node` | default 10 | Pinging **off at startup in both**; the sim re-reads run-dependent parameters on every enable. The message is volatile: the GCS sends `true` at START once a subscriber is matched (≤ 10 s, then anyway with a warning). The GCS **Sonar** selector refuses to start `sss_node.py` beside a running simulator or driver (one `/side_scan_sonar` only). |
| `/side_scan_sonar/ground_truth/contacts` | `std_msgs/String` (JSON) | `sss_sim_node` → offline analysis (`mission_metrics --source jsonl` on a dump) | default 10 | **Simulation-only, additive.** Schema: `BlueBoat-SSS-Sim/blueboat_sss_sim/docs/topics.md`. `ghost`/`via` mark a multipath image of the same `object_id` — aggregate on `(object_id, via)`; both default to direct when absent. `shadow_bins` and `visible` are read off the rendered visibility mask (a training label measures the image), so a consumer using them as a flat-bottom *height* estimator must invert the geometry itself. |
| `/side_scan_sonar/ground_truth/sensor` | `std_msgs/String` (JSON) | `sss_sim_node` → offline analysis (`analysis/sea_validation.py`, the Gazebo sea gate) | default 10 | **Simulation-only, additive** (2026-10-08). Every ping cycle: the vehicle pose at the ping time and the transducer pose each side was rendered from (the lever arm rotated by the full attitude). Schema: `BlueBoat-SSS-Sim/blueboat_sss_sim/docs/topics.md`. |
| `/sss_processor/processed` | `blueboat_interfaces/ProcessedSSSPing` | `sss_processor_node` → GCS | BEST_EFFORT, depth **200** at the GCS | Slant-range corrected, water column removed; sign of `*_y` = side (**+y port, −y starboard**). |
| `/sss_processor/log/enable` | `std_msgs/Bool` | GCS (Record ON/OFF) → `sss_processor_node` | default | |
| `/sss_ai/seabed_analysis` | `std_msgs/String` (JSON, schema 1) | GCS → *(no consumer in the current tree)* | default | Image metadata + detections, **never pixels**. |
| `/sss_ai/detections` | `vision_msgs/Detection2DArray` | *(none)* → GCS | default | Placeholder, not wired to a model — the wire slot a detector would occupy. |
| `/rosout` | `rcl_interfaces/Log` | all nodes → GCS embedded console | default | The GCS matches the literal string `sss_processor_node` to sweep orphan processes on STOP, so that executable name and its `output='screen'` are load-bearing. |

**Acquisition parameters** (`range_start_mm`, `range_length_mm`, `msec_per_ping`,
`gain_index`, `num_results`, `pulse_len_percent`): identical names, semantics **and defaults**
real = sim since 2026-09-28 (range start 0, free run); the sim's smoke test reads the real
driver's source and asserts the equality.

| Parameter | Default (sim = real) | `project_synthesis.md` §8.5 reserved |
|---|---|---|
| `range_length_mm` | 20000 (sized from water depth, `sssCLAUDE.md` NC #5) | 30 m coverage pass / 15 m revisit pass |
| `gain_index` | −1 (device auto) | — |
| `num_results` | 1200 (the device maximum) | — |
| `pulse_len_percent` | 0.00125 | — |

The device's **best range resolution** (owner's decision, 2026-09-28): the transmit pulse
stays on its measured 44.3 µs floor to ~27 m. The sim's smoke gates keep measuring at the
calibration acquisition (600 / 0.002 / gain 4); §8.5's passes are passed explicitly per run.
`config/fault_injection_sonar.yaml` is **test-only** (CM-2 corollary) — never a calibration or
comparison run. `gain_index: -1` is a command-only sentinel: `OmniscanProfile.gain_index` is
`uint16`, so the device reports the concrete index its auto-gain resolved, and the sim (no AGC)
its calibrated 4. Profile resolution and details: `simCLAUDE.md` §3.1.

**Sim acoustic-model revisions invalidate older comparisons against simulated recordings**
(nothing on the wire changed — CM-1, CM-2): 2026-09-18 re-calibration (absolute levels),
2026-09-19 image formation re-derived (object level), 2026-09-28 objects rendered from material
physics (object level; older worlds are reported stale on load until rebuilt). A legacy
bundle's frozen `sonar.yaml` still renders with its frozen constants. No per-object
brightness, ever. Evidence: `simCLAUDE.md` NC #4/#6/#15/#17,
`BlueBoat-SSS-Sim/blueboat_sss_sim/docs/sonar_model.md`.

**Transducer lateral offset — disagreement:** `mount_y_abs_m: 0.20` in the sim,
`TRANSDUCER_Y_OFFSET_PORT_M / _STBD_M = 0.0` in `sss_processor_node.py`; `simTODO.md` [P1].

**Ping rate — VERIFIED on the corpus:** device period `max(50 ms, 2R/c + ~3 ms)` (the spec
sheet's "20 pings/s up to 30 m"); the sim's `ping_period_s` implements exactly that. Compare
sim and real ping counts at the same `range_length_mm`.

**Ping assembly.** Both stacks key rows on `ping_number` and emit one-sided rows; neither
pairs by arrival time or withholds a ping while the bottom tracker bootstraps (`sssCLAUDE.md`
NC #2). The processor re-bases on a counter restart (a key ≥ 128 behind the newest seen =
device or sim relaunched under a running processor) and judges "stream stopped" by the wall
clock against the last arrival only, never wall time against a message stamp (sonar stamps are
sim time under Gazebo). Processor and GCS warn when > 25 % of recent rows are one-sided.
`ProcessedSSSPing.msg`'s "10-ping bootstrap" header comment is stale; contract unaffected. The
sim's same-tick rule (`simCLAUDE.md` NC #3) is no longer load-bearing for the processor; it
stays the sim's own rule until `BlueBoat-SSS-Sim` chooses to relax it (CM-3).

**Ping counters are per-device.** The two units number pings independently, offset constant
per power-up but arbitrary (**0, −1 and +60 all measured** across the 16 two-sided field logs;
`BlueBoat-SSS/blueboat_gcs/docs/SONARVIEW_SVLOG_ANALYSIS.md` §9.3). Raw `ping_number` is
**not** a shared key across sides — on a +60 log it merges halves acquired up to 3.0 s apart;
any module assembling, replaying or relabelling dual-channel rows must align the counters
first. `port_ping_number` and `starboard_ping_number` in one `ProcessedSSSPing` **legitimately
differ** by that offset; a torn row shows as the gap *changing*, never as it being non-zero.

### 4.4 MAVROS boundary

| Name | Type | Dir | Module |
|---|---|---|---|
| `/mavros/state` | `mavros_msgs/State` | in | `robot_interface`; MCS (only when `mavros_msgs` imports — absent in simulation) |
| `/mavros/imu/data` | `sensor_msgs/Imu` | in | `robot_interface` |
| `/mavros/local_position/odom` | `nav_msgs/Odometry` | in | `robot_interface` |
| `/mavros/global_position/global` | `sensor_msgs/NavSatFix` | in | `robot_interface`, GCS, MCS — **BEST_EFFORT**; `lat==0 and lon==0` = no fix, discarded. In a Gazebo run of a GPS-anchored mission **MCS is the only publisher** (fixes synthesised from sim odom, ~5 Hz, `status` left at **-2 / STATUS_UNKNOWN**), so only `-1` (STATUS_NO_FIX) means no fix — never gate on `status < 0`. In a **bag replay** `bag_replay` is the only publisher: the recorded fixes, unchanged but for the stamp (MCS's SimGps stays disarmed). |
| `/mavros/global_position/compass_hdg` | `std_msgs/Float64` | in | MCS, GCS. Degrees **clockwise from north**; MCS converts `radians(90 - hdg)`. Preferred heading source; odom yaw the fallback |
| `/mavros/rc/override` | `mavros_msgs/OverrideRCIn` | out | `robot_interface` at ~20 Hz, latest-wins |

FCU endpoint = `BlueBoat_launch.py`'s `fcu_url` launch argument (default
`udp://:14550@192.168.2.2:14550`). **Port 14550 collides with a running QGroundControl** →
intermittent launch failures (`mavros_router`:
`link[1000] open failed: DeviceError:udp:bind: Address already in use`); close QGC or pass
`fcu_url:=` with another port.

The sim's `mavros_shim_node` (on by default) republishes `/blueboat/odom` under MAVROS names
for tooling written against them (`simCLAUDE.md` §3.2).

### 4.5 File-level interfaces

The Aug Studio exposes **no ROS interface of any kind** — files and CLI only; several other
handoffs are file-mediated too. The per-artifact contracts (`.svlog`, GCS recording sessions
and seabed images, world folders, YOLO and augmented datasets, `sss_aug_dataset.yaml`,
sea-state presets/timelines, trajectory YAML, position CSVs, mission report folders,
controller `.npy`, the `<root>` data-dir resolution) live in skill `file-interfaces`; load it
before producing, reading, moving or converting any of them. **Before reading, comparing or
decoding a `.svlog`, load skill `svlog`.** Field records are write-once (CM-7); the AI is fed
the seabed pictures plus their JSON metadata, never world-frame crops (CM-10).

### 4.6 Shared conventions

| Convention | Statement |
|---|---|
| Side identity | `channel_number` 0 = port, 1 = starboard, at **byte 34** of the raw framed packet; a `255` channel falls back to the **wrapped** sign of `transducer_heading_deg` (one rule, ported verbatim: `sss_helper.side_from_fields`, `blueboat_gcs.core.svlog.resolve_side`, `blueboat_sss_sim.analysis.svlog_reader._side_from_packet`); a bearing of exactly 0 resolves nothing (processor: arrival topic, counted; GCS: port, counted). **On the wire `transducer_heading_deg` is the mounting angle, constant −90 port / +90 starboard**; `vehicle_heading_deg` carries the compass heading. The sim encodes the same since 2026-09-15 (older sim recordings carry the absolute bearing). Sim body frame: `Side.PORT.sign = +1` (+y body), `STARBOARD = −1`. Processed pings: **+y = port, −y = starboard**. |
| Frames | Sim world **ENU**, z = 0 at the surface, depths negative. Internal math uses ENU yaw; hardware- or user-facing values use compass degrees. MCS: yaw in radians, CCW-positive about +z; map scene in **local east/north metres about the first GPS fix** — north-up, never rotates, gated on the GPS anchor (`BlueBoat-MCS/GPS_MAP_ARCHITECTURE.md`). Real `/blueboat/odom`: local ENU, **absolute** yaw. |
| Frame on the wire | `/blueboat/manual_target` **world**; `/blueboat/pinger_coordinates` and `/controller_target` **body**; `/monitoring_data` **world in every branch**. `master_control` converts the manual target via `inRobotFrame()` before `solve_LoS()` and passes the pinger vector through, so both are robot-frame at the solver — correct by design. |
| MAVROS twist | `/mavros/local_position/odom` has `child_frame_id: base_link`: `twist` is body-frame, `pose` world-frame. `robot_interface` re-expresses **pose** into a boot-relative frame and passes **twist** through untouched. |
| Gazebo generation | ROS 2 **Jazzy** + Gazebo **Harmonic** (Fortress not installed). `blueboat_sss_sim` emits `gz-sim-*` names throughout. `blueboat_description` is still Fortress-named (`ignition-gazebo-*-system`) and loads only through Harmonic's deprecated-name shim, which warns per plugin and is removed in gz-sim 9 — the port is a post-v1.0 item. |
| TF | `project_synthesis.md` §5.2 specifies `map → odom → base_link → sss_link` with lever-arm offsets. **No module publishes or consumes that tree, and no module reads TF at all.** The one TF publisher is the external `pose_to_tf` node that `blueboat_description/launch/upload_rov_launch.py` starts **in simulation only**, emitting a single `world → blueboat/base_link` for RViz. Geometry is handled per-module; the lever-arm point surfaces as the transducer-offset disagreement (§4.3). |

---

## 5. Project-wide non-negotiables

Only genuinely cross-module constraints (a shared boundary, or reached independently by two or
more modules); module-local rules stay in the module.

**CM-1 — Topic, service and parameter signatures are a cross-repo contract.** No module
changes a name or message type unilaterally; refactors change file internals only
(`ctrlCLAUDE.md` N1, `simCLAUDE.md` NC #1; all of §4 depends on it). `blueboat_interfaces` is
the only place a message type is defined; the sim reuses it and puts additional simulation
data on new additive JSON topics (`ground_truth/contacts` is the pattern).

**CM-2 — Simulation and real water expose the identical ROS interface:** names, types, QoS
(BEST_EFFORT / KEEP_LAST / 10 on the sonar topics), parameter names, node names, ping-enable
semantics and, since 2026-09-28, the acquisition defaults (§4.3). One deliberate,
user-ordered exception (2026-10-09): the run-session plumbing (`/blueboat/run_command`,
`/blueboat/run_state`, `/blueboat/run_log`) exists only in a real-robot launch with
`session_mode:=true` — operator/station plumbing, no sensor or perception interface, and
every downstream stack runs unchanged against both graphs. A **bag replay** (v1.1,
`Replay_launch.py`) is neither graph: it plays a recorded real run back (telemetry on its live
names, commands under `/replay/`), so it is evidence about that run, never a simulation result
and never one side of the sim-to-real comparison. Downstream stacks run
unmodified in both; divergence invalidates the sim-to-real comparison the thesis rests on
(`ctrlCLAUDE.md` N2, `simCLAUDE.md` NC #1). **Corollary (2026-09-18): "identical" has to be
*demonstrated*, and a clean simulation cannot** — a stream whose gain never walks, whose
counter never restarts, which never reports `channel_number: 255` or drops a ping leaves four
downstream paths untaken (the processor's gain compensation stuck at `g = 0`, its counter
re-base and the CM-5 side fallback never entered, CM-6's one-sided rows never occurring). So
the sim ships `config/fault_injection_sonar.yaml` (all knobs off by default), putting all five
on the wire, each reproducing something the corpus shows; running the real stack against it
once turns CM-2 from a claim into a test.

**CM-3 — No module modifies a neighbour's package.** Integration happens by serving identical
interfaces (`simCLAUDE.md` NC #8, `mcsCLAUDE.md` N9, `ctrlCLAUDE.md` N1). **No exception
remains:** no source file is owned by two submodules (§2).

**CM-4 — QoS is changed at both ends or not at all.** A `RELIABLE` subscriber against a
`BEST_EFFORT` publisher receives *nothing* (`sssCLAUDE.md` NC #4); a non-latched subscriber
against `TRANSIENT_LOCAL` never sees a sample published before it matched, so a latched
one-shot `/blueboat/controller_ready` was missed — the latched-readiness row of §4.1 is the
second instance of the same failure mode, closed by re-publishing, not by changing QoS.

**CM-5 — Side identity comes from the packet, never from the topic or the `src` tag:**
`channel_number` at byte 34, falling back to the sign of `transducer_heading_deg`. VERIFIED
against 5250 packets, zero mismatches. Applies to any module consuming raw frames or profiles.

**CM-6 — Never drop a ping.** Rows assemble by `ping_number` **normalised by the per-device
counter offset** (§4.3); one-sided rows are emitted, not discarded; no ping is withheld
because the bottom tracker has not locked (`sssCLAUDE.md` NC #2). Obeyed by
`sss_processor_node` and the GCS replay path; a missing pose is the only sanctioned drop, and
it is BlueBoat-Control's to fix.

**CM-7 — Field data and generated ground truth are write-once.** Recorded `.svlog` files,
position CSVs and controller `.npy` logs are primary field record, never overwritten or
regenerated; mission bundles are immutable snapshots, regenerated rather than edited; the Aug
Studio never modifies an input dataset (`sssCLAUDE.md` NC #6, `ctrlCLAUDE.md` §6,
`simCLAUDE.md` NC #10, `augCLAUDE.md` #1).

**CM-8 — Monitoring output is world-frame in every controller branch, and no consumer
re-applies a frame correction.** The conversion belongs at the source (`ctrlCLAUDE.md` N9,
`mcsCLAUDE.md` N3 — two halves of one rule).

**CM-9 — The belief layer is the only object the replanner reads.** Detector, sensor and
planner changes interact only through it (`project_synthesis.md` §5.1 ⚠, `sssCLAUDE.md` #15).
Nothing in the current tree implements it — §6 D7.

**CM-10 — AI inputs are waterfall-domain and boat-relative, never world-frame mosaic crops:**
world-frame patches distort near turns and make intensity aggregation ambiguous where cells
are revisited (`project_synthesis.md` §5.2 ⚠, `sssCLAUDE.md` #12).

**CM-11 — The headline detector trains on real imagery only.** Synthetic data is for the
policy comparison, the sim-to-real transfer-gap experiment and development; a detector
trained on it would inherit aspect sensitivity from the model rather than measure it
(`project_synthesis.md` §7.6 ⚠, `sssCLAUDE.md` #11, `simCLAUDE.md` NC #11, the Aug Studio's
stated role).

**CM-12 — The policy baseline is two-pass orthogonal, and tuned seriously.** Single-pass is a
strawman; a deliberately weakened baseline is detected instantly and sinks the comparison
(`project_synthesis.md` §7.3 ⚠, §8.6 ⚠, `sssCLAUDE.md` #13, `mcsCLAUDE.md` N10).

**CM-13 — Headline results are stated as model-conditional:** "In a calibrated simulation
environment…", never an unqualified empirical finding, the caveat leading the limitations
chapter rather than buried in it (`project_synthesis.md` §4.1 ⚠, `sssCLAUDE.md` #16,
`mcsCLAUDE.md` N10). The evidence architecture of `project_synthesis.md` §4 governs which
layer may support which claim; no layer is used above its evidential weight.

**CM-14 — Perception, control and AI iteration happen offline against recorded rosbags, never
in the water.** Field time is weather-gated and the scarcest resource; needing a field session
to test a change means the replay tooling has a gap (`project_synthesis.md` §8.6 ⚠,
`ctrlCLAUDE.md` N7, `sssCLAUDE.md` #14).

**CM-15 — Safe shutdown precedes terminating a launch:** publish `default` on
`/blueboat/input_str`, confirm a matched subscriber, wait for the `/blueboat/param_mode` echo,
flush, then terminate (MCS Stop Mission, labelled **Turn Off Connection** in a real-robot
run session, where a run still active is stopped first on `/blueboat/run_command`); killing
the launch first can leave the motors in override (`mcsCLAUDE.md` N1). `ctrlCLAUDE.md` N5 is the control-stack half: the default servo mapping
is restored before shutdown and a SERVO function is never set to `0`. Since 2026-09-04
`robot_interface` and `param_set` also attempt that restore themselves in independent bounded
`try/finally` blocks — best effort (a launch teardown SIGINTs the whole process group, mavros
included), never a replacement for the station's sequence. **Corollary (2026-09-04): stopping
the motors, releasing the servo mapping and ending the mission are three separate operator
actions, never re-nested.** The E-STOP publishes `stop` — `robot_interface` zeroes thrust,
closes the `enable_motors` gate, disarms and **latches** until an explicit `enable` — and
touches neither the parameter mode nor the launch. Leaving override *transfers* authority (the
RC channels go back to whatever else transmits), so it can never be part of a panic button
(`mcsCLAUDE.md` N1b table; `ctrlCLAUDE.md` N4b latch).

**CM-16 — `enable_motors` gates all thruster output, and a closed gate holds neutral.** No
**thrust-bearing** PWM reaches the motors unless `enable_motors:=True`; every
`/mavros/rc/override` write outside the gate carries neutral 1500/1500 or channel release
(`ctrlCLAUDE.md` N4). **Reworded 2026-09-04** from "no code path writes to
`/mavros/rc/override` around that gate", because writing *nothing* was unsafe:
`robot_interface` requests `override` unconditionally at init, so `SERVO1/3_FUNCTION` sit on
RCIN passthrough and the ESCs follow RC channels 1 and 3 from any transmitter, with nothing
feeding ArduPilot's `RC_OVERRIDE_TIME` to keep those channels ours — a silent gate left the
motors drivable by a hand transmitter, a QGC joystick or an RC failsafe. The gate now streams
true neutral (0 N is an exact knot of the calibration table) while in override, pinning the
channels and feeding the watchdog.

---

## 6. Discrepancies against `project_synthesis.md`

Current relational facts. `project_synthesis.md` outranks a module `CLAUDE.md` by convention;
where a module describes something that demonstrably exists and runs, the entry says which
source is the more reliable guide.

**D1 — Where preprocessing runs: resolved 2026-09-28** — on the operator laptop, like every
node (§1.1); anything saying "on the robot" is wrong.

**D2 — SSS ping message schema.** §5.2 specifies a custom two-sided message (`sound_speed`,
`range_max`, `num_samples`, `uint8[] port_intensities`, `uint8[] starboard_intensities`,
`ping_period`). What exists is `blueboat_interfaces/OmniscanProfile`: one-sided, one topic per
side, mirroring the decoded Cerulean header (§4.3). *More reliable:* the modules — the type exists and three
modules consume it; §5.2's schema reads as a pre-implementation sketch. Its *derived* content — the three-step ping→world transform and the slant-range
correction `r_ground = sqrt(r_slant² − h²)` — holds.

**D3 — Maximum ping rate: resolved** — §5.1's 20 Hz is right (§4.3).

**D4 — Continuous world-frame mosaic.** §5.3 ⚠: the world-frame mosaic is generated on demand
or post-mission, not continuously (wasteful, off the critical path); the GCS `MosaicService`
builds one **live** over satellite tiles. *Reconciled:* the ⚠ constrains the **detector's**
input path; the GCS mosaic is an operator display feeding no detector, and CM-10, which
protects the perception pipeline, is not violated. If a detector is ever fed from the mosaic,
the ⚠ binds directly.

**D5 — Range settings.** §8.5 reserves 30 m per side for coverage and 15 m for revisit passes;
`sssCLAUDE.md` NC #5 sets range from water depth (~4× the deepest expected), because 80 m in
shallow water pushed the bottom return to sample 49/600 and broke bottom detection. The
implemented default, 20 m at both ends (§4.3), sits between the reserved values; the rules
agree in the harbour band and can conflict in very shallow water; §8.5 stays authoritative for
what the experiments use. The field went the other way on 2026-09-07: the beach sessions ran
**20 m** at ~1.2 m altitude — what `config/shallow_beach_sonar.yaml` reproduces and the second
calibration corpus is made of. A third rule is thus in evidence — *range follows the altitude
the boat can actually hold* — and the reserved values remain the experiment plan, not a
description of the corpus.

**D6 — TF tree.** §5.2's `map → odom → base_link → sss_link` with lever-arm offsets: **no
module consumes TF and none of those four frames exists** (§4.6 TF); the lever-arm point
surfaces as the transducer-offset disagreement (§4.3).

**D7 — Unimplemented interface boundary.** The detector, belief layer (multi-channel Bayesian
grid: `p_target`, `n_observations`, `aspect_coverage`, `last_intensity`, `max_confidence`),
initial CPP, replanner and mission manager are specified in §5 and correspond to deliverables
D3, D4, D6, D7. No submodule implements them or is designated to own them; the GCS's unwired
`vision_msgs/Detection2DArray` subscription is the only wire slot anticipating any of it.
Detector output schema, belief-grid channels, the three replanner rules (resolution, budget,
abandonment) and the confidence-calibration requirement are governed by `project_synthesis.md`
§5.2, §8.1, §8.2 until a module claims them.

---

## 7. Where the detail lives

The root describes relationships; each submodule stays authoritative for its internals and its
backlog — do not duplicate either here.

| Topic | Read |
|---|---|
| Scope, evidence architecture, headline claim phrasing, design rules | `project_synthesis.md` §§1–4, §8 (project files) |
| Experiment design, target classes, metrics, campaign planning | `project_synthesis.md` §7–§8.4 and `target_families_and_surrogates.md` — **out of scope for this file** |
| Controllers, guidance law, thrust path, trajectory library, MAVROS bridge | `BlueBoat-Control/.claude/CLAUDE.md` · no `TODO.md` since the v1.0 freeze (post-v1.0 items go to the requesting module's `TODO.md`). Deeper, in the package: `blueboat_control/src/TRAJECTORY_SYSTEM.md`, `FIELD_TUNING.md` |
| Sonar driver, processor, `.svlog` format, GCS internals, measured acquisition settings | `BlueBoat-SSS/.claude/CLAUDE.md` · open items `BlueBoat-SSS/.claude/TODO.md` |
| Acoustic model, world generation, mission bundles, renderer seams, smoke test | `BlueBoat-SSS-Sim/.claude/CLAUDE.md` · open items `BlueBoat-SSS-Sim/.claude/TODO.md` |
| Station threading model, map and georeferencing, Pattern Designer | `BlueBoat-MCS/.claude/CLAUDE.md` · no `TODO.md` since the v1.0 freeze |
| Augmentation families, intensity-domain policy, reproducibility contract, extension contract, release gates | `SSS-Dataset-Aug-Studio/.claude/CLAUDE.md` · open items `SSS-Dataset-Aug-Studio/.claude/TODO.md` |
| Per-module test / lint / smoke gates, exact commands, what survives a fresh clone | skill `module-gates` (`.claude/skills/module-gates/SKILL.md`) |

**CLAUDE.md map — read the relevant ones before touching a directory.** A nested `CLAUDE.md`
loads by itself only when the Read tool opens a file in its directory; Bash, Grep and Glob
access never trigger it. So before changing anything under one of these paths (or scripting a
change there), Read its `CLAUDE.md` first:
- module roots: `<module>/.claude/CLAUDE.md`, all five submodules;
- `BlueBoat-Control/`: `blueboat_control/src/` (controller and thrust-path evidence),
  `blueboat_description/`, `log_reviewer/`;
- `BlueBoat-SSS/`: `blueboat_sss/blueboat_gcs/` (GCS);
- `BlueBoat-SSS-Sim/`: `blueboat_sss_sim/blueboat_sss_sim/builder/` (World Builder) and
  `…/sea/` (sea state);
- `BlueBoat-MCS/`: `mcs/designer/` (Pattern Designer).

Each nested file holds that directory's rules and evidence; its module root file states what
moved where.

Where a module's `CLAUDE.md` marks its repo layout UNCERTAIN or its GCS/controller sections
HISTORICAL, the repository outranks the document. Prefer reading a file to trusting a
description of it.

**The two reviews.** `project_review.md` and `sim_review.md` (superproject root, untracked) are
the dated review documents; ~20 source files and several `CLAUDE.md`/`TODO.md` sections cite
them by section — load-bearing, not archive. `sim_review.md` **Part 7** records that its Part 6
update plan was implemented on 2026-09-18, what gates each item, and the two of its own
numbers that did not survive being measured properly. Its measurement chain,
`~/ros2_ws/sim_review_work/`, is **outside every repository** — this machine only, in no
clone. ⚠ **Provenance, not a gate:** its scripts and sonar profiles are frozen at the
pre-2026-09-18 constants, so re-running them against today's model shows large deltas that are
*the fix, not a regression*; the gates are the per-module suites (skill `module-gates`).
