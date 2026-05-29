#!/usr/bin/env python3

import math
import numpy as np
import csv

import rclpy
from rclpy.node import Node

from geometry_msgs.msg import Quaternion

from rclpy.qos import (
    QoSProfile,
    ReliabilityPolicy,
    HistoryPolicy
)

from blueboat_interfaces.msg import ProcessedSSSPing

import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

from custom_functions import quaternion_to_yaw

def sonar_to_world(robot_x: float, robot_y: float, q: Quaternion, left_y: list[float], right_y: list[float]):
    """
    From left_y and right_y in the robot's local frame to world coordinates.

    Parameters
    ----------
    robot_x, robot_y : float
        Robot in world (relative to the starting point)

    q : Quaternion
        Quaternion orientation robot 

    left_y : list[float]
        y-shift from port (+y)

    right_y : list[float]
        y-shift from starboard (-y)

    Returns
    -------
    left_world : list[(x,y)] 
        left_world[i] = (x,y) in world coordinates of the i-th port ping sample
    right_world : list[(x,y)]
        right_world[i] = (x,y) in world coordinates of the i-th starboard ping sample
    """

    left_world: list[tuple[float, float]] = []
    right_world: list[tuple[float, float]] = []

    yaw = quaternion_to_yaw(q)
    cos_yaw = math.cos(yaw)
    sin_yaw = math.sin(yaw)

    # left (port)
    for y_local in left_y:

        # In robot local frame, x is 0 (ping is directly to the side), y is given by the ping

        # Rotation applied
        x_rot = -y_local * sin_yaw
        y_rot = y_local * cos_yaw

        # Translation monde
        x_world = robot_x + x_rot
        y_world = robot_y + y_rot

        left_world.append((x_world, y_world))

    # right (starboard)
    for y_local in right_y:

        # Rotation applied
        x_rot = - y_local * sin_yaw
        y_rot =  y_local * cos_yaw

        # Translation monde
        x_world = robot_x + x_rot
        y_world = robot_y + y_rot

        right_world.append((x_world, y_world))

    return left_world, right_world

class RawSSSImage(Node):

    def __init__(self):
        super().__init__('sss_image_publisher')

        # QoS profile
        sonar_qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=10,
        )

        # Subscriber
        self.subscription = self.create_subscription(
            ProcessedSSSPing,
            '/sss_processor/processed',
            self._on_processed_ping,
            sonar_qos
        )

        self.seabed_x_data = []
        self.seabed_y_data = []
        self.intensity_data = []

        # Matplotlib interactive mode
        plt.ion()

        # Depth plot
        self.fig_depth, self.ax_depth = plt.subplots()

        self.line_depth, = self.ax_depth.plot([], [])

        self.ax_depth.set_xlabel("Time")
        self.ax_depth.set_ylabel("Depth (m)")
        self.ax_depth.set_title("Live sonar plot")
        self.ax_depth.grid(True)

        self.depth_x_data = []
        self.depth_y_data = []

        self.get_logger().info("Live Depth plot ready.")
        
    def save_to_csv(self):

        filename = "sonar_mosaic.csv"

        with open(filename, mode='w', newline='') as file:

            writer = csv.writer(file)

            # Header
            writer.writerow(["x_world","y_world","intensity_db"])

            # Data
            for x, y, intensity in zip(self.seabed_x_data, self.seabed_y_data, self.intensity_data):
                writer.writerow([x,y,intensity])

        self.get_logger().info(
            f"Saved {len(self.intensity_data)} points to {filename}"
        )

    def save_to_npz(self):

        filename = "sonar_mosaic.npz"

        np.savez(
            filename,

            x=np.array(self.seabed_x_data),
            y=np.array(self.seabed_y_data),
            intensity=np.array(self.intensity_data)
        )

        self.get_logger().info(
            f"Saved {len(self.intensity_data)} points to {filename}"
        )

    def _on_processed_ping(self, msg):
        # Traceability
        port_stamp = msg.port_stamp
        starboard_stamp = msg.starboard_stamp

        port_ping_number = msg.port_ping_number
        starboard_ping_number = msg.starboard_ping_number

        # Robot state
        robot_x = msg.robot_x
        robot_y = msg.robot_y

        robot_orientation = msg.robot_orientation

        # Quaternion components
        q = robot_orientation

        # Bathymetry
        water_depth = msg.water_depth

        # Geometry
        transducer_x_offset = msg.transducer_x_offset

        # Sides
        port_intensity_db = list(msg.port_intensity_db)
        port_y = list(msg.port_y)
        starboard_intensity_db = list(msg.starboard_intensity_db)
        starboard_y = list(msg.starboard_y)

        # Example debug

        self.get_logger().info(
            f'Ping received | '
            f'port_number={port_ping_number} '
            f'starboard_number={starboard_ping_number} '
            f'port_samples={len(port_intensity_db)} '
            f'starboard_samples={len(starboard_intensity_db)} '
            f'Robot Coordinates in World: ({robot_x}, {robot_y})'
        )

        # 1. -> Depth live plotting

        # Convert ROS time -> float seconds
        self.depth_x_data.append(port_stamp.sec + port_stamp.nanosec * 1e-9)

        self.depth_y_data.append(water_depth)
        
        # Update plot
        self.line_depth.set_xdata(self.depth_x_data)
        self.line_depth.set_ydata(self.depth_y_data)

        self.ax_depth.relim()
        self.ax_depth.autoscale_view()

        self.fig_depth.canvas.draw()
        self.fig_depth.canvas.flush_events()

        # 2. -> seabed profile image creation

        left_world, right_world = sonar_to_world(robot_x, robot_y, q, port_y, starboard_y) # left_world[i] = (x,y) in world coordinates of the i-th port ping sample

        all_x = [x for x, _ in left_world] + [x for x, _ in right_world]
        all_y = [y for _, y in left_world] + [y for _, y in right_world]

        self.seabed_x_data += all_x
        self.seabed_y_data += all_y
        self.intensity_data += port_intensity_db + starboard_intensity_db

def main(args=None):
    rclpy.init(args=args)

    node = RawSSSImage()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("CTRL+C detected")
        # Save data before shutdown
        node.save_to_npz()

    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()