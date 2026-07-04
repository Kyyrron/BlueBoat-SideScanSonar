#!/usr/bin/env python3
"""Mission path service -- interface-identical sibling of ``path_generation.py``.

Serves the same ``blueboat_interfaces/srv/RequestPath`` service on
``/path_request`` (time array in, ``nav_msgs/Path`` out), but the
time-parameterised trajectory comes from a mission bundle's
``trajectory.yaml`` (see :mod:`blueboat_sss_sim.mission.generate`) instead of
hard-coded analytic shapes.

Because the service contract is byte-identical, the unmodified
``master_control.py`` / ``path_publisher.py`` stack tracks generated survey
missions with **zero changes** -- at launch time you simply start this node
instead of ``path_generation.py``.

Parameters
----------
trajectory_file   path to trajectory.yaml (required)
display_log       bool, mirrors the original node
"""

from __future__ import annotations

import rclpy
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Path
from rclpy.node import Node
from scipy.spatial.transform import Rotation as R

from blueboat_interfaces.srv import RequestPath

from ..mission.patterns import WaypointTrajectory


class MissionPathGeneration(Node):
    def __init__(self) -> None:
        super().__init__("path_generation")

        self.declare_parameter("display_log", False)
        self.declare_parameter("trajectory_file", "")
        self._display_log = bool(self.get_parameter("display_log").value)

        traj_file = self.get_parameter("trajectory_file").value
        if not traj_file:
            raise RuntimeError("parameter 'trajectory_file' is required")
        self._traj = WaypointTrajectory.load_yaml(traj_file)
        self.get_logger().info(
            f"mission trajectory '{self._traj.name}': "
            f"{len(self._traj.waypoints)} waypoints, "
            f"{self._traj.total_length:.0f} m, "
            f"{self._traj.duration:.0f} s at {self._traj.speed} m/s")

        self.create_service(RequestPath, "/path_request", self._generate_path)

    def _single_pose(self, t: float) -> PoseStamped:
        x, y, yaw = self._traj.pose_at(t)
        quat = R.from_euler("zyx", [yaw, 0.0, 0.0]).as_quat()
        pose = PoseStamped()
        pose.header.frame_id = "world"
        pose.pose.position.x = x
        pose.pose.position.y = y
        pose.pose.position.z = 0.0
        pose.pose.orientation.x = quat[0]
        pose.pose.orientation.y = quat[1]
        pose.pose.orientation.z = quat[2]
        pose.pose.orientation.w = quat[3]
        return pose

    def _generate_path(self, request, response):
        if self._display_log:
            self.get_logger().info(
                f"path_request with {len(request.path_request.data)} samples")
        path_msg = Path()
        path_msg.header.frame_id = "world"
        now = self.get_clock().now().to_msg()
        for t in request.path_request.data:
            pose = self._single_pose(float(t))
            pose.header.stamp = now
            path_msg.poses.append(pose)
        response.path = path_msg
        return response


def main(args=None) -> None:
    rclpy.init(args=args)
    node = MissionPathGeneration()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
