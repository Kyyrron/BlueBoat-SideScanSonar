# Cross-module interface contract (superproject CLAUDE.md §4)

<!-- Moved verbatim from .claude/CLAUDE.md on 2026-11-07 (/doctor) so it loads on demand; section numbers unchanged, so "§4.x" / "§6 Dn" references elsewhere resolve here. -->

## 4. Cross-module interface contract

Where two modules state different values for one thing, both appear in the row — the
disagreement is itself a cross-module fact, resolved in the named module's `TODO.md`. Names
are **absolute** in the source: `master_control` is constructed with `namespace='blueboat'`,
but ROS 2 does not namespace absolute names (`ctrlCLAUDE.md` §2).

### 4.1 Vehicle and control

QoS is `default` for every row unless the notes say otherwise (`/blueboat/odom`: `default 10`).

| Name | Type | Producer → Consumers | Notes |
|---|---|---|---|
| `/blueboat/odom` | `nav_msgs/Odometry` | `robot_interface` (real) · Gazebo bridge (sim, `odom_topic` param) · `bag_replay` (bag replay: the recorded `/mavros/local_position/odom` with its **full** attitude and body twist, in the replay world frame) → `master_control`, `sss_processor_node`, `sss_sim_node`, GCS, MCS, BlueBoat-Belief (BEST_EFFORT, depth 50; with `/mavros/global_position/global`, BEST_EFFORT depth 10, for its odom → map fit), BlueBoat-Replanner (default QoS, depth 10; freshness by arrival time, for the decision record) | **Both local ENU since 2026-08-31; only the origin differs.** Real: origin = boat at launch, yaw **absolute ENU**. Sim: Gazebo ENU, no re-zeroing. Documents describing a launch-relative yaw predate the fix. `sssTODO.md`: this topic reads zero in real-robot runs. The GCS takes per-row roll / pitch / yaw rate for the seabed-image metadata from `/mavros/imu/data` (2026-10-16), never from this topic's yaw-only real attitude. |
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
| `/blueboat/update_path` | service `blueboat_interfaces/srv/UpdatePath` | client → `master_control` (every launch, sim and real). Clients today: Control's tests (`test/path_update_demo.py`, `test/gazebo_path_update.py`) and BlueBoat-Replanner (`ros/executor.py`; cross-checked offline against Control's `PathUpdater`, run under ROS on 2026-11-12 only against a made-up server of the real service type, not yet against `master_control`); an MCS "Replanner mode" is future | **Live path update, 2026-10-15, additive.** Loads the first path of a **replanner-owned** run (`path_source:=replanner`), or replaces its rest from `change_point` on. A fixed-mission or pinger run answers `mission_owned`. Every request gets `ok` or one of 17 codes, and a refusal changes nothing. It never touches safety or operator state (Control N10). Gazebo-verified for PID/LoS/MPC, not on water. Contract: `BlueBoat-Control/docs/PATH_UPDATE_INTERFACE.md`. |
| `/blueboat/path_progress` | `std_msgs/String` (JSON, `blueboat_path_progress/1`) | `master_control` → BlueBoat-Replanner (`replanner`, RELIABLE VOLATILE depth 10), tests | Default QoS, 10 Hz plus one on every answer or transition, in every launch. Carries τ (the governor's path parameter; never derive wall-clock times from path seconds), the state, the following and active ids, `min_change_point`, the end of the path and the last answer. |
| `/blueboat/path_update_event` | `std_msgs/String` (JSON, `blueboat_path_update_event/1`) | `master_control` → `robot_interface`, `simulation_interface`, BlueBoat-Replanner, the run bag | Reliable, **depth 50**, not heartbeated. One message per answer, activation, end or clear. Logged as the run's `<date>-<note>-pathlog.csv`, created only if the run received a request. |
| `/replanner/plan` | `nav_msgs/Path` | BlueBoat-Replanner (`replanner`) → RViz, GCS (optional) | RELIABLE, **TRANSIENT_LOCAL**, depth 1, frame `world`. The mirror of the path Control holds, republished on every accepted change; pose stamps = path parameter. Display only. Since 2026-11-12 (isolated ROS graph only). |
| `/replanner/decision` | `std_msgs/String` (JSON, `blueboat_replanner_decision/1`) | `replanner` → bag, analysis | RELIABLE, depth 50. One per decision: inputs, candidates with J / J2, rules fired, budget, timing, request, labels. Schema: `BlueBoat-Replanner/docs/topics.md` §5.1. |
| `/replanner/status` | `std_msgs/String` (JSON, `blueboat_replanner_status/1`) | `replanner` → operator, MCS (future) | RELIABLE, **TRANSIENT_LOCAL**, depth 1, 1 Hz + on change. States include `disarmed` (override / E-STOP; re-armed only by `/replanner/start`), `stopped_holding` (the only "stopped") and `stop_rejected` (stop **not** in effect). |
| `/replanner/start`, `/replanner/stop` | service `std_srvs/srv/Trigger` | operator → `replanner` | Start or re-arm a mission (never autonomous; needs a replanner-owned run); stop = a truncation to a hold. |
| `/replay/state` | `std_msgs/String` (JSON) | `bag_replay` → MCS (REPLAY box) | **Bag replay only, TRANSIENT_LOCAL depth 1**, 2 Hz: `{bag, t, duration, rate, paused, finished, frame: empty\|anchored, world, world_offset, pose_source, gazebo}`; additive 2026-10-27 `{placement, attitude_source, attitude_rate_hz, attitude_interp, heave, boat_pose}`. |
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
| `/sim/sea_state/boat_pose` | `geometry_msgs/TransformStamped` | ros_gz bridge in `sea_state_launch.py` (from gz `/model/blueboat/pose`, `blueboat_description`'s own `PosePublisher`) · **in a bag replay, `bag_replay`** (the replayed pose, 100 Hz, 2026-10-27; no sea state runs there) → `sea_state_node`, `sss_sim_node` | **Simulation-only, additive** (2026-10-09): the boat's pose every physics step (100 Hz), sim-time stamped — what the hull wrench and the sonar use; the 20 Hz `/blueboat/odom` is their fallback. |
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
| `/side_scan_sonar/ground_truth/contacts` | `std_msgs/String` (JSON) | `sss_sim_node` → offline analysis (`mission_metrics --source jsonl` on a dump); BlueBoat-Perception's dataset labels (dataset mode in a world only, since 2026-10-16) | default 10 | **Simulation-only, additive.** Empty under the ray-cast renderer (no contacts yet). Schema: `BlueBoat-SSS-Sim/blueboat_sss_sim/docs/topics.md`. `ghost`/`via` mark a multipath image of the same `object_id` — aggregate on `(object_id, via)`; both default to direct when absent. `shadow_bins` and `visible` are read off the rendered visibility mask (a training label measures the image), so a consumer using them as a flat-bottom *height* estimator must invert the geometry itself. |
| `/side_scan_sonar/ground_truth/sensor` | `std_msgs/String` (JSON) | `sss_sim_node` → offline analysis (`analysis/sea_validation.py`, the Gazebo sea gate); BlueBoat-Perception's dataset labels (dataset mode in a world only) | default 10 | **Simulation-only, additive** (2026-10-08). Every ping cycle: the vehicle pose at the ping time and the transducer pose each side was rendered from (the lever arm rotated by the full attitude). Schema: `BlueBoat-SSS-Sim/blueboat_sss_sim/docs/topics.md`. |
| `/side_scan_sonar/ground_truth/run_info` | `std_msgs/String` (JSON) | `sss_sim_node` → the GCS (`core/sim_run_info.py`, stored as a session's `metadata.json["simulation"]`) | RELIABLE, TRANSIENT_LOCAL, depth 1 at both ends (CM-4) | **Simulation-only, additive (2026-11-11).** The run's provenance: renderer, profile path + sha256, world digest, seeds, acquisition, build stamp, whether the installed simulator is its source tree. `ground_truth/sensor` gained `run_id` and `range_scale` the same day (true slant range → imaged range, `1500 / c` under the ray-cast); BlueBoat-Perception's `core/sim_labels.py` multiplies its label ranges by it. Schema: BlueBoat-SSS-Sim `docs/topics.md` |
| `/sss_processor/processed` | `blueboat_interfaces/ProcessedSSSPing` | `sss_processor_node` → GCS, BlueBoat-Belief | BEST_EFFORT, depth **200** at the GCS, depth 50 at Belief | Slant-range corrected, water column removed; sign of `*_y` = side (**+y port, −y starboard**). |
| `/sss_processor/log/enable` | `std_msgs/Bool` | GCS (Record ON/OFF) → `sss_processor_node` | default | |
| `/sss_ai/seabed_image` | `sensor_msgs/Image` 32FC1 | GCS → BlueBoat-Perception | RELIABLE, KEEP_LAST 32, VOLATILE (both ends, CM-4) | **Since 2026-10-16.** Every seabed image, recording or not: the raw float dB (= the session's `_world.npz:intensity_db`). `header.frame_id` = the image key `"<stream_id>/<image_id>"`, not a TF frame. Contract: `BlueBoat-Perception/docs/topics.md`. |
| `/sss_ai/seabed_image/png` | `sensor_msgs/Image` mono8 | GCS → BlueBoat-Perception | same | The display PNG, byte-equal to the saved one. |
| `/sss_ai/seabed_image/metadata` | `std_msgs/String` (JSON envelope) | GCS → BlueBoat-Perception | same | The picture metadata (schema 5) in an envelope carrying the key. |
| `/sss_ai/seabed_analysis` | `std_msgs/String` (JSON) | GCS → *(no consumer in the current tree)* | default | Image metadata, **never pixels**. Schema = the picture metadata's: **5 since 2026-10-16** (4 before). `detections` is always `[]`; the detections are on `/sss_ai/detections`. |
| `/sss_ai/detections` | `vision_msgs/Detection2DArray` | **BlueBoat-Perception → GCS**, BlueBoat-Belief (RELIABLE, depth 50). Dev and simulation only: BlueBoat-Replanner's `replanner_emulator` (`emulator_launch.py`) publishes it **instead of** Perception, never beside it | default (RELIABLE, 10) | **The station's one detection source** (owner's order, 2026-10-16): one array per image, possibly empty. Every map marker, waterfall marker and `detections.csv` row comes from here; the GCS runs no detector. uid = `2_000_000 + 16·image_id + k`, restarting with `image_id` at every START. Since 2026-10-23 only detections with `confidence >= map_min_confidence` (0.10) are published here; the image record keeps all, same uids; ≤ 999 per image. |
| `/sss_ai/image_records` | `std_msgs/String` (JSON, `blueboat_perception/image_record/1`) | BlueBoat-Perception → BlueBoat-Belief (optional companion since 2026-11-12), offline analysis | RELIABLE, KEEP_LAST 100, VOLATILE (both ends, CM-4) | One per image, with or without detections (`detections: []` = searched, nothing found; `null` = no pixels). Offline over the session = live: byte-equal canonical JSON minus `provenance` / `source`. **Belief reads four things from it and nothing else:** the row span (`time.t_min_s` / `t_max_s`), whether the detector searched the image (`processing.detector.status == "ran"` and `detections` not `null`), `processing.detector.dummy`, `processing.calibration.calibrated`. It never takes a detection from a record. Belief works without the topic (`BlueBoat-Belief/blueboat_belief/docs/MATH.md` §8). |
| `/sss_ai/perception/status` | `std_msgs/String` (JSON) | BlueBoat-Perception → operator, tests | RELIABLE, depth 1, TRANSIENT_LOCAL | 1 Hz: join counters (`late_parts`, `gaps`, …), latency, configuration. |
| `/belief_map/belief_grid` | `blueboat_belief_interfaces/BeliefGrid` | BlueBoat-Belief (`belief_map`) → BlueBoat-Replanner | RELIABLE, **TRANSIENT_LOCAL**, KEEP_LAST 1 | **Since 2026-11-12 (built 2026-11-04).** Contract `belief_grid/0`: `BlueBoat-Belief/blueboat_belief/docs/topics.md`. 1 Hz on a steady clock; `grid_seq` +1 per message and restarting at 1 with the node. `header.stamp` is the evidence horizon on the sonar-profile clock (every ping at or before it is in the grid), one to two image strides behind the newest ping. Map frame = ENU about the survey area's `geo_anchor`; `odom_to_map_valid` false until the GPS / odom fit converged. Scores are raw while `model_params_json.detector_calibrated` is false. Searched sectors are `aspect_log_miss < 0`, not `aspect_counts > 0`. |
| `/belief_map/query_belief` | `blueboat_belief_interfaces/srv/QueryBelief` | client → `belief_map` | — | A disc query (map frame); everything it returns can be recomputed from `BeliefGrid`. |
| `/belief_map/p_target`, `/belief_map/coverage` | `nav_msgs/OccupancyGrid` | `belief_map` → operator display (RViz) | RELIABLE, TRANSIENT_LOCAL, KEEP_LAST 1 | Display only, 0.5 Hz, frame label `map` (no TF). `p_target` is on a log scale. |
| `/belief_map/contacts` | `visualization_msgs/MarkerArray` | `belief_map` → operator display | default 10 | Display only: a 2-sigma ellipse and a label per contact. |
| `/diagnostics` | `diagnostic_msgs/DiagnosticArray` | `belief_map` → operator, tests | default 10 | 1 Hz on a steady clock, status name `belief_map`: every rejection counter, `stats.*`, alignment, the configured and the observed calibration flag, `coverage.source`, `latency.event_age_s`. **The project's only `/diagnostics` publisher.** |
| `/rosout` | `rcl_interfaces/Log` | all nodes → GCS embedded console | default | The GCS matches the literal string `sss_processor_node` to sweep orphan processes on STOP, so that executable name and its `output='screen'` are load-bearing. |

**Acquisition parameters** (`range_start_mm`, `range_length_mm`, `msec_per_ping`,
`gain_index`, `num_results`, `pulse_len_percent`): identical names, semantics **and defaults**
real = sim since 2026-09-28 (range start 0); the sim's smoke test reads the real driver's
source and asserts the equality. **Since 2026-10-27 they are SonarView's acquisition**
(owner: "as close to SonarView as possible", identically in SSS and SSS-Sim; only the range
may vary — `sssCLAUDE.md` NC #3b).

| Parameter | Default (sim = real) | Survey setting (`project_synthesis.md` §8.5) |
|---|---|---|
| `range_length_mm` | 20000 (sized from water depth, `sssCLAUDE.md` NC #5) | **20 m per side for every survey condition** (owner, 2026-10-20) — the default, no override |
| `msec_per_ping` | **50** (SonarView's command, 2026-10-27; was 0 = free run) | — |
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

**Sonar model and slow-down (owner order, 2026-11-07).** The simulator renders with the
geometric model (default) or the ray-cast sensor (`sss_sim_node` `renderer`, launch
`sonar_renderer:=`; `simCLAUDE.md` §3.1). The ray-cast costs far more than the 50 ms ping
period, so a ray-cast run is **slowed as a whole**: `full_mission_launch.py
real_time_factor:=` (0.01-4.0; MCS Slow-down x0.010-x4.000 since 2026-11-10, above x1 only the time between held pings runs faster) runs Gazebo below real time
(`gz sim -z`), and every world-timing rule runs on `/clock` — `master_control` /
`simulation_interface` `time_source: ros` (every simulation launch; `wall`, the default, in
every real one), the processor and Perception under `use_sim_time`, the GCS and MCS on
sim-paced stream/station clocks. A slowed run therefore pings at 20 Hz in sim time and its
records (`.svlog`, `.npy`, poslog, GCS sessions, Perception records and datasets) are those
of a real-speed run. One exception: the ray-cast publishes no ground-truth contacts yet, so a ray-cast
run's Perception dataset labels are empty. Verified live at x0.2 and x0.05 with the geometric sonar (RTF measured
0.2000, ping stamps every 50.0 ms of sim time, `.npy` `t` in sim seconds), and with the
ray-cast on the GPU (`warp-lang==1.19.0`, in the ROS venv via `requirements.txt` **and** for
the system python `sss_sim_node` runs on): x0.08 held 20 Hz on a flat world, x0.15 did not
(the node logs the factor it needs; `simCLAUDE.md` §3.1). **Held (2026-11-09).** A quay in range
costs a ray-cast ping 1–16 s (0.1 s in open water), so a fixed factor skipped ticks there (the
first full harbour run lost 23 % of its pings). `sss_sim_node` now also **pauses the Gazebo world**
(`/world/<name>/control`, gz-transport; `hold_sim_while_rendering`, launch `sonar_hold_sim`,
default `auto` = the ray-cast only) while a ping cycle overruns its wall budget, and resumes it
as soon as the cycle ends. Still one graph and one `/clock`: a held run is a slowed run whose
clock rate varies, records as above, every ping at its 50 ms sim-time period;
`~/ground_truth/sensor` adds `sim_held` (additive). MCS's Sonar model menu adds the generated
live variants (`raycast_live_sonar.yaml`, `raycast_fast_sonar.yaml`; owner order 2026-11-09) as
`sonar_config:=` — the plain Ray-cast and geometric command lines are unchanged. **Harbour, end to end (2026-11-07).**
- Path: the MCS `LaunchManager` (Ray-cast, x0.03, Extra args `sonar_config:=` → the harbour hybrid profile), then
  the GCS App's START / Record.
- Result: 20.3 Hz in sim time, and the session's `.svlog`, seabed images, waterfall, mosaic and detections as at
  real speed.
- Two limits:
  - Keep the ray-cast's range ≤ 30 m; above 40 m the 8 GB GPU runs out of memory (CUDA error 101). This also
    applies to the GCS's range control, which re-ranges the simulated sonar.
  - The processor's bottom tracker reads the ray-cast's first return 1.4–1.6 m late, against 2 cm for the
    geometric renderer, so the georeference of ray-cast images is off near nadir (`simCLAUDE.md` §3.1).

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
simulator's `config/default_sonar.yaml`. **Submersion agreed at 0.22 m (2026-11-02), fore/aft still disagrees:** field-calibration
pass 3 measured the installation (rear-most hull holes, the same for every corpus):
`sensor_depth_m` **0.22** in the simulator and `TRANSDUCER_SUBMERSION_M` **0.22** in
`sss_processor_node` / the GCS's `core/svlog.py` (both moved the same day). Fore/aft: the
simulator's `mount_x_m` is **−0.345** (the drawing, vs the hull centre); the processor's
`TRANSDUCER_X_OFFSET_M` stays 0.0 and no georeference uses a fore/aft arm. That arm is
relative to the navigation fix (−0.60 m measured on the pool corpus with the GPS near the
bow), so it belongs in a per-session setting; planned in `~/calib/pass3/GCS_PLAN.md` item 4. The seabed pictures
georeference with it since 2026-10-16 (georef convention 2, schema 5). `simTODO.md` closed
its old 0.20 / 0.0 disagreement item on 2026-10-19. The simulator's render fixture,
frozen at 0.20 m, was rebaselined that day; re-rendering at 0.20 reproduced it bit for bit.

**Ping rate — VERIFIED, corrected 2026-10-27:** period `max(msec_per_ping, 2R/c + ~3 ms)`.
The corpus's `max(50 ms, 2R/c + ~3 ms)` (the spec sheet's "20 pings/s up to 30 m") is
**SonarView's 50 ms command**, not a device cap: every corpus file is SonarView's, and our
driver free-running (`msec_per_ping` 0) pinged every **29.0 ms (34.5 Hz) at 20 m** on all four
2026-10-27 recordings. With the default 50 ms, sim (`ping_period_s`, its `max_ping_rate_hz`
cap now 0 = off) and real give the corpus law at every range. Compare sim and real ping
counts at the same `range_length_mm`.

**Ping loss, 2026-10-27 — before ROS** (`sssCLAUDE.md` *Measured acquisition settings*,
`BlueBoat-SSS/blueboat_sss/blueboat_gcs/docs/SONARVIEW_SVLOG_ANALYSIS.md` §11). Our first
field recordings lost 4–61 % of pings where SonarView, the same morning, lost 0 %; the
GCS's depth-200 records miss exactly the pings the processor's depth-10 ones miss, so QoS is
not the cause (CM-4 stands). Causes: `brping`'s receive buffer shared by both devices (now
replaced by a per-device `OmniscanLink`) and the WiFi hop, which SonarLink — recording on
the boat's Pi — never crosses and our stack always does (§1.1).

**Ping assembly.** Both stacks key rows on `ping_number` and emit one-sided rows; neither
pairs by arrival time or withholds a ping while the bottom tracker bootstraps (`sssCLAUDE.md`
NC #2). The processor re-bases on a counter restart (a key ≥ 128 behind the newest seen =
device or sim relaunched under a running processor) and judges "stream stopped" by the wall
clock against the last arrival only, never wall time against a message stamp (sonar stamps are
sim time under Gazebo). In a simulation graph that arrival clock is `/clock` (the processor
runs `use_sim_time` whenever a `/clock` publisher exists at launch, 2026-11-07, and since
2026-11-09 switches to it when one appears later — the GCS starts it before Gazebo — and back to
wall time after 5 s without one), so a simulation slowed below real time does not tear rows. Processor and GCS warn when > 25 % of recent rows are one-sided.
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

**Autopilot message rates — set by the sonar processor (2026-10-27, owner-accepted).** Without
a request ArduPilot streams **4 Hz** on the mavros link: `/mavros/local_position/odom`,
`/mavros/imu/data`, `/mavros/global_position/global` and hence `/blueboat/odom` all ran at
~4 Hz in every 2026-10-27 run bag — except while SonarView was open (10.7–13 Hz), because
SonarLink requests ATTITUDE / LOCAL_POSITION_NED / GLOBAL_POSITION_INT at 30 Hz and a message
interval is autopilot-wide. `sss_processor_node` sends SonarView's exact set through
`/mavros/set_message_interval` whenever the sonar streams, re-asserted every 30 s and (since
2026-11-03) renewed whenever its measured pose rate falls below 10 Hz (`sssCLAUDE.md`).
**What the `/mavros/*` consumers actually receive does not hold steady — UNCERTAIN.**
SonarView's own on-boat recordings carry ~13 Hz per pose message for that request. On the
2026-10-28 water run (`fragmentation_evidence_8`) the autopilot delivered **30 Hz for about
9 s of every 30 s re-assert period and 4 Hz for the other ~21 s**, repeating (calibration
pass 4 report, `~/calib/pass4/step1/D5b/REPORT.md`, owner's machine). So something resets
the intervals between re-asserts. The cause is not identified, and the renewal added for it
is **unverified on water**. The earlier statement here, "~13 Hz until the autopilot reboots,
including later runs without the sonar", does not hold for that run. Control effect: on
that pattern `master_control`'s 20 Hz loop saw **4 Hz pose for about 70 % of the run**
(one pose for five ticks, the PID derivative Δerror / 0.05 s a 5× spike every fifth tick)
and a fresh pose on most ticks only during the 30 Hz bursts. PID-derivative gains tuned or
judged at 13 Hz may therefore behave differently from what a run delivers. The owner's
2026-10-27 judgment stands for the intended steady rate: smooth derivative, gains tuned at
4 Hz may need a retune, fresher MPC/LoS state, real closer to the sim's 20 Hz odom, run
bags' `/mavros/*` topics larger. Record the pose rate with any control experiment.
In simulation the service is absent and nothing is requested. mavros stamps **0** on the real
launch (`use_sim_time` with no `/clock`): the processor keys zero-stamped odom and mavlink
envelopes on arrival time (`sssCLAUDE.md`); the source fix stays a Control item.

### 4.5 File-level interfaces

The Aug Studio exposes **no ROS interface of any kind** — files and CLI only; several other
handoffs are file-mediated too. The per-artifact contracts (`.svlog`, GCS recording sessions
and seabed images, world folders, YOLO and augmented datasets, Perception's tile datasets /
models / evaluations (`Tile_data/`, `Perception_models/`, `Perception_eval/`), `sss_aug_dataset.yaml`,
sea-state presets/timelines, trajectory YAML, position CSVs, mission report folders,
Replanner mission files and run records (`Replanner_data/`),
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
There is **no ROS action server** in any module. `/diagnostics` has exactly one publisher,
BlueBoat-Belief's `belief_map` (§4.3, since 2026-11-12); no other module publishes or reads it.
