import time
import random
import math
import os
import subprocess
import threading
import signal
import json


from collections import deque, defaultdict
import cflib.crtp
from cflib.crazyflie.swarm import CachedCfFactory, Swarm
from cflib.crazyflie import Crazyflie, syncCrazyflie
from cflib.crazyflie.high_level_commander import HighLevelCommander
import networkx as nx
import matplotlib.pyplot as plt

# Constants
# Parameters
NUM_EPISODES = 4  # Number of episodes for testing
Pause = 4
SIMULATION_DURATION = 100 # Time to wait before stopping Gazebo
data = {}

uris = [
    'udp://0.0.0.0:19850',
    'udp://0.0.0.0:19851',
    'udp://0.0.0.0:19852',
    'udp://0.0.0.0:19853',
]
theta_x = math.radians(30)
theta_y = math.radians(30)

# FOV Calculation Functions
def calculate_fov_dimensions(z, theta_x, theta_y):
    width = 2 * z * math.tan(theta_x)
    height = 2 * z * math.tan(theta_y)
    return width, height

def fovs_overlap(fov1, fov2):
    overlap_x = max(0, min(fov1['x_max'], fov2['x_max']) - max(fov1['x_min'], fov2['x_min']))
    overlap_y = max(0, min(fov1['y_max'], fov2['y_max']) - max(fov1['y_min'], fov2['y_min']))
    return overlap_x * overlap_y > 0

# Graph Functions
def build_graph(fovs):
    graph = defaultdict(list)
    for i in range(len(fovs)):
        for j in range(i + 1, len(fovs)):
            if fovs_overlap(fovs[i], fovs[j]):
                graph[i].append(j)
                graph[j].append(i)
    return graph

def count_connected_components(graph, num_nodes):
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

def draw_graph(graph, num_nodes):
    G = nx.Graph()
    for node in range(num_nodes):
        G.add_node(node)
    for node, neighbors in graph.items():
        for neighbor in neighbors:
            G.add_edge(node, neighbor)
    nx.draw(G, with_labels=True, node_color='lightblue', node_size=500, font_size=16, font_weight='bold')
    plt.show()

# Reward Calculation
def calculate_reward(positions, theta_x, theta_y):
    total_area = 0
    overlap_area = 0
    fovs = []
    num_robots = len(positions)

    for uri, position in positions.items():
        width, height = calculate_fov_dimensions(position.z, theta_x, theta_y)
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

    graph = build_graph(fovs)
    #draw_graph(graph, num_robots)
    num_components = count_connected_components(graph, num_robots)
    penalty = num_components - 1 if num_components > 1 else 0
    penalty_score = penalty * (total_area / num_robots)
    reward = total_area - overlap_area - penalty_score

    return reward, total_area, overlap_area, penalty, num_robots

# Command Functions
def take_off(scf):
    commander = scf.cf.high_level_commander
    commander.takeoff(1.0, 2.0)
    time.sleep(Pause)

def land(scf):
    commander = scf.cf.high_level_commander
    commander.land(0.0, 2.0)
    time.sleep(2)
    commander.stop()

def hover(scf, duration=5):
    commander = scf.cf.high_level_commander
    commander.go_to(0, 0, 0, 0, duration, relative=True)
    time.sleep(Pause)

def move_uav(scf, command, *args):
    commander = scf.cf.high_level_commander
    distance = 0.5
    duration = 1
    command_map = {
        'forward': (distance, 0, 0),
        'back': (-distance, 0, 0),
        'left': (0, distance, 0),
        'right': (0, -distance, 0),
        'stay': (0, 0, 0)
    }
    if command in command_map:
        dx, dy, dz = command_map[command]
        commander.go_to(dx, dy, dz, 0, duration, relative=True)
    time.sleep(Pause)



# Define the function to start Gazebo
def start_gazebo():
    print("Starting Gazebo...")
    global gz_process
    gz_process = subprocess.Popen(["/bin/bash", "/home/alan/CrazySim/crazyflie-lib-python/launch_gazebo.sh", "start"])
    time.sleep(30)

