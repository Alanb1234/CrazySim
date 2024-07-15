import rclpy
from rclpy.node import Node
from std_msgs.msg import Empty
from geometry_msgs.msg import PoseStamped
import numpy as np

class ResetSubscriber(Node):
    def __init__(self):
        super().__init__('reset_subscriber')
        self.subscription = self.create_subscription(
            Empty,
            'reset_uav_topic',
            self.reset_callback,
            10)
        self.pose_publishers = [self.create_publisher(PoseStamped, f'/cf{i}/cmd_pose', 10) for i in range(8)]
        self.original_positions = [
            np.array([0, 0, 1], dtype=float), 
            np.array([1, 0, 1], dtype=float), 
            np.array([0, 1, 1], dtype=float), 
            np.array([1, 1, 1], dtype=float),
            np.array([-1, 0, 1], dtype=float), 
            np.array([0, -1, 1], dtype=float), 
            np.array([-1, -1, 1], dtype=float), 
            np.array([1, -1, 1], dtype=float)
        ]

    def reset_callback(self, msg):
        self.get_logger().info('Reset command received')
        self.reset_uavs()

    def reset_uavs(self):
        for i, position in enumerate(self.original_positions):
            pose_msg = PoseStamped()
            pose_msg.header.stamp = self.get_clock().now().to_msg()
            pose_msg.header.frame_id = 'world'
            pose_msg.pose.position.x = float(position[0])
            pose_msg.pose.position.y = float(position[1])
            pose_msg.pose.position.z = float(position[2])
            self.pose_publishers[i].publish(pose_msg)
        self.get_logger().info('UAVs reset to original positions')

def main(args=None):
    rclpy.init(args=args)
    node = ResetSubscriber()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
