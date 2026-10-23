# CLAUDE.md — BlueBoat Aspect-Aware SSS Survey (superproject)

Root guidance for the superproject carrying six git submodules: **how the modules relate** —
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
        │                                  ├─ BlueBoat-Perception      (detector — dummy today — + image records)
        └── BlueBoat Base Station (WiFi) ──┤  [Belief · Replanner · Evaluation]  planned, not built
            192.168.2.0/24                 └─ SIMULATION: blueboat_sss_sim serves the identical sonar
                                              interface, Gazebo owns hull dynamics
```

**The module chain (owner's decision, 2026-10-20; `project_synthesis.md` §5.1).**

```
sonar module (seabed images + metadata) → Perception → Belief → Replanner → Control
```

- The GCS shows **only Perception's detections** (`/sss_ai/detections`); it runs no detector.
- **Belief** reads **only** Perception's per-image records (`/sss_ai/image_records`) plus the
  mission's survey area and anchor, and sends **only** to the Replanner.
- The **Replanner** reads **only** Belief, acts on its own (simulation and boat alike) and
  generates **every survey type** through Control's live path update (`/blueboat/update_path`,
  §4.1).
- **Belief, Replanner and Evaluation are planned, not built.** No package, node or topic of
  theirs exists. Perception and the link guardian exist; the Aug Studio is optional.
- The Mission Control Station does not use the path update yet; a survey-mission launch mode
  is the planned way (Control `docs/REQUESTS.md` R-1). A built-world simulation cannot yet run
  a replanner-owned run (R-3).
- New modules may own their own interfaces package (CM-1); an existing topic is never renamed
  or retyped.

### 1.1 Deployment — **VERIFIED by the owner, 2026-09-28**

**All** code runs on **this computer** (`~/ros2_ws`): every ROS node (MAVROS,
`robot_interface`, `master_control`, `path_generation`, `uwgps_log`, `sss_node.py`,
`sss_processor_node`, `perception_node`, the simulator), the Mission Control Station and the GCS. It reaches the
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
for `LGRD_NEUTRAL` s (3) it holds the passthrough thrusters at neutral (RC override 1500 —
with no RC receiver ArduPilot otherwise keeps the last laptop command), and after
`LGRD_TIMEOUT` s (5) it switches `SERVO1/3_FUNCTION` from passthrough to 74/73, **arms the
autopilot itself** if needed (ArduPilot refuses to arm on passthrough; first attempt 3.5 s
after the switch, so Rover's disarmed 1 Hz loop has set the ±1000 thruster range), and enters
RTL. Its
laptop companion `link_guardian/laptop/guardian.py` (plain script, not a colcon package) is
started by MCS with every real-robot launch: sets the flag, moves HOME to each run start,
serves MCS's GUARDIAN box over `/link_guardian/status` / `/link_guardian/command`. Design,
setup and test ladder: `link_guardian/README.md`.

| Module | Produces |
|---|---|
| **BlueBoat-Control** | Vehicle motion, pose, thrust, trajectories; per-run ros2bag + kinematic Gazebo replay of a run (v1.1); owns `blueboat_interfaces` — **frozen at tag `v1.0`** (§3), with user-ordered additive changes since (`UpdatePath.srv`, 2026-10-15) |
| **BlueBoat-SSS** — `blueboat_sss` | Sonar acquisition, slant-range correction, bottom tracking, `.svlog` |
| **BlueBoat-SSS** — `blueboat_gcs` | Live mosaic, overlays, recording sessions, seabed images |
| **BlueBoat-MCS** | Mission launch/supervision (incl. "From a ros2bag" replay launches and the link guardian's GUARDIAN box, v1.1), pattern designer, safe shutdown — **frozen at tag `v1.0`** (§3) |
| **BlueBoat-SSS-Sim** | GPS-anchored Gazebo worlds (World Builder GUI over MCS anchored paths) + a drop-in replacement for the real sonar interface + the **sea state** (current/waves into Gazebo, `sea_state_node`) |
| **SSS-Dataset-Aug-Studio** — *optional* | Physics-informed augmentation of YOLO datasets (offline, file-level only); nothing in the chain depends on it |
| **Link guardian** (`link_guardian/`, not a submodule) | Connection-loss guardian: ArduPilot Lua script + laptop companion `guardian.py` (§1.1). Not yet tested on the boat |
| **Belief · Replanner · Evaluation** | **Planned, not built** — the chain above; open requirements `project_synthesis.md` §5.2, §8.1, §8.4 |
| **BlueBoat-Perception** — `blueboat_perception` | **The station's one detection source** (since 2026-10-16): the GCS's seabed images → detector input (`fixed_gray`, a fixed mapping of the raw dB) → detector (the station's former dummy; YOLO an interface stub) → calibration (identity) → `/sss_ai/detections` for the GCS map + one record per image (`/sss_ai/image_records`) for the future belief layer. ROS-free deterministic core, thin node, offline CLI (offline = live, byte-equal records); dataset mode: a YOLO dataset per world run, labelled from the simulator's ground truth (highlight + shadow boxes, the 29 World Builder classes), plus the archival ground-truth bag |

---

## 2. Workspace layout and build order

**VERIFIED.** Each submodule's `.gitmodules` `path` equals its repository name, directly under
the root; the surprise is that two ROS packages sit one level below their git roots: the
simulator's at `BlueBoat-SSS-Sim/blueboat_sss_sim/` and Perception's at
`BlueBoat-Perception/blueboat_perception/`. A `.../BlueBoat-SideScanSonar/blueboat_mcs/`
path in an older document is history.

`~/ros2_ws` is the project's **only** ROS workspace (§1.1). The superproject is checked out at
`~/ros2_ws/src/BlueBoat-SideScanSonar/` and is not itself the colcon workspace; `colcon build`
runs from `~/ros2_ws`. Build `blueboat_interfaces` first — every ROS module's types resolve
there (`OmniscanProfile`, `ProcessedSSSPing`, `RequestPath.srv`, `UpdatePath.srv`); `blueboat_sss_sim` modifies
no other package (`simCLAUDE.md` NC #8). `blueboat_perception` (`ament_python`) uses standard
types only (`std_msgs`, `sensor_msgs`, `vision_msgs`), so it has no build-order constraint;
the GCS imports its ROS-free core lazily for the replay window's Run AI (installed package,
else the superproject checkout), and Perception imports nothing from the GCS. Two submodules are not colcon packages:
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

The six module directories are git **submodules**, each an independent repository; root
`git status` shows a submodule as modified without naming files — inspect inside it.
`.gitmodules` paths are authoritative for the layout.

**Frozen modules (recorded 2026-09-18).** `BlueBoat-Control` and `BlueBoat-MCS` are frozen at
tag `v1.0` (Control `65b15bb`, MCS `790934f`, both on `origin/main`, 2026-09-14). **Sessions do
not edit these two submodules** unless the user explicitly orders it; a needed change becomes a
post-v1.0 item in the requesting module's `TODO.md` or a review's update plan. **Add-only rule
(owner, 2026-10-20):** Control and MCS are updated **by additions only** — a new topic, service,
parameter, launch argument or UI element; nothing proven is renamed, retyped or changed in
behaviour unless the behaviour stays identical *and is shown to be*
(`BlueBoat-Control/test/mc_harness.py --compare HEAD`, MCS's smoke test, the interface
baseline). Every dated owner order is an instance of this rule. The "frozen" statement is the
**2026-09-18 baseline**: the gitlinks have since moved on (2026-10-20: Control `b94dd7b`, MCS
`490f195`), so the trees are no longer identical to the tags. The dated orders (2026-09-28 to
2026-10-16: documentation splits, sea-state UI, run sessions, v1.1 run bags and bag replay,
link guardian, live path update, the Perception companion in MCS) are recorded in skill
`git-history`. BlueBoat-Perception itself (added 2026-10-16) is not frozen.

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
| `/blueboat/odom` | `nav_msgs/Odometry` | `robot_interface` (real) · Gazebo bridge (sim, `odom_topic` param) · `bag_replay` (bag replay: the recorded `/mavros/local_position/odom` with its **full** attitude and body twist, in the replay world frame) → `master_control`, `sss_processor_node`, `sss_sim_node`, GCS, MCS | **Both local ENU since 2026-08-31; only the origin differs.** Real: origin = boat at launch, yaw **absolute ENU**. Sim: Gazebo ENU, no re-zeroing. Documents describing a launch-relative yaw predate the fix. `sssTODO.md`: this topic reads zero in real-robot runs. The GCS takes per-row roll / pitch / yaw rate for the seabed-image metadata from `/mavros/imu/data` (2026-10-16), never from this topic's yaw-only real attitude. |
| `/blueboat/pinger_coordinates` | `std_msgs/Float32MultiArray` `[x, y, z]` | `robot_interface` → `master_control`, GCS, MCS | **Body/vehicle frame, three values**: Water Linked *filtered* (`filaco`) x/y/z, dead-reckoned at odom rate between USBL fixes. `master_control` reads `[:2]` in `PID`, passes all three to `solve_LoS` in `LoS`; a consumer assuming length 2 reads a length-3 array. The 2-element **world-frame** `corrected_pinger` goes out here only under `robot_interface`'s `fixed_pinger`, hard-coded `False`, settable from no parameter or topic. GCS default `alignment.pinger_frame: robot`. |
| `/blueboat/controller_ready` | `std_msgs/Bool` | `robot_interface` (real) · `simulation_interface` (sim) → `master_control`, MCS; also the **E-STOP acknowledgement** (`False` on latch) | **QoS producer-dependent:** real default depth 10 VOLATILE, sim latched (TRANSIENT_LOCAL). Both consumers subscribe volatile depth 10, compatible with either, so neither end may be "fixed" to match the other (CM-4). Late subscribers are covered by **both** producers' periodic re-publish (`ready_republish_period = 1.0` s; `simulation_interface` since 2026-10-09, when its latched one-shot left a late `master_control` waiting forever), not durability — one-shot handshakes race DDS discovery. |
| `/thruster_input` | `std_msgs/Float32MultiArray` | `master_control` → `robot_interface`, `simulation_interface`, MCS | **`[right, left]`**, Newtons — traced end to end in `ctrlCLAUDE.md` §5; the only open link (`git -C BlueBoat-Control show d64ac71^:.claude/TODO.md` §2) is whether ArduPilot's `SERVO1` is physically the right thruster. **Never silent while `master_control` runs**: every early return publishes `[0, 0]`; both interface nodes zero thrust after `thruster_input_timeout` (0.5 s) of silence. |
| `/controller_target` | `std_msgs/Float32MultiArray` | `master_control` → `robot_interface` | Deliberately **body-frame** for the pinger case; not to be unified with `/monitoring_data` — different signals (`ctrlCLAUDE.md` N9). |
| `/monitoring_data` | `std_msgs/Float32MultiArray` | `master_control` → `robot_interface`, MCS | `[t, x, y, psi, x_d, y_d, psi_d, u1, u2]`; `x_d/y_d/psi_d` **world-frame in every branch** (`--- world-frame monitoring target ---` markers, five capture sites in `master_control.py`), so the residual risk is a stale `~/ros2_ws/install`. **20 Hz** (MCS `DiagnosticsConfig.expected_hz` assumes it). ⚠ `self.dt` is hardcoded `0.05` in Control's committed SHA but the launch parameter `control_dt` (default 0.05) in its working tree; which one a real-robot run used depends on the last build into `~/ros2_ws/install` — the repository cannot tell. |
| `/blueboat/input_str` | `std_msgs/String` | MCS `command_center`, operator CLI → **`robot_interface` only** | `enable`, `disable`, `stop`, `override`, `default`, `arm`, `disarm`, `rearm` (session only, 2026-10-14: `default` → arm → `override`), `manual` (2026-10-23, additive: autopilot flight mode → MANUAL), `move <l> <r> <s>`. `arm` works only in `default` (ArduPilot refuses on passthrough). MCS publishes `rearm` (GUARDIAN box), `disarm` (Turn Off choice) and `manual` (Turn Off after *Guardian OFF*, once `default` is confirmed). Neither `param_set` nor `master_control` subscribes; `robot_interface` translates `override`/`default` onto `/blueboat/param_str`. An unrecognised first token falls through to the move handler (needs exactly four fields); an empty message is ignored. `stop` **latches** (CM-15 corollary); only `enable` clears it (MCS **Release E-STOP**, run session with motors enabled). |
| `/blueboat/manual_target` | `std_msgs/Float32MultiArray` `[x, y]` | MCS, GCS visualisation app → `master_control` | **World frame.** `[0.0, 0.0]` = resume-original-mission sentinel, not a coordinate; a genuine origin click is nudged by `1e-3`. Any manual target also releases arrow control (the MCS "hold where released" publishes the boat's own position). |
| `/blueboat/arrow_thrust` | `std_msgs/Float32MultiArray` `[right, left]` N, or `[]` | MCS (ARROW CONTROL box) → `master_control` | 20 Hz while on, `[]` releases. Highest-priority branch in **every** mode (sim included): goes out through `publish_thrust`, freezes τ like a manual target, logs the last registered target; a gap > `arrow_timeout` (0.5 s) commands zero and **stays** in arrow control. Since 2026-10-09. |
| `/blueboat/run_command` | `std_msgs/String` (JSON) | MCS → `master_control` | **Real-robot run session only** (`session_mode:=true`, every station launch since 2026-10-09). `configure` {controller_type, use_pinger, note, mission, optional `path_source` (`mission` \| `replanner`, since 2026-10-15)} / `start` / `stop`, each with a `seq`. Schema: `BlueBoat-Control/.claude/CLAUDE.md` §2.3. |
| `/blueboat/run_state` | `std_msgs/String` (JSON) | `master_control` → `robot_interface`, MCS | **Run session only.** `seq`/`ok`/`detail` answer the last command; `state` idle / loading / running / error; heartbeated 1 Hz. `robot_interface` opens and closes each run's CSV from it. Additive key `path_source` since 2026-10-15. |
| `/blueboat/run_log` | `std_msgs/String` (JSON) | `robot_interface` → MCS | **Run session only.** The run's CSV and whether it is being written; heartbeated 1 Hz. Additive since v1.1 (2026-10-13): `bag_enabled`, `bag_recording`, `bag` (staging dir while recording, else the last run's filed bag) — MCS's RUN box "Bag" row; a pre-v1.1 producer sends none. |
| `/blueboat/update_path` | service `blueboat_interfaces/srv/UpdatePath` | client → `master_control` (every launch, sim and real). Clients today: only Control's tests (`test/path_update_demo.py`, `test/gazebo_path_update.py`); the replanner and an MCS "Replanner mode" are future | **Live path update, 2026-10-15, additive.** Loads the first path of a **replanner-owned** run (`path_source:=replanner`), or replaces its rest from `change_point` on. A fixed-mission or pinger run answers `mission_owned`. Every request gets `ok` or one of 17 codes, and a refusal changes nothing. It never touches safety or operator state (Control N10). Gazebo-verified for PID/LoS/MPC, not on water. Contract: `BlueBoat-Control/docs/PATH_UPDATE_INTERFACE.md`. |
| `/blueboat/path_progress` | `std_msgs/String` (JSON, `blueboat_path_progress/1`) | `master_control` → replanner (future), tests | Default QoS, 10 Hz plus one on every answer or transition, in every launch. Carries τ (the governor's path parameter; never derive wall-clock times from path seconds), the state, the following and active ids, `min_change_point`, the end of the path and the last answer. |
| `/blueboat/path_update_event` | `std_msgs/String` (JSON, `blueboat_path_update_event/1`) | `master_control` → `robot_interface`, `simulation_interface`, the run bag | Reliable, **depth 50**, not heartbeated. One message per answer, activation, end or clear. Logged as the run's `<date>-<note>-pathlog.csv`, created only if the run received a request. |
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
`mpc_control` nodes, MCS, the GCS (`ros/path_listener.py:114`, the planned-path overlay; it
also reads `/path_generation/get_parameters`). Request = an array of path-parameter values (deliberately
parameter-agnostic); response `frame_id: "world"`, one pose per value. `master_control` asks
`linspace(tau, tau + path_time, path_steps)`; `path_publisher` a *time window*
`[0, total_time]`, so `full_mission_launch` sets `total_time` from the bundle's stored
`duration_s`. A replanner-owned run (`path_source:=replanner`, 2026-10-15) never calls
`/path_request`: it holds its own path, fed through the second service, `/blueboat/update_path`
(§4.1).

### 4.3 Sonar acquisition

Real `sss_node.py` and simulated `sss_sim_node` share node name `side_scan_sonar`, so private
topics resolve identically and downstream runs unmodified against either (**VERIFIED** in
both).

| Name | Type | Producer → Consumers | QoS | Notes |
|---|---|---|---|---|
| `/side_scan_sonar/{port,starboard}/profile` | `blueboat_interfaces/OmniscanProfile` | `sss_node` · `sss_sim_node` → `sss_processor_node`; GCS (BEST_EFFORT, depth 200, raw bins joined to `/sss_processor/processed` rows by `ping_number`) | BEST_EFFORT, KEEP_LAST, **10** | **`pwr_results` is `uint16[]` — settled** from the only definition, `BlueBoat-Control/blueboat_interfaces/msg/OmniscanProfile.msg` (CM-1); the sim's documentation-only copy `msg_reference/OmniscanProfile.msg` matches field for field, but its "linear echo power" comment is wrong. Field list guarded by `BlueBoat-Control/.claude/tools/interface_baseline.json`. **Normalised per ping, not absolute counts**: invert with `db = min_pwr_db + raw/65535·(max_pwr_db − min_pwr_db)` (`sss_helper.scale_to_db`). Every field ping has exactly one bin at 65535, minimum 0, span clamped at 90 dB (68 948 / 68 948 Shiraishi-jima pings); the sim emits the same. Stacking raw arrays from different pings into a waterfall without converting to dB is wrong at either end. |
| `/side_scan_sonar/{port,starboard}/raw` | `std_msgs/UInt8MultiArray` | same → `sss_processor_node` only (the GCS subscribes `~/profile`, not this) | BEST_EFFORT, KEEP_LAST, 10 | Already-framed Cerulean Ping Protocol packet (msg_id 2198), republished verbatim; length `8 + 52 + 2·num_results + 2`. The processor rebuilds `.svlog` from it; disabling it produces empty logs. |
| `/side_scan_sonar/ping/enable` | `std_msgs/Bool` | GCS, operator, launch one-shot → `sss_node`, `sss_sim_node` | default 10 | Pinging **off at startup in both**; the sim re-reads run-dependent parameters on every enable. The message is volatile: the GCS sends `true` at START once a subscriber is matched (≤ 10 s, then anyway with a warning). The GCS **Sonar** selector refuses to start `sss_node.py` beside a running simulator or driver (one `/side_scan_sonar` only). |
| `/side_scan_sonar/ground_truth/contacts` | `std_msgs/String` (JSON) | `sss_sim_node` → offline analysis (`mission_metrics --source jsonl` on a dump); BlueBoat-Perception's dataset labels (dataset mode in a world only, since 2026-10-16) | default 10 | **Simulation-only, additive.** Schema: `BlueBoat-SSS-Sim/blueboat_sss_sim/docs/topics.md`. `ghost`/`via` mark a multipath image of the same `object_id` — aggregate on `(object_id, via)`; both default to direct when absent. `shadow_bins` and `visible` are read off the rendered visibility mask (a training label measures the image), so a consumer using them as a flat-bottom *height* estimator must invert the geometry itself. |
| `/side_scan_sonar/ground_truth/sensor` | `std_msgs/String` (JSON) | `sss_sim_node` → offline analysis (`analysis/sea_validation.py`, the Gazebo sea gate); BlueBoat-Perception's dataset labels (dataset mode in a world only) | default 10 | **Simulation-only, additive** (2026-10-08). Every ping cycle: the vehicle pose at the ping time and the transducer pose each side was rendered from (the lever arm rotated by the full attitude). Schema: `BlueBoat-SSS-Sim/blueboat_sss_sim/docs/topics.md`. |
| `/sss_processor/processed` | `blueboat_interfaces/ProcessedSSSPing` | `sss_processor_node` → GCS | BEST_EFFORT, depth **200** at the GCS | Slant-range corrected, water column removed; sign of `*_y` = side (**+y port, −y starboard**). |
| `/sss_processor/log/enable` | `std_msgs/Bool` | GCS (Record ON/OFF) → `sss_processor_node` | default | |
| `/sss_ai/seabed_image` | `sensor_msgs/Image` 32FC1 | GCS → BlueBoat-Perception | RELIABLE, KEEP_LAST 32, VOLATILE (both ends, CM-4) | **Since 2026-10-16.** Every seabed image, recording or not: the raw float dB (= the session's `_world.npz:intensity_db`). `header.frame_id` = the image key `"<stream_id>/<image_id>"`, not a TF frame. Contract: `BlueBoat-Perception/docs/topics.md`. |
| `/sss_ai/seabed_image/png` | `sensor_msgs/Image` mono8 | GCS → BlueBoat-Perception | same | The display PNG, byte-equal to the saved one. |
| `/sss_ai/seabed_image/metadata` | `std_msgs/String` (JSON envelope) | GCS → BlueBoat-Perception | same | The picture metadata (schema 5) in an envelope carrying the key. |
| `/sss_ai/seabed_analysis` | `std_msgs/String` (JSON) | GCS → *(no consumer in the current tree)* | default | Image metadata, **never pixels**. Schema = the picture metadata's: **5 since 2026-10-16** (4 before). `detections` is always `[]`; the detections are on `/sss_ai/detections`. |
| `/sss_ai/detections` | `vision_msgs/Detection2DArray` | **BlueBoat-Perception → GCS** | default (RELIABLE, 10) | **The station's one detection source** (owner's order, 2026-10-16): one array per image, possibly empty. Every map marker, waterfall marker and `detections.csv` row comes from here; the GCS runs no detector. uid = `2_000_000 + 16·image_id + k`, restarting with `image_id` at every START. |
| `/sss_ai/image_records` | `std_msgs/String` (JSON, `blueboat_perception/image_record/1`) | BlueBoat-Perception → *(future belief layer; offline analysis)* | RELIABLE, KEEP_LAST 100 | One per image, with or without detections (`detections: []` = searched, nothing found; `null` = no pixels). Offline over the session = live: byte-equal canonical JSON minus `provenance` / `source`. |
| `/sss_ai/perception/status` | `std_msgs/String` (JSON) | BlueBoat-Perception → operator, tests | RELIABLE, depth 1, TRANSIENT_LOCAL | 1 Hz: join counters (`late_parts`, `gaps`, …), latency, configuration. |
| `/rosout` | `rcl_interfaces/Log` | all nodes → GCS embedded console | default | The GCS matches the literal string `sss_processor_node` to sweep orphan processes on STOP, so that executable name and its `output='screen'` are load-bearing. |

**Acquisition parameters** (`range_start_mm`, `range_length_mm`, `msec_per_ping`,
`gain_index`, `num_results`, `pulse_len_percent`): identical names, semantics **and defaults**
real = sim since 2026-09-28 (range start 0, free run); the sim's smoke test reads the real
driver's source and asserts the equality.

| Parameter | Default (sim = real) | Survey setting (`project_synthesis.md` §8.5) |
|---|---|---|
| `range_length_mm` | 20000 (sized from water depth, `sssCLAUDE.md` NC #5) | **20 m per side for every survey condition** (owner, 2026-10-20) — the default, no override |
| `gain_index` | −1 (device auto) | — |
| `num_results` | 1200 (the device maximum) | — |
| `pulse_len_percent` | 0.00125 | — |

The device's **best range resolution** (owner's decision, 2026-09-28): the transmit pulse
stays on its measured 44.3 µs floor to ~27 m. The sim's smoke gates keep measuring at the
calibration acquisition (600 / 0.002 / gain 4). The old 30 m coverage / 15 m revisit passes are
**no longer part of the plan**; `BlueBoat-SSS-Sim`'s opt-in `config/coverage_pass_sonar.yaml`
(30 m) and the GCS range slider (5–50 m, starts at 20) remain as diagnostic tools only, and the
simulator's `config/enclosed_basin_world.yaml:9` still says "default 15 m range" (stale).
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

**Transducer lateral offset — agreed at 0.285 m** (BR-101447 hull spacing / 2; checked
2026-10-16): `TRANSDUCER_Y_OFFSET_PORT_M / _STBD_M` in `sss_processor_node.py` (since SSS
`994a74b`), mirrored in the GCS's `core/svlog.py`, and `mount_y_abs_m: 0.285` in the
simulator's `config/default_sonar.yaml`. Submersion 0.15 m is an estimate (= the sim's
`sensor_depth_m`); the fore/aft offset is still 0.0, unmeasured. The seabed pictures
georeference with it since 2026-10-16 (georef convention 2, schema 5). `simTODO.md` closed
its old 0.20 / 0.0 disagreement item on 2026-10-19. The simulator's render fixture,
frozen at 0.20 m, was rebaselined that day; re-rendering at 0.20 reproduced it bit for bit.

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

The `/mavros/*` topics and services each node takes from or sends to ArduPilot, the sim's
`mavros_shim_node` republishing and the FCU endpoint are in skill `interface-inventory`.
Gotcha kept here: `BlueBoat_launch.py`'s `fcu_url` default (`udp://:14550@192.168.2.2:14550`)
**collides with a running QGroundControl** (`mavros_router` `udp:bind: Address already in
use`) — close QGC or pass `fcu_url:=` with another port. `/mavros/global_position/global` has
`lat==0 and lon==0` = no fix, and in a stock-world Gazebo run MCS is its only publisher with
`status` -2, so only `-1` means no fix — never gate on `status < 0`. `/mavros/rc/override` is
written only by `robot_interface`.

### 4.5 File-level interfaces

The Aug Studio exposes **no ROS interface of any kind** — files and CLI only; several other
handoffs are file-mediated too. The per-artifact contracts (`.svlog`, GCS recording sessions
and seabed images, world folders, YOLO and augmented datasets, `sss_aug_dataset.yaml`,
sea-state presets/timelines, trajectory YAML, position CSVs, mission report folders,
controller `.npy`, the `<root>` data-dir resolution) live in skill `file-interfaces`; load it
before producing, reading, moving or converting any of them. **Before reading, comparing or
decoding a `.svlog`, load skill `svlog`.** Field records are write-once (CM-7); the AI is fed
the seabed pictures plus their JSON metadata, never world-frame crops (CM-10). Since
2026-10-16 the detector input is BlueBoat-Perception's fixed mapping (`fixed_gray_v1`, its
decision 6.4) of the pictures' **raw dB** and per-row gain, not the display PNG, which stays
the operator picture and the `identity` baseline; CM-10 holds (the same waterfall-domain,
boat-relative grid).

### 4.6 Shared conventions

| Convention | Statement |
|---|---|
| Side identity | `channel_number` 0 = port, 1 = starboard, at **byte 34** of the raw framed packet; a `255` channel falls back to the **wrapped** sign of `transducer_heading_deg` (one rule, ported verbatim: `sss_helper.side_from_fields`, `blueboat_gcs.core.svlog.resolve_side`, `blueboat_sss_sim.analysis.svlog_reader._side_from_packet`); a bearing of exactly 0 resolves nothing (processor: arrival topic, counted; GCS: port, counted). **On the wire `transducer_heading_deg` is the mounting angle, constant −90 port / +90 starboard**; `vehicle_heading_deg` carries the compass heading. The sim encodes the same since 2026-09-15 (older sim recordings carry the absolute bearing). Sim body frame: `Side.PORT.sign = +1` (+y body), `STARBOARD = −1`. Processed pings: **+y = port, −y = starboard**. |
| Frames | Sim world **ENU**, z = 0 at the surface, depths negative. Internal math uses ENU yaw; hardware- or user-facing values use compass degrees. MCS: yaw in radians, CCW-positive about +z; map scene in **local east/north metres about the first GPS fix** — north-up, never rotates, gated on the GPS anchor (`BlueBoat-MCS/GPS_MAP_ARCHITECTURE.md`). Real `/blueboat/odom`: local ENU, **absolute** yaw. |
| Frame on the wire | `/blueboat/manual_target` **world**; `/blueboat/pinger_coordinates` and `/controller_target` **body**; `/monitoring_data` **world in every branch**. `master_control` converts the manual target via `inRobotFrame()` before `solve_LoS()` and passes the pinger vector through, so both are robot-frame at the solver — correct by design. |
| MAVROS twist | `/mavros/local_position/odom` has `child_frame_id: base_link`: `twist` is body-frame, `pose` world-frame. `robot_interface` re-expresses **pose** into a boot-relative frame and passes **twist** through untouched. |
| Gazebo generation | ROS 2 **Jazzy** + Gazebo **Harmonic** (Fortress not installed). `blueboat_sss_sim` emits `gz-sim-*` names throughout. `blueboat_description` is still Fortress-named (`ignition-gazebo-*-system`) and loads only through Harmonic's deprecated-name shim, which warns per plugin and is removed in gz-sim 9 — the port is a post-v1.0 item. |
| TF | `project_synthesis.md` §5.2 specifies `map → odom → base_link → sss_link` with lever-arm offsets. **No module publishes or consumes that tree, and no module reads TF at all.** TF is published **in simulation and bag replay only**, by two things, neither on a real-robot run: the external `pose_to_tf` node that `blueboat_description/launch/upload_rov_launch.py` starts (a single `world → blueboat/base_link` for RViz) and `robot_state_publisher` (`state_publisher_launch.py:22`: `/tf` and `/tf_static` from the URDF). Geometry is handled per-module; the lever-arm point surfaces as the transducer-offset disagreement (§4.3). |

### 4.7 Other served interfaces (added 2026-10-20)

Debug, plumbing and parameter-level names not listed in §4.1–§4.4 (`/sim/sea_state/markers`,
`/side_scan_sonar/set_parameters`, the run bag's `resume` service, the Gazebo bridge topics,
`/clock`, `/tf`, the parameter inventory) are in skill `interface-inventory`. Control's complete
set is the `entries` list of `BlueBoat-Control/.claude/tools/interface_baseline.json`.
There is **no ROS action server and no `/diagnostics` topic** in any module.

---

## 5. Project-wide non-negotiables

Only genuinely cross-module constraints (a shared boundary, or reached independently by two or
more modules); module-local rules stay in the module.

**CM-1 — Topic, service and parameter signatures are a cross-repo contract.** No module
changes a name or message type unilaterally; refactors change file internals only
(`ctrlCLAUDE.md` N1, `simCLAUDE.md` NC #1; all of §4 depends on it). `blueboat_interfaces` is
the only place a *vehicle or sonar* message type is defined; the sim reuses it and puts
additional simulation data on new additive JSON topics (`ground_truth/contacts` is the
pattern). **New modules (Belief, Replanner, Evaluation) may own their own interfaces package**
(owner, 2026-10-20), and BlueBoat-Perception already publishes JSON and standard types only;
what is never allowed is renaming or retyping an existing topic, service or parameter.

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
Belief reads only Perception's per-image records plus the mission's survey area and anchor,
and sends only to the Replanner; the Replanner reads only Belief. Nothing in the current tree
implements either — §6 D7.

**CM-10 — AI inputs are waterfall-domain and boat-relative, never world-frame mosaic crops:**
world-frame patches distort near turns and make intensity aggregation ambiguous where cells
are revisited (`project_synthesis.md` §5.2 ⚠, `sssCLAUDE.md` #12).

**CM-11 — The headline detector is a YOLO model in BlueBoat-Perception, trained on simulated
datasets (Perception's dataset mode), with its confidence calibrated on held-out simulated
worlds** (owner, 2026-10-20; replaces "trains on real imagery only"). Real water validates the
simulator (motion and sensor), runs the heading-response experiment, checks simulator-to-real
conclusions later and serves the final demonstration; a labelled real dataset blocks nothing.
**Consequence to keep stated:** a simulation-trained detector inherits its aspect sensitivity
from the simulator's model, so detector-dependent results stay model-conditional (CM-13) and
the real heading-response experiment is what bounds the simulator. Split and calibrate by
world, never by image (consecutive seabed images overlap 50 %). `project_synthesis.md` §4 E2 /
E7, §7.6, §8.2. The old wording survives in `sssCLAUDE.md` #11, `simCLAUDE.md` NC #11, and
Perception / Aug Studio documents — stale lines listed in the 2026-10-20 report.

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

What "recorded" means in the tree differs by stream. A real run's **run bag** (v1.1) holds
navigation, commands and session plumbing, and **excludes** `/side_scan_sonar/*`,
`/sss_processor/*` and `/sss_ai/*` (`run_bag.py:52`). The sonar's record is the `.svlog`
and the GCS recording session. So:
- control iterates against run bags (`Replay_launch.py`, the log reviewer);
- perception and AI iterate against **GCS sessions**, with `blueboat-perception-offline`,
  which reproduces live records byte for byte;
- `.svlog` files are replayed through the GCS window, whose Run AI uses Perception's core.

`svlog_to_rosbag.py` converts a `.svlog` to a bag, but no tool joins a run bag and a sonar
recording into one replay.

**CM-15 — Safe shutdown precedes terminating a launch:** publish `default` on
`/blueboat/input_str`, confirm a matched subscriber, wait for the `/blueboat/param_mode` echo,
flush, then terminate (MCS Stop Mission, labelled **Turn Off Connection** in a real-robot
run session, where a run still active is stopped first on `/blueboat/run_command`); killing
the launch first can leave the motors in override (`mcsCLAUDE.md` N1). The echo wait outlasts
`param_set`'s own sequence bound (25 s, 2026-10-23), and an unconfirmed `default` is the
operator's call to terminate, never a timer's: torn down mid-sequence, the autopilot keeps
SERVO1/3 on passthrough and its GCS sysid on mavros, and no other ground station can drive it. `ctrlCLAUDE.md` N5 is the control-stack half: the default servo mapping
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

**D5 — Range settings: resolved 2026-10-20.** The owner's decision is **20 m per side for
every survey condition** (§4.3, `project_synthesis.md` §8.5, rewritten): the old 30 m coverage /
15 m revisit passes are gone, and the implemented default is the setting. `sssCLAUDE.md` NC #5
(range from water depth, ~4× the deepest expected, because 80 m in shallow water pushed the
bottom return to sample 49/600 and broke bottom detection) still governs very shallow water.
The beach sessions of 2026-09-07 also ran **20 m** at ~1.2 m altitude (what
`config/shallow_beach_sonar.yaml` reproduces). Leftovers that still say 30 m / 15 m are module
lines or opt-in diagnostics (§4.3).

**D6 — TF tree.** §5.2's `map → odom → base_link → sss_link` with lever-arm offsets: **no
module consumes TF and none of those four frames exists** (§4.6 TF); the lever-arm point
surfaces as the transducer-offset disagreement (§4.3).

**D7 — Interface boundary, partly claimed (2026-10-16; chain re-stated 2026-10-20).** The
detector, the belief layer (multi-channel Bayesian grid: `p_target`, `n_observations`,
`aspect_coverage`, `last_intensity`, `max_confidence`) and the replanner are specified in §5.
Since 2026-10-20 the plan is the chain of §1: sonar module → Perception → Belief → Replanner →
Control, and the §5.1 "initial CPP" and "mission manager" boxes are **folded into the
Replanner**, which generates every survey type through Control's live path update.
**BlueBoat-Perception owns the detector boundary:** `/sss_ai/detections` (the GCS map) and
`/sss_ai/image_records` (one record per image, Belief's input contract,
`BlueBoat-Perception/docs/topics.md` §4). Its detector is still the dummy, the YOLO adapter an
interface stub, and calibration identity (`calibrated: false`, so `confidence` is no
probability — §8.2 ⚠). **Belief, Replanner and Evaluation are planned, not built, and
unowned**; belief-grid channels, the three replanner rules (resolution, budget, abandonment)
and the confidence-calibration requirement are governed by `project_synthesis.md` §5.2, §8.1,
§8.2 until a module claims them. One fact to carry: the image records hold no survey area, no
anchor and no latitude / longitude, so Belief takes those from the mission, as the chain says.

**D8 — Mission swap: resolved 2026-10-20 (recorded 2026-10-19, Control `docs/REQUESTS.md`
R-4).** The old §5.1 had the mission manager perform a "MAVLink mission swap" to ArduPilot. In
the implementation nothing goes to ArduPilot: `master_control` follows the path on the laptop
and streams RC override (Control N6). `project_synthesis.md` §5.1, §5.2, §7.5, §9 D5 now name
Control's live path update (`/blueboat/update_path`, `/blueboat/path_progress`,
`/blueboat/path_update_event`; §4.1) as the mechanism. It is built and tested in Gazebo, **not
on water, and has no client**; MCS does not use it yet (a survey-mission launch mode is the
planned way); built-world simulations cannot yet run replanner-owned runs (Control R-3). The
caller is the Replanner (D7), unbuilt.

**D9 — Detector family and input geometry: resolved 2026-10-20 (recorded 2026-10-19).** The
old §5.1–§5.2 specified a "classical proposer + CNN classifier" on 512 × 512 patches every N
pings at ~1–2 Hz. Decision: **a YOLO model in BlueBoat-Perception**, on the GCS seabed images
as the code has them — 256 rows × 1200–2402 native slant bins, a new image every 128 rows
(~0.1–0.36 Hz measured), raw dB mapped by `fixed_gray_v1`, the adapter to tile across-track and
merge with NMS (`project_synthesis.md` §5.2 describes it). **Not yet built:** the YOLO adapter
is an interface stub that raises on use; no weights, training script, train / validation split
by world or calibrator beyond identity exist (the dataset mode that writes the training data
does). CM-10 holds.

**D10 — "SSS data pipeline: Built, field-validated" (§9 D1; recorded 2026-10-19; synthesis
§9 D1 re-stated 2026-10-20 as built, verified in simulation, field validation partial).** The
pipeline is built and verified live in simulation, but the field validation predates most of
it:
- The corpus holds no field recording made by the current stack. The 2026-09-07 beach logs
  were recorded by Cerulean's SonarLink on BlueOS.
- Only three July harbour logs come from `sss_processor_node`, and they predate the
  September changes: packet-based side identity, counter-offset row assembly, 20 m / 1200
  bins, GPS velocities in `.svlog`, the 0.285 m lever arm and georef convention 2
  (`project_review.md` header; `sssTODO.md` "Needs a real-sonar session", "Needed field
  data").

*More reliable:* the module TODOs. "Field-validated" applies to the July processor and to
offline replays of SonarLink logs, not to the stack as it stands. The "waterfall buffer" of
D1 exists as the GCS's seabed images.

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
| Augmentation families, intensity-domain policy, reproducibility contract, extension contract, release gates (the module is **optional**) | `SSS-Dataset-Aug-Studio/.claude/CLAUDE.md` · open items `SSS-Dataset-Aug-Studio/.claude/TODO.md` |
| Live path update (the Replanner's entry point): contract, refusal codes, tests, first water test | `BlueBoat-Control/docs/PATH_UPDATE_INTERFACE.md`, `PATH_UPDATE_DESIGN.md`, `PATH_UPDATE_REPORT.md`, `PATH_UPDATE_REAL_WATER_TEST.md`; requests `docs/REQUESTS.md` |
| Connection-loss guardian: design, setup, test ladder | `link_guardian/README.md` (superproject) |
| Planned chain (Belief, Replanner, Evaluation) | `project_synthesis.md` §5.1–§5.2, §7.3, §8.1–§8.4 — no module exists |
| Detector pipeline, detector input (fixed mapping, near-range mask, turn flags), image records, dataset mode, offline = live | `BlueBoat-Perception/.claude/CLAUDE.md` · open items `BlueBoat-Perception/.claude/TODO.md`; evidence `docs/PREPROCESSING_STUDY.md`, `docs/LIVE_CHECKS.md` |
| Per-module test / lint / smoke gates, exact commands, what survives a fresh clone | skill `module-gates` (`.claude/skills/module-gates/SKILL.md`) |
| Dated owner orders that opened the frozen Control / MCS (2026-09-28 to 2026-10-16) | skill `git-history` |
| MAVROS boundary table, FCU endpoint, other served interfaces (§4.4, §4.7 detail) | skill `interface-inventory` |

**CLAUDE.md map — read the relevant ones before touching a directory.** A nested `CLAUDE.md`
loads by itself only when the Read tool opens a file in its directory; Bash, Grep and Glob
access never trigger it. So before changing anything under one of these paths (or scripting a
change there), Read its `CLAUDE.md` first:
- module roots: `<module>/.claude/CLAUDE.md`, all six submodules;
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
