---
name: interface-inventory
description: BlueBoat MAVROS boundary table (topics and services taken from and sent to ArduPilot, FCU endpoint and the QGroundControl port collision, the simulator's mavros shim) plus the long tail of other served interfaces (sea-state markers, bag-record resume, Gazebo bridge topics, /clock, /tf, parameter lists). Use before adding or consuming a /mavros/* name, debugging an FCU connection, or looking for a debug or plumbing topic not in the root CLAUDE.md §4.1–§4.3.
---

# MAVROS boundary and other served interfaces

Moved verbatim from the superproject `.claude/CLAUDE.md` §4.4 and §4.7 (2026-10-21).
CM-1 (no renaming or retyping of an existing name) applies to every row here.

### 4.4 MAVROS boundary

| Name | Type | Dir | Module |
|---|---|---|---|
| `/mavros/state` | `mavros_msgs/State` | in | `robot_interface`; MCS (only when `mavros_msgs` imports — absent in simulation) |
| `/mavros/imu/data` | `sensor_msgs/Imu` | in | `robot_interface`; `sss_processor_node` (→ `.svlog` ATTITUDE); GCS (BEST_EFFORT 10, seabed-image metadata only, never geometry; since 2026-10-16) |
| `/mavros/local_position/odom` | `nav_msgs/Odometry` | in | `robot_interface` |
| `/mavros/global_position/global` | `sensor_msgs/NavSatFix` | in | `robot_interface`, GCS, MCS — **BEST_EFFORT**; `lat==0 and lon==0` = no fix, discarded. In a Gazebo run of a GPS-anchored mission on a **stock world** (`Sim_launch`) **MCS is the only publisher** (fixes synthesised from sim odom, ~5 Hz, `status` left at **-2 / STATUS_UNKNOWN**), so only `-1` (STATUS_NO_FIX) means no fix — never gate on `status < 0`. In a **built-world** run (`full_mission_launch`, `with_mavros_shim` default on) the simulator's `mavros_shim` publishes it (~5 Hz, `STATUS_FIX`) and MCS disarms its own SimGps whenever `world_dir` is set (`mcs/gui/main_window.py:346-366`). In a **bag replay** `bag_replay` is the only publisher: the recorded fixes, unchanged but for the stamp (MCS's SimGps stays disarmed). |
| `/mavros/global_position/compass_hdg` | `std_msgs/Float64` | in | MCS, GCS. Degrees **clockwise from north**; MCS converts `radians(90 - hdg)`. Preferred heading source; odom yaw the fallback |
| `/mavros/rc/override` | `mavros_msgs/OverrideRCIn` | out | `robot_interface` at ~20 Hz, latest-wins |
| `/mavros/local_position/pose` (`PoseStamped`), `/mavros/local_position/velocity_local` (`TwistStamped`), `/mavros/vfr_hud` (`VfrHud`) | as listed | in | `sss_processor_node` (BEST_EFFORT 10; the `.svlog` MAVLink envelopes — `src/sss_processor_node.py:381-389`); the GCS also takes `vfr_hud` |
| `/mavros/global_position/rel_alt` (`Float64`), `/mavros/home_position/home` (`HomePosition`), `/mavros/global_position/gp_origin` (`GeoPointStamped`) | as listed | in | `sss_processor_node` (default 10), same envelopes |
| `/mavros/battery` | `sensor_msgs/BatteryState` | in | MCS (`mcs/ros/bridge_node.py:128`), BEST_EFFORT |
| `/mavros/cmd/arming`, `/mavros/cmd/command`, `/mavros/set_mode` | services `CommandBool`, `CommandLong`, `SetMode` | client | `robot_interface` (`robot_interaction/robot_interface.py:227-229`); `guardian.py` also uses `cmd/command` and `set_mode` |
| `/mavros/param/pull`, `/mavros/param/get_parameters`, `/mavros/param/set_parameters` | services `ParamPull`, rcl `GetParameters` / `SetParameters` | client | `param_set` (`robot_interaction/param_set.py:101-103`); `guardian.py` (`link_guardian/laptop/guardian.py:93-108`) |
| `/mavros/statustext/recv`, `/mavros/cmd/set_home`, `/mavros/home_position/req_update` | `StatusText` / services | in / client | `guardian.py` only |

FCU endpoint = `BlueBoat_launch.py`'s `fcu_url` launch argument (default
`udp://:14550@192.168.2.2:14550`). **Port 14550 collides with a running QGroundControl** →
intermittent launch failures (`mavros_router`:
`link[1000] open failed: DeviceError:udp:bind: Address already in use`); close QGC or pass
`fcu_url:=` with another port.

The sim's `mavros_shim_node` (on by default) republishes `/blueboat/odom` under MAVROS names
for tooling written against them (`simCLAUDE.md` §3.2): `/mavros/global_position/global`
(BEST_EFFORT), `/mavros/global_position/compass_hdg`, `/mavros/imu/data`,
`/mavros/local_position/pose` and `/mavros/local_position/velocity_local` (default 10) —
`ros/mavros_shim_node.py:56-76`; parameters `odom_topic`, `sim_origin_lat`, `sim_origin_lon`,
launch argument `with_mavros_shim`.

### 4.7 Other served interfaces (added 2026-10-20)

Names the code serves or uses that §4.1–§4.4 did not list. Same convention: QoS `default`
unless stated. Sources: the 2026-10-20 inventory of every node (Control by AST via
`interface_inventory.py --emit`; the rest by reading the launch files and nodes).

