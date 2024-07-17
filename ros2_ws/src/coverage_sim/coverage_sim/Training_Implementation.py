import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Pose
import time
import threading

import cflib.crtp
from cflib.crazyflie.swarm import CachedCfFactory, Swarm

from .Training_Components import GazeboController, UAVController

uris = [
    'udp://0.0.0.0:19850',
    'udp://0.0.0.0:19851',
    'udp://0.0.0.0:19852',
    'udp://0.0.0.0:19853',
]

class UAVControlNode(Node):
    def __init__(self, uris):
        print("UAVControlNode.__init__ called with uris:", uris)
        super().__init__('uav_control_node')
        self._publishers = []
        self._uri_to_publisher = {}
        for i, uri in enumerate(uris):
            topic_name = f'/cf{i}/cmd_pose'
            publisher = self.create_publisher(Pose, topic_name, 10)
            self._publishers.append(publisher)
            self._uri_to_publisher[uri] = publisher
            print(f"Created publisher for {uri} on topic {topic_name}")
        print("UAVControlNode initialization complete")

    def move_uav(self, uri, x, y, z):
        pose = Pose()
        pose.position.x = float(x)
        pose.position.y = float(y)
        pose.position.z = float(z)
        if uri in self._uri_to_publisher:
            self._uri_to_publisher[uri].publish(pose)
            print(f"Published move command for {uri}: x={x}, y={y}, z={z}")
        else:
            print(f"No publisher found for URI: {uri}")



def initialize_cflib():
    cflib.crtp.init_drivers()


def main():
    print(f"Number of active threads: {threading.active_count()}")

    try:
        rclpy.init()
        gazebo_controller = GazeboController()
        uav_controller = UAVController()

        print("About to create UAVControlNode with uris:", uris)
        uav_node = UAVControlNode(uris)
        print("UAVControlNode created successfully")

        gazebo_controller.start_gazebo()
        initialize_cflib()

        factory = CachedCfFactory(rw_cache='./cache')
        swarm = Swarm(uris, factory=factory)
        swarm.open_links()

        print("Starting to move UAVs")
        while rclpy.ok():
            for i, uri in enumerate(uris):
                print(f"Moving UAV {i} to position ({i}, {i}, 1.0)")
                uav_node.move_uav(uri, i, i, 1.0)
            rclpy.spin_once(uav_node, timeout_sec=0.1)
            time.sleep(1)  # Wait for 1 second before sending the next set of commands

    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()

    finally:
        print("Cleaning up...")
        if 'swarm' in locals():
            swarm.close_links()
        if 'gazebo_controller' in locals():
            gazebo_controller.stop_gazebo()
        if rclpy.ok():
            rclpy.shutdown()

if __name__ == '__main__':
    main()

