"""Launch the simulated Side Scan Sonar stack.

Composable with the existing ``Sim_launch.py``: start your simulator as
usual, then include (or run alongside) this launch with the mission bundle
directory. Nothing in the existing launch files needs modification.

Arguments
---------
mission_dir     mission bundle directory (from `generate_mission`); provides
                scene, sonar config and trajectory. Required.
with_recorder   also run the YOLO dataset recorder            (default true)
with_mavros_shim  republish heading/imu under MAVROS names    (default false)
with_mission_path run the RequestPath mission service         (default false)
                  (leave false if the existing path_generation.py runs;
                  the two serve the same service name)
dataset_dir     recorder output (default <mission_dir>/dataset)
auto_ping       enable pinging automatically at startup       (default true)
"""

from simple_launch import SimpleLauncher

sl = SimpleLauncher(use_sim_time=True)

sl.declare_arg("mission_dir", default_value="")
sl.declare_arg("with_recorder", default_value=True)
sl.declare_arg("with_mavros_shim", default_value=False)
sl.declare_arg("with_mission_path", default_value=False)
sl.declare_arg("dataset_dir", default_value="")
sl.declare_arg("auto_ping", default_value=True)


def launch_setup():
    mission_dir = sl.arg("mission_dir")
    if not mission_dir:
        raise RuntimeError("launch argument 'mission_dir' is required")
    dataset_dir = sl.arg("dataset_dir") or f"{mission_dir}/dataset"

    # Simulated sonar (drop-in replacement for the real sss_node.py).
    sl.node("blueboat_sss_sim", "sss_sim_node", output="screen",
            parameters={
                "scene_dir": mission_dir,
                "sonar_config": f"{mission_dir}/sonar.yaml",
                "odom_topic": "/blueboat/odom",
                "publish_ground_truth": True,
            })

    if sl.arg("with_recorder"):
        sl.node("blueboat_sss_sim", "dataset_recorder_node", output="screen",
                parameters={"output_dir": dataset_dir})

    if sl.arg("with_mavros_shim"):
        sl.node("blueboat_sss_sim", "mavros_shim_node")

    if sl.arg("with_mission_path"):
        sl.node("blueboat_sss_sim", "sss_path_generation", output="screen",
                parameters={"trajectory_file": f"{mission_dir}/trajectory.yaml"})

    if sl.arg("auto_ping"):
        # One-shot ping enable a few seconds after the graph is up
        # (same command an operator issues on the real system).
        from launch.actions import ExecuteProcess, TimerAction
        sl.add_action(TimerAction(period=5.0, actions=[ExecuteProcess(
            cmd=["ros2", "topic", "pub", "--once",
                 "/side_scan_sonar/ping/enable", "std_msgs/msg/Bool",
                 "data: true"], output="screen")]))

    return sl.launch_description()


generate_launch_description = sl.launch_description(opaque_function=launch_setup)
