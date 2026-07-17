# 3 — ROS2 Integration Guide

Complete contract between the station and the existing BlueBoat stack.
Topic names are configurable (`config/settings.py` → `TopicsConfig`); the
defaults below match the stack as provided.

## Subscribed topics

| Topic | Type | Producer | Used for |
|---|---|---|---|
| `/blueboat/odom` | `nav_msgs/Odometry` | `robot_interface.py` | World pose (origin-relative, yaw-only quaternion), heading, speed, trajectory, travelled distance, georeference input |
| `/mavros/global_position/global` | `sensor_msgs/NavSatFix` | MAVROS | Robot GPS read-out, georeference input (BEST_EFFORT QoS) |
| `/mavros/state` | `mavros_msgs/State` | MAVROS | FCU connected / armed / mode |
| `/blueboat/pinger_coordinates` | `Float32MultiArray[3]` | `robot_interface.py` | Pinger in **robot/body frame** (sensor-fused); distance; world position derived by rotating with the current odom pose |
| `/uw_gps_data` | `Float32MultiArray[19]` | `uwgps_log.py` | Timestamp of the last raw USBL packet ("Last update" field) |
| `/monitoring_data` | `Float32MultiArray[9]` `[t,x,y,ψ,x_d,y_d,ψ_d,u1,u2]` | `master_control.py` | **Current path target** `(x_d, y_d)` → target line and robot↔path distance; no recomputation of the controller's target |
| `/thruster_input` | `Float32MultiArray[2]` `[right, left]` (N) | `master_control.py` | Motor command display and history |
| `/blueboat/controller_ready` | `std_msgs/Bool` | `robot_interface.py` | Mission-readiness aggregation |
| `/blueboat/param_mode` | `std_msgs/String` | `param_set.py` | Confirmation echo of `default`/`override`; E-STOP acknowledgement |

## Published commands

| Topic | Type | Payload | Effect (robot side) |
|---|---|---|---|
| `/blueboat/input_str` | `std_msgs/String` | `"default"` | `robot_interface.str_input_callback` → forwarded to `param_set` → safe parameters; echoed on `/blueboat/param_mode`. Published by **Emergency Stop** and by the mode-toggle button. |
| `/blueboat/input_str` | `std_msgs/String` | `"override"` | Direct-control parameters; the other state of the toggle button. |
| `/blueboat/manual_target` | `Float32MultiArray[2]` | `[x, y]` world metres | `master_control` steers to it with LoS, overriding the mission. |
| `/blueboat/manual_target` | `Float32MultiArray[2]` | `[0.0, 0.0]` | Sentinel: `master_control` resumes the original mission. Published automatically when Manual Target mode is deactivated. |

Equivalent shell commands (what the buttons do):

```bash
ros2 topic pub --once /blueboat/input_str std_msgs/msg/String "data: default"
ros2 topic pub --once /blueboat/input_str std_msgs/msg/String "data: override"
ros2 topic pub --once /blueboat/manual_target std_msgs/msg/Float32MultiArray "data: [12.5, -3.0]"
```

Because `(0,0)` is the reserved resume sentinel, a click exactly on the world
origin is nudged to `(0.001, 0)` before publishing.

## Services

`/path_request` (`blueboat_interfaces/RequestPath`): the station requests
`linspace(0, total_time, n)` exactly like `path_publisher.py` and renders the
returned `nav_msgs/Path` as the mission-path layer. Called ~3 s after a launch
with a non-empty controller and `use_pinger:=False` (the launch file only
starts `path_generation` in that case).

## Mission launch

```
ros2 launch blueboat_control BlueBoat_launch.py \
    enable_motors:=<bool> note:=<str> controller_type:=<''|PID|LoS|MPC> \
    trajectory:=<name> use_pinger:=<bool> [extra:=args]
```

**Gazebo simulation alternative** — the dialog's "Gazebo simulation" mode
runs instead:

```
ros2 launch blueboat_control Sim_launch.py \
    robot_file:=<name> trajectory:=<name> controller_type:=<PID|LoS|MPC>
```

That graph consists of the Gazebo world, `simulation_interface.py`
(publishes `/blueboat/controller_ready` and `/monitoring_data`, consumes
`/thruster_input` and `/blueboat/odom` from Gazebo), `path_generation`,
`path_publisher` and `master_control` — and notably **no** MAVROS,
robot_interface, param_set or pinger nodes. The station adapts coherently:
readiness gating drops the FCU check, the mission path is always requested
(path_generation always runs), manual targets work unchanged
(`master_control` subscribes regardless), and the safe-shutdown sequence
skips the `param_mode` acknowledgement wait, which structurally cannot
arrive (the command is still published; the publish-before-terminate
ordering is preserved).

Started in its own process session; stopped with SIGINT to the group
(graceful, propagated by `ros2 launch`), escalating to SIGTERM after
`launch.sigint_timeout_s` and SIGKILL after `sigterm_timeout_s` more.
Coupling rules encoded in the dialog: `trajectory` is disabled when
`use_pinger` is checked (no `path_generation` node in that branch), and
`enable_motors` always requires explicit re-confirmation.

## Safe-shutdown sequence (normative — guards **every** termination path)

E-STOP, **Stop Mission** and **Application Exit** all run the same sequence
(`CommandCenter.safe_shutdown`); nothing in the application terminates nodes
outside of it:

