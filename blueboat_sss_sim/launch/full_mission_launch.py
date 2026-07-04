"""End-to-end simulated mission.

Starts, in one command:
  1. Gazebo on the mission bundle's generated ``world.sdf``;
  2. the existing BlueBoat robot description/spawn (via
     ``blueboat_description``'s world launch, world overridden) -- if your
     ``world_launch.py`` does not expose a world argument, see
     docs/integration_guide.md section 3 for the two-line patch or run
     Gazebo separately;
  3. the existing control stack (``simulation_interface``,
     ``master_control``, ``path_publisher``) unchanged;
  4. this package's mission path service (replacing ``path_generation.py``);
  5. the simulated sonar + dataset recorder (``sss_sim_launch.py``).

Prerequisite: ``generate_mission --config ... --out <mission_dir>``.

Arguments
---------
mission_dir       mission bundle directory (required)
controller_type   controller for master_control        (default 'MPC')
use_existing_world_launch  include blueboat_description world_launch.py
                  with a `world` argument               (default true)
"""

from simple_launch import SimpleLauncher

sl = SimpleLauncher(use_sim_time=True)

sl.declare_arg("mission_dir", default_value="")
sl.declare_arg("controller_type", default_value="MPC")
sl.declare_arg("use_existing_world_launch", default_value=True)


def launch_setup():
    mission_dir = sl.arg("mission_dir")
    if not mission_dir:
        raise RuntimeError("launch argument 'mission_dir' is required")
    world_file = f"{mission_dir}/world.sdf"

    # 1-2. Gazebo + robot.
    if sl.arg("use_existing_world_launch"):
        sl.include("blueboat_description", "world_launch.py",
                   launch_arguments={"sliders": False,
                                     "world": world_file})
    else:
        from launch.actions import ExecuteProcess
        sl.add_action(ExecuteProcess(
            cmd=["ign", "gazebo", "-r", world_file], output="screen"))

    # 3. Existing control stack, untouched.
    sl.node("blueboat_control", "simulation_interface.py")
    sl.node("blueboat_control", "path_publisher.py")
    sl.node("blueboat_control", "master_control.py",
            parameters={"controller_type": sl.arg("controller_type"),
                        "simulation": True})

    # 4. Mission trajectory served on the same RequestPath interface.
    sl.node("blueboat_sss", "sss_path_generation", output="screen",
            parameters={"trajectory_file": f"{mission_dir}/trajectory.yaml"})

    # 5. Sonar + dataset.
    sl.include("blueboat_sss", "sss_sim_launch.py",
               launch_arguments={"mission_dir": mission_dir,
                                 "with_recorder": True,
                                 "with_mission_path": False})

    return sl.launch_description()


generate_launch_description = sl.launch_description(opaque_function=launch_setup)
