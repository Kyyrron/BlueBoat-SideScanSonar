"""Launch file for the SSS *processing* pipeline only.

Started by the BlueBoat GCS "START acquisition" button (see
blueboat_gcs/ros/pipeline_launcher.py). It intentionally does NOT start:

* ``sss_node.py``           — the acquisition node runs on the robot side
  and is controlled through ``/side_scan_sonar/ping/enable`` (the GCS
  publishes true/false on START/STOP);
* ``processed_sss_listener.py`` — the matplotlib live listener that this
  application replaces.

Install alongside the existing ``SSS_launch.py`` in the blueboat_sss
package (add it to the launch install rule in CMakeLists / setup.py).

Standalone usage:
    ros2 launch blueboat_sss SSS_processing_launch.py
"""

from simple_launch import SimpleLauncher


def generate_launch_description():
    sl = SimpleLauncher()

    sl.node('blueboat_sss', 'sss_processor_node.py',
            name='sss_processor',
            output='screen')

    return sl.launch_description()