| Name | Type | Producer → Consumers | Notes |
|---|---|---|---|
| `/sim/sea_state/markers` | `visualization_msgs/MarkerArray` | `sea_state_node` → RViz, MCS | **TRANSIENT_LOCAL, depth 1**. `ros/sea_state_node.py:120,233`; documented in `BlueBoat-SSS-Sim/blueboat_sss_sim/docs/topics.md`. |
| `/side_scan_sonar/set_parameters` | service `rcl_interfaces/SetParameters` | GCS (live range change) → `sss_node` / `sss_sim_node` | `blueboat_gcs/ros/ros_manager.py:231-247`. The live range is an operator tool; the survey range is the 20 m default (§4.3). |
| `/path_generation/get_parameters` | service `rcl_interfaces/GetParameters` | GCS → `path_generation` | `blueboat_gcs/ros/path_listener.py:39-42`. |
| `/blueboat_run_bag_<pid>_<k>/resume` | service `rosbag2_interfaces/Resume` | `robot_interface` → the run's `ros2 bag record` process | Pre-armed paused between runs, resumed at run start (`robot_interface.py:1642`, `_custom_libraries/run_bag.py:50-52,131-132`). The recorder takes every topic except `/side_scan_sonar`, `/sss_processor`, `/sss_ai`. |
| `/world/<w>/set_pose` | service `ros_gz_interfaces/SetEntityPose`, bridged by `replay_set_pose_bridge` | `bag_replay` → Gazebo | Bag replay only (`bag_replay.py:414`, `Replay_launch.py:93-95`). |
| `/clock` | `rosgraph_msgs/Clock` | ros_gz bridge → every `use_sim_time` node | Simulation and replay launches (`world_launch.py:23`, `full_mission_launch.py:289`, `Replay_launch.py:92`). Absent on a real-robot run. |
| `/blueboat/cmd_thruster1`, `/blueboat/cmd_thruster2` (UVR variant: `3`) | `std_msgs/Float64` (N) | `simulation_interface`, the standalone `mpc_control` nodes (via the `ROV` helper) → ros_gz bridge → Gazebo | The simulated thrust path (`blueboat_control/__init__.py:135`, `upload_rov_launch.py:66,72`). |
| `/blueboat/pose_gt`, `/blueboat/joint_states` | `geometry_msgs/Pose`, `sensor_msgs/JointState` | Gazebo → ros_gz bridge → `pose_to_tf`, `robot_state_publisher` | Simulation only (`upload_rov_launch.py:41,44-45`). |
| `/blueboat/blueboat_thruster{1,2,3}_wrench`, `/blueboat/blueboat_base` | `geometry_msgs/WrenchStamped`, depth 1 | `ROV` helper → RViz | Debug only. |
| `/blueboat/robot_description` | `std_msgs/String` | `robot_state_publisher` → `ROV` helper, RViz, the Gazebo spawner | **TRANSIENT_LOCAL**. |
| `/tf`, `/tf_static` | `tf2_msgs/TFMessage` | `robot_state_publisher`, `pose_to_tf` → RViz | Simulation and bag replay only (§4.6 TF). |
| `/parameter_events`, `~/{get,set,list,describe}_parameters` | rcl | every rclpy node | Standard. |

**Parameters not listed above.** Control: dozens of parameters across `master_control`
(gains, governor, LoS and MPC tuning, `path_update_*`, `path_progress_period`,
`path_request_timeout`, `thrust_limit`, `data_dir`), `robot_interface`, `param_set` (retry and
sequence timeouts), `path_generation`, `bag_replay` (anchor, `model_name`, `world_name`,
`pose_rate_hz`, `start_paused`, `waterline_z`), `underwater_gps_logger`, `pid_sim` and
`blueboat_controller`; the complete set is the `entries` list of
`BlueBoat-Control/.claude/tools/interface_baseline.json` (gate:
`interface_inventory.py --check`, 163 entries, exit 0 on 2026-10-20). Simulator:
`sss_sim_node` (`scene_dir`, `sonar_config`, `publish_ground_truth`, `seed`, `predict_pose`,
`pose_topic`, `odom_topic`), `sea_state_node` (`current*`, `waves*`, `schedule_file`, `seed`,
`rate_hz`, `world_name`, `world_dir`, `depth_m`, `ramp_s`, `enable_waves`, …), `mavros_shim`
(above) and the launch arguments `sea_*`, `quiet`, `auto_ping`, `headless` — documented in
`BlueBoat-SSS-Sim/blueboat_sss_sim/docs/topics.md`. Perception (`perception` node,
`ros/perception_node.py:128-140`): `mode`, `dataset_name`, `dataset_path`, `world_dir`,
`data_dir`, `record_log`, `join_timeout_s`, `detector`, `preprocess`, `detector_input_mapping`,
`near_range_mask_m`, `turn_window_s`, `label_source`, `label_min_rows`, `label_wait_s`,
`calibration`, `sigma_*`, `footprint_row_step` and six topic-name parameters
(`docs/topics.md` §6). `sss_node` and `sss_processor_node` declare only the six acquisition
parameters; the GCS reads `config/default.yaml`, MCS declares none. There is **no ROS action
server and no `/diagnostics` topic** in any module. In dataset mode with a `world_dir`,
Perception's launch also starts a separate `ros2 bag record` process
(`perception_ground_truth_recorder`) for the two ground-truth topics.