# Define the function to stop Gazebo
def stop_gazebo():
    print("Stopping Gazebo...")
    print("Terminating Gazebo...")
    try:
        subprocess.run(['pkill', '-f', 'gz sim'], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error terminating Gazebo: {e}")
    time.sleep(10)


def commands(episode):
    # Initialize Crazyflie swarm
    print("Initializing drivers...")
    cflib.crtp.init_drivers()
    factory = CachedCfFactory(rw_cache='./cache')
    with Swarm(uris, factory=factory) as swarm:
        
        swarm.parallel_safe(take_off)
        time.sleep(5)

        # Run the coverage task and collect data
        TakeOff_positions = swarm.get_estimated_positions()
        for uri, position in TakeOff_positions.items():
            print(f'UAV {uri} - x: {position.x}, y: {position.y}, z: {position.z}')
        
        reward1, total_area1, overlap_area1, penalty1, num_robots1 = calculate_reward(TakeOff_positions, theta_x, theta_y)
        print(f'Coverage Reward: {reward1}, Total Area: {total_area1}, Overlap Area: {overlap_area1}, Penalty: {penalty1}, Robots: {num_robots1}')
        time.sleep(2)

        data[f"ep{episode}"] = {
            "robot1": [],
            "robot2": [],
            "robot3": [],
            "robot4": [],
            "rewards": [reward1]
        }

        # Define movement commands
        commands_1 = {
            'udp://0.0.0.0:19850': ['stay'],
            'udp://0.0.0.0:19851': ['forward'],
            'udp://0.0.0.0:19852': ['left'],
            'udp://0.0.0.0:19853': ['left']
        }
        commands_2 = {
            'udp://0.0.0.0:19850': ['forward'],
            'udp://0.0.0.0:19851': ['forward'],
            'udp://0.0.0.0:19852': ['forward'],
            'udp://0.0.0.0:19853': ['left']
        }
        commands_3 = {
            'udp://0.0.0.0:19850': ['stay'],
            'udp://0.0.0.0:19851': ['forward'],
            'udp://0.0.0.0:19852': ['stay'],
            'udp://0.0.0.0:19853': ['left']
        }

        command_sets = [commands_1, commands_2, commands_3]

        # Execute movement commands in parallel and record actions
        for i, commands in enumerate(command_sets):
            swarm.parallel_safe(move_uav, args_dict=commands)
            time.sleep(5)
            moved_positions = swarm.get_estimated_positions()
            for uri, position in moved_positions.items():
                print(f'UAV {uri} - x: {position.x}, y: {position.y}, z: {position.z}')
            reward, total_area, overlap_area, penalty, num_robots = calculate_reward(moved_positions, theta_x, theta_y)
            print(f'Coverage Reward: {reward}, Total Area: {total_area}, Overlap Area: {overlap_area}, Penalty: {penalty}, Robots: {num_robots}')

            # Record rewards after movements
            data[f"ep{episode}"]["rewards"].append(reward)

            # Record commands
            for uri, command in commands.items():
                if uri == 'udp://0.0.0.0:19850':
                    data[f"ep{episode}"]["robot1"].append(command)
                elif uri == 'udp://0.0.0.0:19851':
                    data[f"ep{episode}"]["robot2"].append(command)
                elif uri == 'udp://0.0.0.0:19852':
                    data[f"ep{episode}"]["robot3"].append(command)
                elif uri == 'udp://0.0.0.0:19853':
                    data[f"ep{episode}"]["robot4"].append(command)

        swarm.parallel_safe(land)
        time.sleep(10)
        




# Main function for testing
def main():
    for episode in range(NUM_EPISODES):
        # Restart Gazebo
        print(f"Starting Episode {episode + 1}")


        # Start Gazebo
        start_gazebo()

        # Run the simulation
        commands(episode + 1)

        print(f"Finished Episode {episode + 1}")
        stop_gazebo()


    # Save data to JSON file
    with open("simulation_data.json", "w") as json_file:
        json.dump(data, json_file, indent=4)
        



# Main Function
if __name__ == '__main__':
    main()
    
