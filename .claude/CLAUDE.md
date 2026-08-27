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
| **BlueBoat-SSS-Sim** | either | Synthetic worlds + a drop-in replacement for the real sonar interface |
| **SSS-Dataset-Aug-Studio** | basestation | Physics-informed augmentation of YOLO datasets (offline, file-level only) |

The **belief layer is the only object the replanner reads**; detector, sensor and planner
changes interact only through it (`project_synthesis.md` §5.1 ⚠, echoed as `sssCLAUDE.md`
#15). Nothing in the current tree implements it — see §6, D7.

---

## 2. Workspace layout and build order

**UNCERTAIN — on-disk directory names.** The superproject repository is
`BlueBoat-SideScanSonar` (`sssCLAUDE.md` §13 project repositories; `mcsTODO.md` D1 records
that the MCS tree previously sat at `.../BlueBoat-SideScanSonar/blueboat_mcs/`). The mapping
below is by **repository name**; the actual submodule paths recorded in `.gitmodules` have
not been established here. Read `git submodule status` before relying on any path.

| Submodule repo | Contains | Build system |
|---|---|---|
| `BlueBoat-Control` | ROS 2 packages `blueboat_control`, `blueboat_description`, `blueboat_interfaces` | colcon (ament) |
| `BlueBoat-SSS` | ROS 2 package `blueboat_sss`; standalone app `blueboat_gcs` | colcon for `blueboat_sss`; plain Python for the GCS |
| `BlueBoat-SSS-Sim` | ROS 2 package — resolves as `blueboat_sss_sim` under `ros2 launch`, Python module directory still `blueboat_sss` | colcon (ament_python) |
| `BlueBoat-MCS` | `mcs/`, `integration/`, `docs/`, `run.py`, `smoke_test.py` | standalone Python, no colcon, no `setup.py` |
| `SSS-Dataset-Aug-Studio` | `sss_aug_studio/`, `pyproject.toml`, `tests/`, `docs/` | pip / `pyproject.toml`, Python ≥ 3.10 |

**ROS workspace.** `blueboat_sss_sim` has been launched successfully from `~/ros2_ws`
(**VERIFIED**, `simCLAUDE.md` §7). `ctrlCLAUDE.md`'s README quotes `~/blueboat_ws`;
`mcsTODO.md` B3 tracks that disagreement. Whether the superproject *is* a colcon workspace
or is checked out beneath one is **UNCERTAIN**. Two of the five submodules are not colcon
packages at all, so a workspace-root `colcon build` covers only part of the tree.

**Build and dependency order** (ROS side):

1. `blueboat_interfaces` — every ROS module's message and service types resolve here.
   `OmniscanProfile`, `ProcessedSSSPing`, `RequestPath.srv`.
2. `blueboat_control` + `blueboat_description` — the platform stack and the URDF/world launch
   that `blueboat_sss_sim` includes.
3. `blueboat_sss` and `blueboat_sss_sim` — both additive; `blueboat_sss_sim` modifies no
   other package (`simCLAUDE.md` NC #8).

`blueboat_gcs`, `BlueBoat-MCS` and `SSS-Dataset-Aug-Studio` do not participate in the colcon
build. The GCS and MCS import `rclpy` from a sourced workspace at runtime and both degrade to
a GUI-only mode when it is absent. The Aug Studio has no ROS dependency in any mode.

**Package-name split in the simulator (VERIFIED, current state).** `ros2 launch
blueboat_sss_sim …` resolves; `ros2 run blueboat_sss_sim …` fails with "No executable found",
because the console scripts and the Python module directory are still `blueboat_sss`. Offline
tools run as `python3 -m blueboat_sss.<module>` from the package source root. `simTODO.md`
[P0] holds this.

**Cross-repo file deployment.** `BlueBoat-MCS/integration/` holds patched copies of four
`blueboat_control` nodes (`path_generation.py`, `yaml_trajectory.py`, `master_control.py`,
`robot_interface.py`). They are app-adjacent source that must be copied into
`blueboat_control` on the boat and the workspace rebuilt; nothing under `mcs/` imports them
at runtime (`mcsCLAUDE.md` N9). Several interface guarantees in §4 — world-frame
`/monitoring_data`, the `from_yaml` trajectory branch — hold only where those copies are
deployed. This is the one place in the project where two submodules own the same source file.
`mcsTODO.md` D4 holds the question of where those files should live.

---

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
| `/blueboat/odom` | `nav_msgs/Odometry` | `robot_interface` (real) · Gazebo bridge (sim, `odom_topic` param) | `master_control`, `sss_processor_node`, `sss_sim_node`, GCS, MCS | default 10 | **Disagreement in kind, not name.** Real: pose re-zeroed at `robot_interface`'s first callback — position *and* yaw, so world origin is the boat at launch and world +x is launch heading (`mcsCLAUDE.md` §2). Sim: bridged from Gazebo in ENU with no re-zeroing (`simCLAUDE.md` §8). `sssTODO.md` holds a separate item that this topic reads zero on the real boat. |
| `/blueboat/pinger_coordinates` | `std_msgs/Float32MultiArray` `[x, y]` | `robot_interface` | `master_control`, GCS, MCS | default | **Body/vehicle frame.** GCS default `alignment.pinger_frame: robot`. Seeded from the Waterlinked *filtered* (`filaco`) position, dead-reckoned at odom rate between USBL fixes. |
| `/blueboat/controller_ready` | `std_msgs/Bool` | **Modules disagree:** `robot_interface` per `ctrlCLAUDE.md` §2.2 · `master_control.py` per `mcsCLAUDE.md` §2 | `master_control`, MCS | `depth=1`, **TRANSIENT_LOCAL** (latched) — a non-matching subscriber never receives it | Republished periodically rather than once, because one-shot handshakes race DDS discovery. `mcsTODO.md` E notes the latched QoS is beyond `smoke_test.py`'s reach. |
| `/thruster_input` | `std_msgs/Float32MultiArray` | `master_control` | `robot_interface`, MCS | default | Order is **`[right, left]`** in Newtons. Marked *(provisional)* in `ctrlCLAUDE.md` §5 and never bench-verified per `ctrlTODO.md` §2; stated as fact in `mcsCLAUDE.md`. |
| `/controller_target` | `std_msgs/Float32MultiArray` | `master_control` | `robot_interface` | default | Deliberately **body-frame** for the pinger case. Not to be unified with `/monitoring_data` — different signals (`ctrlCLAUDE.md` N9). |
| `/monitoring_data` | `std_msgs/Float32MultiArray` | `master_control` | `robot_interface`, MCS | default | `[t, x, y, psi, x_d, y_d, psi_d, u1, u2]`. `x_d/y_d/psi_d` are **world-frame in every controller branch** — true only with the patched `master_control` from `BlueBoat-MCS/integration/`. **Rate disagreement:** `dt = 0.05` (20 Hz) in `ctrlCLAUDE.md` §4 *(provisional)*; MCS `DiagnosticsConfig.expected_hz` lists 20.0 while `mcs/docs/03_ros_integration.md` states 1 Hz. `mcsTODO.md` B1 holds it. |
| `/blueboat/input_str` | `std_msgs/String` | MCS `command_center`, operator CLI | `param_set`, `master_control` | default | Values: `enable`, `stop`, `override`, `default`, `arm`, `disarm`, `move <l> <r> <s>`. |
| `/blueboat/manual_target` | `std_msgs/Float32MultiArray` `[x, y]` | MCS, GCS visualisation app | `master_control` | default | **World frame on the wire.** `[0.0, 0.0]` is the resume-original-mission sentinel, not a coordinate; a genuine origin click is nudged by `1e-3`. |
| `/blueboat/param_str` | `std_msgs/String` | `robot_interface` | `param_set` | default | |
| `/blueboat/param_ready` | `std_msgs/Bool` | `param_set` | `robot_interface` | default | Republished periodically. |
| `/blueboat/param_mode` | `std_msgs/String` | `param_set` | `robot_interface`, MCS | default | `'default'` / `'override'`. This echo is what proves an E-STOP landed. |
| `/uw_gps_data` | `std_msgs/Float32MultiArray` | `uwgps_log` | `robot_interface`, MCS | default | 19 values: date(7), aco xyz, ant xyz, lat/lon/dep, filaco xyz. |
| `/pose_arrow` | `visualization_msgs/Marker` | `master_control` | RViz / Gazebo | default | Debug only. |
| `/set_path` | `nav_msgs/Path` | `path_publisher.py` | GCS | default | **Ownership UNCERTAIN.** Referenced by `sssCLAUDE.md` (GCS), `mcsCLAUDE.md` N7 and `simCLAUDE.md` §3.2, but `path_publisher.py` is absent from `ctrlCLAUDE.md` §2.1's node table. MCS N7 records it as started only by `Sim_launch.py`; `full_mission_launch.py` in the simulator also starts it. |

### 4.2 Path service

| Name | Type | Servers | Clients | Notes |
|---|---|---|---|---|
| `/path_request` | `blueboat_interfaces/srv/RequestPath` | `path_generation` (`blueboat_control`) **XOR** `sss_path_generation` (`blueboat_sss_sim`) | `master_control`, `path_publisher`, MCS | **Exactly one server may run.** Request is `Float32MultiArray path_request` — an array of path-parameter values, deliberately parameter-agnostic; response is `nav_msgs/Path`, `frame_id: "world"`, one pose per value. `ctrlTODO.md` §1 records that the `.srv` contents have not been established against the real definition. `master_control` requests `linspace(tau, tau + path_time, path_steps)`; `path_publisher` requests a *time window* `[0, total_time]` with its own default of 120 s, so `full_mission_launch` sets `total_time` from the bundle's stored `duration_s`. |
| `/mission/full_path` | `nav_msgs/Path` | `sss_path_generation` | RViz | **TRANSIENT_LOCAL latched**, published once at startup. Simulation-only, additive. |

### 4.3 Sonar acquisition

The real `sss_node.py` and the simulator's `sss_sim_node` both use node name
`side_scan_sonar`, so private topics resolve identically and downstream runs unmodified
against either. **VERIFIED** in both modules.

| Name | Type | Producer | Consumers | QoS | Notes |
|---|---|---|---|---|---|
| `/side_scan_sonar/{port,starboard}/profile` | `blueboat_interfaces/OmniscanProfile` | `sss_node` (real) · `sss_sim_node` (sim) | `sss_processor_node`, `dataset_recorder_node` (sim) | BEST_EFFORT, KEEP_LAST, **10** | Decoded header including `channel_number`, `transducer_heading_deg`, `ping_number`, `pwr_results`. Marked HISTORICAL in `sssCLAUDE.md`; `simTODO.md` [P1] records that the simulator's reference copy of the `.msg` was reconstructed rather than taken from `blueboat_interfaces`, with `pwr_results` width (`uint16[]` vs `uint32[]`) unestablished. |
| `/side_scan_sonar/{port,starboard}/raw` | `std_msgs/UInt8MultiArray` | `sss_node` · `sss_sim_node` | `sss_processor_node` only — **the GCS does not subscribe** (VERIFIED) | BEST_EFFORT, KEEP_LAST, 10 | Already-framed Cerulean Ping Protocol packet, republished verbatim. Layout: `'B''R' \| u16 payload_len \| u16 msg_id=2198 \| u8 src \| u8 dst \| 52-byte payload \| u16[num_results] \| u16 checksum`. Frame length `8 + 52 + 2·num_results + 2` (1262 B at 600 bins). The processor rebuilds `.svlog` from this; disabling it produces empty logs. |
| `/side_scan_sonar/ping/enable` | `std_msgs/Bool` | GCS (HISTORICAL name), operator, launch one-shot | `sss_node`, `sss_sim_node` | default 10 | Pinging is **off at startup in both**. The simulator re-reads run-dependent parameters on every enable. |
| `/side_scan_sonar/ground_truth/contacts` | `std_msgs/String` (JSON) | `sss_sim_node` | `dataset_recorder_node` | default 10 | **Simulation-only, additive.** Per ping cycle: `{"t_sim", "contacts":[{"side","object_id","type","slant_range_m","extent_bins","shadow_bins","visible","ping_number"}]}`. |
| `/sss_processor/processed` | `blueboat_interfaces/ProcessedSSSPing` | `sss_processor_node` | GCS | BEST_EFFORT, depth **200** at the GCS | Slant-range corrected, water column already removed. Sign of `*_y` encodes side: **+y = port, −y = starboard**. Topic name HISTORICAL. |
| `/sss_processor/log/enable` | `std_msgs/Bool` | GCS (Record ON/OFF) | `sss_processor_node` | default | Name HISTORICAL. |
| `/sss_ai/seabed_analysis` | `std_msgs/String` (JSON, schema 1) | GCS | *(no consumer in the current tree)* | default | Image metadata + detections, **never pixels**. |
| detections topic | `vision_msgs/Detection2DArray` | *(none)* | GCS | default | Placeholder; not wired to a model. This is the wire slot a detector would occupy. |
| `/rosout` | `rcl_interfaces/Log` | all nodes | GCS embedded console | default | The GCS also matches the literal string `sss_processor_node` to sweep orphan processes on STOP, so that executable name and its `output='screen'` are load-bearing. |

**Acquisition parameters** — identical names and semantics across real and simulated nodes
(`range_start_mm`, `range_length_mm`, `msec_per_ping`, `gain_index`, `num_results`,
`pulse_len_percent`), with **three different defaults for the same knob currently in the
tree**:

| Parameter | `blueboat_sss_sim` default | `sss_node.py` default | `SSS_processing_launch.py` default | `project_synthesis.md` §8.5 reserved |
|---|---|---|---|---|
| `range_length_mm` | 15000 | 30000 | 20000 | 30 m coverage pass / 15 m revisit pass |
| `gain_index` | 4 | −1 (device auto) | — | — |

Launching with defaults images a different swath at a different gain in sim than on hardware.
`simTODO.md` [P1] holds this; `sssCLAUDE.md` NC #5 adds an independent constraint that range
be set from water depth (~4× the deepest expected) rather than from the area to cover.

**Transducer lateral offset** — a shared physical value the two modules do not agree on:
`mount_y_abs_m: 0.20` in the simulator, `TRANSDUCER_Y_OFFSET_PORT_M / _STBD_M = 0.0` in
`sss_processor_node.py`. `simTODO.md` [P1] holds it.

**Ping-rate cap** — `max_ping_rate_hz` defaults to 20 in the simulator (`0` disables) to match
the Omniscan 450 spec sheet and `project_synthesis.md` §1; the decoded field capture gives
22 ms per channel at 15 m (≈45 Hz). Both are reproducible through the knob. `simTODO.md` [P2]
holds it.

**Ping pairing** — a live cross-module dependency. `sss_processor_node` currently pairs
port/starboard by arrival time within **50 ms** and drops unmatched pings, which is why
`simCLAUDE.md` NC #3 requires both sides to be published from the same timer tick.
`sssCLAUDE.md` NC #2 states the target behaviour — assemble by `ping_number`, emit one-sided
rows, never withhold a ping while the bottom tracker bootstraps — and `sssTODO.md` records it
as not yet done on the robot side. Until it lands, the simulator's same-tick rule is
load-bearing for both stacks.

### 4.4 MAVROS boundary

| Name | Type | Direction | Module |
|---|---|---|---|
| `/mavros/state` | `mavros_msgs/State` | in | `robot_interface`; MCS (only when `mavros_msgs` imports — absent in simulation) |
| `/mavros/imu/data` | `sensor_msgs/Imu` | in | `robot_interface` |
| `/mavros/local_position/odom` | `nav_msgs/Odometry` | in | `robot_interface` |
| `/mavros/global_position/global` | `sensor_msgs/NavSatFix` | in | `robot_interface`, GCS, MCS — **BEST_EFFORT**; `lat==0 and lon==0` means no fix and is discarded |
| `/mavros/global_position/compass_hdg` | `std_msgs/Float64` | in | MCS, GCS. Degrees **clockwise from north**; MCS converts as `radians(90 - hdg)`. Absolute and available immediately, unlike launch-zeroed odom yaw |
| `/mavros/rc/override` | `mavros_msgs/OverrideRCIn` | out | `robot_interface` at ~20 Hz, latest-wins |

FCU endpoint is hard-coded in the control launch file as `udp://:14550@192.168.2.2:14550`.
**Port 14550 collides with a running QGroundControl**, which surfaces as intermittent launch
failures.

The simulator's optional `mavros_shim_node` republishes `/blueboat/odom` as
`/mavros/global_position/compass_hdg`, `/mavros/imu/data` and `/mavros/local_position/pose`.
It exists for tooling written against MAVROS names — note that it publishes
`local_position/pose` (`PoseStamped`) while `robot_interface` consumes
`local_position/odom` (`Odometry`), and `robot_interface` does not run in simulation anyway.
The sonar interface needs no shim: vehicle heading rides inside every `OmniscanProfile`.

### 4.5 File-level interfaces

The Aug Studio exposes **no ROS interface of any kind**. It integrates through files and CLI
only. Several other handoffs are also file-mediated.

| Artifact | Producer | Consumer(s) | Contract |
|---|---|---|---|
| `.svlog` | `sss_processor_node` (from `~/raw`) | GCS replay window, SonarView | Framed Cerulean Ping Protocol stream; packet ids 10, 12, 150, 2198; device ids port 1, starboard 2, platform 3. Files roll at 500 MB. Recorded files are **primary field data**. |
| Recording session `data_root/sessions/<stamp>/` | GCS | analysis, dataset build | `mosaic/`, `waterfall/` (`waterfall_raw.npz` = the dataset source), `detections/`, `svlog/`, `seabed_images/`, `metadata.json`. Created when Record turns ON; nothing is exported if no session was active. |
| Seabed images `seabed_XXXXX.png` + `_world.npz` | GCS | detector training, Aug Studio | Waterfall domain, boat-relative. 256 rows, stride 128. The `.npz` carries per-pixel `world_x`/`world_y` and the **raw float `intensity_db`**; the PNG is display-normalized for annotation tools. **Train on the `.npz`, not the PNG.** |
| Mission bundle (`world.sdf`, `seabed.stl`, `scene.npz`, `scene_manifest.yaml`, `trajectory.yaml`, `sonar.yaml`, `mission_snapshot.yaml`) | `generate_mission` (sim) | Gazebo, `sss_sim_node`, `sss_path_generation`, labeler | One directory, one seed, **immutable**. `scene.npz` + manifest are the ground truth for every simulation-derived metric the thesis reports. Bundles freeze their own `sonar.yaml` and `trajectory.yaml`, so editing package config does not affect an existing bundle. |
| YOLO dataset (Ultralytics layout) | `dataset_recorder_node` (sim, opt-in via `with_recorder:=true`) · beach labelling pipeline (real) | Aug Studio, detector training | The Aug Studio treats the input directory as **read-only** and writes to a new output directory. |
| `sss_aug_dataset.yaml` | dataset author | Aug Studio | Declares `layout`, `intensity_mapping`, `shadow_included`. **`intensity_mapping` must be declared explicitly.** When absent the Aug Studio assumes `log` (dB waterfall export) and inverts on that basis — which matches the GCS `intensity_db` export but silently mis-inverts a linear dataset. `augTODO.md` holds the audit of existing datasets. |
| Augmented dataset + `generation_manifest.json` + `statistics.md` | `sss-aug-generate` | detector training | Byte-reproducible for a given config + `master_seed`, independent of worker count. |
| Trajectory `<name>.yaml` (`blueboat_trajectory/1`) | MCS Pattern Designer | patched `path_generation` on the boat | Dense `[t, x, y, yaw]` samples + `speed`, `loop`, `length_m`, `duration_s`. Selected through the existing launch argument as `trajectory:=from_yaml:/abs/path.yaml` — no launch-file change. The file is **watched**: the robot holds a station-keeping pose at the origin until it appears, which is what makes deferred GPS-anchored deployment possible. `<name>.meta.yaml` is editor-only and the robot never reads it; `.deployed/<name>.yaml` is regenerated every launch and is not hand-edited. |
| Position/pinger CSV `../../../data/Robot_data/{date}-{note}-poslog.csv` | `robot_interface` | offline analysis | **Raw field record.** Two layouts; `target_*` columns exist only in the no-pinger layout and are correct only with the patched `robot_interface`. Path is relative to the launch working directory. |
| Controller `.npy` `data/{ctrl}_data/…` | `master_control` / `robot_interface` | offline analysis | Schema `['t','x','y','psi','x_d','y_d','psi_d','u1','u2']`, target columns world-frame. Path is relative to the launch working directory; changing it breaks downstream analysis scripts. |

### 4.6 Shared conventions

| Convention | Statement |
|---|---|
| Side identity | `channel_number` 0 = port, 1 = starboard, at **byte 34** of the raw framed packet. Simulator: `Side.PORT.sign = +1` (+y body), `STARBOARD = −1`; transducer heading = vehicle heading ∓ 90°. Processed pings: **+y = port, −y = starboard**. Consistent across modules. |
| Frames | Simulator world is **ENU**, z = 0 at the surface, depths negative. Internal math uses ENU yaw; anything hardware- or user-facing uses compass degrees. MCS: yaw in radians, CCW-positive about +z; the map scene is the raw robot world frame before heading alignment and **local ENU** after. Real `/blueboat/odom` is launch-relative and is *not* an absolute heading. |
| Frame on the wire | `/blueboat/manual_target` is **world**. `/blueboat/pinger_coordinates` and `/controller_target` are **body**. `/monitoring_data` is **world in every branch**. `master_control` converts the manual target via `inRobotFrame()` before `solve_LoS()` and passes the pinger vector through, so both are robot-frame at the solver — that asymmetry is correct by design. |
| MAVROS twist | `/mavros/local_position/odom` has `child_frame_id: base_link`, so `twist` is already body-frame while `pose` is world-frame. `robot_interface` re-expresses **pose** into a boot-relative frame and passes **twist** through untouched. |
| Gazebo generation | `ctrlCLAUDE.md` states ROS 2 **Jazzy** + Gazebo **Harmonic** (`gz-*` plugin names); the simulator's `config/default_mission.yaml` defaults `gazebo_plugin_prefix: ignition` (Fortress). `simTODO.md` [P1] holds it. |
| TF | `project_synthesis.md` §5.2 specifies `map → odom → base_link → sss_link` with lever-arm offsets. No module in the current tree publishes or consumes that tree. |

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
interfaces. Converged: `simCLAUDE.md` NC #8, `mcsCLAUDE.md` N9, `ctrlCLAUDE.md` N1. The
`BlueBoat-MCS/integration/` copies are the single sanctioned exception and are explicitly
marked as robot-side files that are not app runtime.

**CM-4 — QoS is changed at both ends or not at all.** A `RELIABLE` subscriber against a
`BEST_EFFORT` publisher is incompatible and receives *nothing*; a non-latched subscriber
against `TRANSIENT_LOCAL` never sees `/blueboat/controller_ready`. `sssCLAUDE.md` NC #4 states
the first; the latched-readiness row in §4.1 is the second instance of the same failure mode.

**CM-5 — Side identity comes from the packet, never from the topic or the `src` tag.**
`channel_number` at byte 34, falling back to the sign of `transducer_heading_deg`. VERIFIED
against 5250 packets with zero mismatches. Applies to any module that consumes raw frames or
profiles.

**CM-6 — Never drop a ping.** Rows assemble by `ping_number`; one-sided rows are emitted
rather than discarded; no ping is withheld because the bottom tracker has not locked.
`sssCLAUDE.md` NC #2. Its current-state qualification is in §4.3.

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
is restored before shutdown, and a SERVO function is never set to `0`.

**CM-16 — `enable_motors` gates all thruster output.** No PWM reaches the motors unless
`enable_motors:=True`, and no code path writes to `/mavros/rc/override` around that gate.
`ctrlCLAUDE.md` N4.

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
`transducer_heading_deg`, `ping_number`, `pwr_results` (16- or 32-bit, not `uint8`). *More
reliable:* the modules — the message type exists, three modules consume it, and its field
list is marked VERIFIED in `sssCLAUDE.md`. §5.2's schema reads as a pre-implementation design
sketch. The synthesis's *derived* content in the same section — the three-step ping→world
transform and the slant-range correction `r_ground = sqrt(r_slant² − h²)` — is unaffected and
holds.

**D3 — Maximum ping rate.** §5.1 gives 20 Hz for the Omniscan 450. The decoded field capture
gives 22 ms per channel at 15 m. Unresolved in both directions; reproducible either way
through `max_ping_rate_hz`. `simTODO.md` [P2] holds it.

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
offsets matter. No module publishes or consumes a TF tree; geometry is handled per-module
(§4.6). The lever-arm point surfaces instead as the transducer-offset disagreement in §4.3.

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
| Controllers, guidance law, thrust path, trajectory library, MAVROS bridge | `BlueBoat-Control/CLAUDE.md` · open items `BlueBoat-Control/TODO.md` (start at JOB 0) |
| Sonar driver, processor, `.svlog` format, GCS internals, measured acquisition settings | `BlueBoat-SSS/CLAUDE.md` · open items `BlueBoat-SSS/TODO.md` |
| Acoustic model, world generation, mission bundles, renderer seams, smoke test | `BlueBoat-SSS-Sim/CLAUDE.md` · open items `BlueBoat-SSS-Sim/TODO.md` (the package rename is [P0] there) |
| Station threading model, map and georeferencing, Pattern Designer, `integration/` deploy | `BlueBoat-MCS/CLAUDE.md` · open items `BlueBoat-MCS/TODO.md` |
| Augmentation families, intensity-domain policy, reproducibility contract, extension contract | `SSS-Dataset-Aug-Studio/CLAUDE.md` · open items `SSS-Dataset-Aug-Studio/TODO.md` |

Where a module's `CLAUDE.md` marks its own repo layout UNCERTAIN or its GCS/controller
sections HISTORICAL, the repository outranks the document. Prefer reading a file to trusting
a description of it.

No lint or type-check tooling is configured anywhere in the tree. The gates that exist are
per-module: `python3 -m test.smoke_test` (simulator, ~33 checks), `QT_QPA_PLATFORM=offscreen
python3 smoke_test.py` (MCS, 13 blocks), `pytest` (Aug Studio, 39 tests at v0.3.0).
`BlueBoat-SSS` and `BlueBoat-Control` have no automated test suite.
