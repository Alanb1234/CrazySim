# Training_components.py
# Contains the different tools needed for the training
# Contaings the Controllers for gazebo and also the UAV
# Contains the reward calculator and DataSaver


import time
import subprocess
import threading
import math
import json
import os
from collections import deque, defaultdict

import cflib.crtp
from cflib.crazyflie.swarm import CachedCfFactory, Swarm
import networkx as nx
import matplotlib.pyplot as plt
from std_msgs.msg import Empty





class UAVController:
    def take_off(self, scf):
        commander = scf.cf.high_level_commander
        commander.takeoff(1.0, 2.0)
        time.sleep(4)

    def land(self, scf):
        commander = scf.cf.high_level_commander
        commander.land(0.0, 2.0)
        time.sleep(10)

    def uav_commands(self, scf, command):
        commander = scf.cf.high_level_commander
        #distance = 1
        distance = 0.25
        duration = 2
        #print(f"Sending command '{command}' to drone '{scf.cf.link_uri}'")
        if command == 'forward':
            commander.go_to(distance, 0, 0, 0, duration, relative=True)
        elif command == 'backward':
            commander.go_to(-distance, 0, 0, 0, duration, relative=True)
        elif command == 'left':
            commander.go_to(0, distance, 0, 0, duration, relative=True)
        elif command == 'right':
            commander.go_to(0, -distance, 0, 0, duration, relative=True)
        elif command == 'stay':
            commander.go_to(0, 0, 0, 0, duration, relative=True)
        time.sleep(4)


class RewardCalculator:
    def __init__(self):
        self.theta_x = math.radians(30)
        self.theta_y = math.radians(30)

    def calculate_fov_dimensions(self, z):
        width = 2 * z * math.tan(self.theta_x)
        height = 2 * z * math.tan(self.theta_y)
        return width, height

    def fovs_overlap(self, fov1, fov2):
        overlap_x = max(0, min(fov1['x_max'], fov2['x_max']) - max(fov1['x_min'], fov2['x_min']))
        overlap_y = max(0, min(fov1['y_max'], fov2['y_max']) - max(fov1['y_min'], fov2['y_min']))
        return overlap_x * overlap_y > 0

    def build_graph(self, fovs):
        graph = defaultdict(list)
        for i in range(len(fovs)):
            for j in range(i + 1, len(fovs)):
                if self.fovs_overlap(fovs[i], fovs[j]):
                    graph[i].append(j)
                    graph[j].append(i)
        return graph

    def count_connected_components(self, graph, num_nodes):
        visited = set()
        components = 0
        for node in range(num_nodes):
            if node not in visited:
                components += 1
                queue = deque([node])
                while queue:
                    current_node = queue.popleft()
                    if current_node not in visited:
                        visited.add(current_node)
                        queue.extend(graph[current_node])
        return components

    def calculate_reward(self, positions):
        total_area = 0
        overlap_area = 0
        fovs = []
        num_robots = len(positions)
        uri_list = list(positions.keys())

        for uri, position in positions.items():
            width, height = self.calculate_fov_dimensions(position.z)
            fov = {
                'x_min': position.x - width / 2,
                'x_max': position.x + width / 2,
                'y_min': position.y - height / 2,
                'y_max': position.y + height / 2,
                'area': width * height
            }
            fovs.append(fov)
            total_area += fov['area']

        for i in range(len(fovs)):
            for j in range(i + 1, len(fovs)):
                overlap_x = max(0, min(fovs[i]['x_max'], fovs[j]['x_max']) - max(fovs[i]['x_min'], fovs[j]['x_min']))
                overlap_y = max(0, min(fovs[i]['y_max'], fovs[j]['y_max']) - max(fovs[i]['y_min'], fovs[j]['y_min']))
                overlap_area += overlap_x * overlap_y

        graph = self.build_graph(fovs)
        num_components = self.count_connected_components(graph, num_robots)
        penalty = num_components if num_components == num_robots else num_components - 1
        penalty_score = penalty * (total_area / num_robots)

        reward = total_area - overlap_area - penalty_score
        return reward, total_area, overlap_area, penalty, num_robots


class DataSaver:
    def save_data_to_json(self, data):
        print("Saving data to JSON file...")
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            json_file_path = os.path.join(script_dir, 'Training_data.json')

            with open(json_file_path, 'w') as f:
                json.dump(data, f, indent=4)
            print(f"Data successfully saved to {json_file_path}")
        except Exception as e:
            print(f"Error saving data to JSON file: {e}")


