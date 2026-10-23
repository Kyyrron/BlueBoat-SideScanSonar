import math
import rclpy
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from std_msgs.msg import Float64

BE = QoSProfile(depth=10, reliability=ReliabilityPolicy.BEST_EFFORT)

class Fake(Node):
    def __init__(self):
        super().__init__('fake_local_odom')
        self.yaw = 0.0
        self.pub = self.create_publisher(Odometry, '/mavros/local_position/odom', BE)
        self.create_subscription(Float64, '/mavros/global_position/compass_hdg', self.cb,
BE)
        self.create_timer(0.05, self.tick)
        self.get_logger().warning('FAKE odometry: fixed (0,0). Bench only.')
    def cb(self, m):
        self.yaw = math.radians(90.0 - m.data)
    def tick(self):
        o = Odometry()
        o.header.stamp = self.get_clock().now().to_msg()
        o.header.frame_id = 'map'
        o.child_frame_id = 'base_link'
        o.pose.pose.orientation.z = math.sin(self.yaw / 2)
        o.pose.pose.orientation.w = math.cos(self.yaw / 2)
        self.pub.publish(o)

rclpy.init()
rclpy.spin(Fake())