1. Verify the ROS graph: `get_subscription_count()` on the reliable
   `/blueboat/input_str` publisher must show a matched subscription
   (`robot_interface`) — the DDS delivery precondition. A count of 0 is
   reported and the sequence continues (publish + late-discovery hold).
2. Publish `String("default")` — synchronous into the reliable DDS writer.
3. Wait for the end-to-end `param_mode == "default"` echo (proves the
   command was received *and acted on*), up to `estop_confirm_timeout_s`
   (2 s default), republishing once at half-timeout (idempotent).
4. On timeout, hold the process/writer alive for `estop_flush_delay_s` so
   the reliable protocol can complete delivery, and tell the operator which
   confirmation level was obtained.
5. Only then terminate the launch process tree (E-STOP additionally offers a
   publish-only variant). `shutdown_sequence_finished` is emitted for
   asynchronous callers (window close waits on it).

Node termination is never initiated before steps 1–4 complete.

## Observations on the existing stack (flagged, not silently patched)

1. **Manual-target resume comparison** — `master_control.manual_target_callback`
   stores `msg.data` (an `array('f')`), but the guard is
   `self.manual_target != [0.0,0.0]`; an `array` never compares equal to a
   `list`, so after the first manual target the `[0,0]` resume sentinel is
   treated as a manual target *at the origin*. One-line fix:
   `self.manual_target = list(msg.data)`. Until applied, "Continue Original
   Mission" will make the boat head to the world origin instead of resuming.
2. **Pinger branch publishes the target on `/thruster_input`** — in the
   `use_pinger` branch of `master_control.timer_callback`, the block commented
   "Publish controller target (for data recording)" uses
   `self.thruster_input_publisher` instead of `self.target_publisher`,
   injecting target coordinates into the thrust stream consumed by
   `robot_interface`. Recommended fix: `self.target_publisher.publish(msg)`.
3. **World-frame pinger not published** — `robot_interface` computes
   `corrected_pinger` but only writes it to CSV. The station derives it from
   `/blueboat/pinger_coordinates` + `/blueboat/odom` (one rotation). If you
   prefer a single source of truth, add next to the pinger publisher:
   `self.publish(Float32MultiArray(), list(self.corrected_pinger), <new pub on /blueboat/pinger_world>)`
   and point `TopicsConfig` at it.
4. Cosmetic: `robot_interface` publishes monitoring on
   `blueboat/monitoring_data` (relative) while `master_control` uses the
   global `/monitoring_data` — the station follows `master_control`.

## QoS

MAVROS sensor topics are subscribed BEST_EFFORT (matching the stack); all
custom topics use default RELIABLE depth 10, matching their publishers.


## Designer trajectories — integrating with `path_generation.py`

The Mission Pattern Designer exports `blueboat_trajectory/1` YAML files
(specification: `08_trajectory_format.md`). Integration changes **only the
loading mechanism** of `path_generation.py`; `generate_path()` and every
hard-coded trajectory are untouched.

Steps (once):

1. Copy `integration/yaml_trajectory.py` into the `blueboat_control`
   package next to `path_generation.py` (it depends only on PyYAML and
   numpy, both shipped with ROS2).
2. Replace `path_generation.py` with `integration/path_generation.py` — or
   apply its three marked blocks by hand: the `import yaml_trajectory as
   yt`, the loader in `__init__` (parses `trajectory:=from_yaml:<path>` or
   the optional `yaml_path` parameter, loads once, falls back to
   `station_keeping` with an error log on failure), and the `from_yaml`
   branch at the top of `single_pose()`:

   ```python
   if path_shape.startswith('from_yaml') and self.yaml_traj is not None:
       x, y, z, roll, pitch, yaw = yt.read_yaml(self.yaml_traj, t)
       ...
   ```

3. Rebuild the workspace. No launch-file modification is needed: the YAML
   path is carried inside the existing `trajectory` argument
   (`trajectory:=from_yaml:/abs/path.yaml`), which both `BlueBoat_launch.py`
   and `Sim_launch.py` already forward to the node.

Station side, saved missions appear automatically in **Launch Mission →
Trajectory → custom paths**; selecting one builds the `from_yaml:` string.


## Mission-path preview and `path_publisher.py`

The station previews the mission path by calling the **`/path_request`
service directly** (the same request `path_publisher.py` makes at startup),
so the preview works identically on the real robot and in simulation and
never depends on `path_publisher`. The request horizon is
`launch.path_preview_total_time_s` (default 120 s, configurable); for
designer trajectories the YAML's own `duration_s` replaces it
automatically, so long custom missions are previewed completely.

`path_publisher.py` itself is only started by `Sim_launch.py`. It is not
simulation-specific code — it merely was never added to the real-robot
launch. To make it available in the real world (e.g. to keep RViz support),
add to `BlueBoat_launch.py` inside the `controller_type != ''` /
`use_pinger == False` branch, next to `path_generation.py`:

```python
sl.node('blueboat_control',
        'path_publisher.py',
        parameters={'total_time': 300.0,   # horizon in seconds
                    'dt': 0.5})
```

Its 120 s "time limit" is just the default of its declared `total_time`
parameter — override it as above (match the mission duration; for YAML
trajectories, the `duration_s` field of the file). Note it also busy-waits
for the service at startup, which is harmless in this launch ordering.
