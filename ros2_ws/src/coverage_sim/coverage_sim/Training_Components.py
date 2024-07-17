# Training_components.py
# Contains the different tools needed for the training
# Contaings the Controllers for gazebo and also the UAV
# Contains the reward calculator and DataSaver


import time
import subprocess

import cflib.crtp
from cflib.crazyflie.swarm import CachedCfFactory, Swarm


from std_msgs.msg import Empty


class GazeboController:
    def start_gazebo(self):
        self.gz_process = subprocess.Popen(
            ["/bin/bash", "/home/alan/CrazySim/launch_gazebo.sh", "start"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        print("Starting Gazebo...")
        time.sleep(20)  # Adjust this sleep time as needed

    def stop_gazebo(self):
        print("Stopping Gazebo...")
        try:
            subprocess.run(['pkill', '-f', 'gz sim'], check=True)
            print("Gazebo terminated.")
        except subprocess.CalledProcessError as e:
            print(f"Error terminating Gazebo: {e}")
        time.sleep(20)


class UAVController:
    def __init__(self):
        self.pause = 4

    def take_off(self, scf):
        commander = scf.cf.high_level_commander
        commander.takeoff(1.0, 2.0)
        time.sleep(self.pause)

    def land(self, scf):
        commander = scf.cf.high_level_commander
        commander.land(0.0, 2.0)
        time.sleep(10)
        commander.stop()

    def uav_commands(self, scf, command):
        commander = scf.cf.high_level_commander
        distance = 0.5
        duration = 1
        print(f"Sending command '{command}' to drone '{scf.cf.link_uri}'")
        if command == 'forward':
            commander.go_to(distance, 0, 0, 0, duration, relative=True)
        elif command == 'back':
            commander.go_to(-distance, 0, 0, 0, duration, relative=True)
        elif command == 'left':
            commander.go_to(0, distance, 0, 0, duration, relative=True)
        elif command == 'right':
            commander.go_to(0, -distance, 0, 0, duration, relative=True)
        elif command == 'stay':
            commander.go_to(0, 0, 0, 0, duration, relative=True)
        time.sleep(self.pause)


