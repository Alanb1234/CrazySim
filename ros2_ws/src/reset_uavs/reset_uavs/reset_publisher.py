import rclpy
from rclpy.node import Node
from std_msgs.msg import Empty

class ResetPublisher(Node):
    def __init__(self):
        super().__init__('reset_publisher')
        self.publisher_ = self.create_publisher(Empty, 'reset_uav_topic', 10)
    
    def publish_reset(self):
        msg = Empty()
        self.publisher_.publish(msg)
        self.get_logger().info('Reset command published')

def main(args=None):
    rclpy.init(args=args)
    reset_publisher = ResetPublisher()
    reset_publisher.publish_reset()
    reset_publisher.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
