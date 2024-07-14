# Output a JOSN file containg the different cotrol signal and corresponding reward signals for 4 UAVs
# Spawn the robots using the bash command below in the frazyflie-firmware folder
# bash tools/crazyflie-simulation/simulator_files/gazebo/launch/sitl_multiagent_text.sh -m crazyflie


import time
import math
from collections import deque, defaultdict
import json
import os

import cflib.crtp

from cflib.crazyflie.swarm import CachedCfFactory, Swarm


import networkx as nx
import matplotlib.pyplot as plt

Pause = 4
data = {}

uris = [
    'udp://0.0.0.0:19850',
    'udp://0.0.0.0:19851',
    'udp://0.0.0.0:19852',
    'udp://0.0.0.0:19853',
    # Add more URIs if you want more copters in the swarm
]

# Define the half-angles for the FOV in radians
theta_x = math.radians(30)  # Half-angle in the x direction
theta_y = math.radians(30)  # Half-angle in the y direction

def calculate_fov_dimensions(z, theta_x, theta_y):
    # Calculate the width and height of the FOV based on the altitude and half-angles
    width = 2 * z * math.tan(theta_x)
    height = 2 * z * math.tan(theta_y)
    return width, height

def fovs_overlap(fov1, fov2):
    # Check if two FOVs overlap
    overlap_x = max(0, min(fov1['x_max'], fov2['x_max']) - max(fov1['x_min'], fov2['x_min']))
    overlap_y = max(0, min(fov1['y_max'], fov2['y_max']) - max(fov1['y_min'], fov2['y_min']))
    return overlap_x * overlap_y > 0

def build_graph(fovs):
    # Build a graph where nodes are drones and edges represent overlapping FOVs
    graph = defaultdict(list)
    for i in range(len(fovs)):
        for j in range(i + 1, len(fovs)):
            if fovs_overlap(fovs[i], fovs[j]):
                graph[i].append(j)
                graph[j].append(i)
    return graph

def count_connected_components(graph, num_nodes):
    # Count the number of connected components using BFS
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

def draw_graph(graph, num_nodes, uri_list):
    # Draw the graph using networkx and matplotlib
    G = nx.Graph()
    for node in range(num_nodes):
        G.add_node(node, label=uri_list[node])
    for node, neighbors in graph.items():
        for neighbor in neighbors:
            G.add_edge(node, neighbor)
    pos = nx.spring_layout(G)
    labels = nx.get_node_attributes(G, 'label')
    nx.draw(G, pos, with_labels=True, labels=labels, node_color='lightblue', node_size=500, font_size=8, font_weight='bold')
    plt.show()

def calculate_reward(positions, theta_x, theta_y):
    total_area = 0
    overlap_area = 0
    fovs = []
    num_robots = len(positions)
    uri_list = list(positions.keys())  # List of URIs

    # Calculate the FOV for each drone
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

    # Calculate the overlapping area
    for i in range(len(fovs)):
        for j in range(i + 1, len(fovs)):
            overlap_x = max(0, min(fovs[i]['x_max'], fovs[j]['x_max']) - max(fovs[i]['x_min'], fovs[j]['x_min']))
            overlap_y = max(0, min(fovs[i]['y_max'], fovs[j]['y_max']) - max(fovs[i]['y_min'], fovs[j]['y_min']))
            overlap_area += overlap_x * overlap_y

    # Build graph and count connected components
    graph = build_graph(fovs)
    #draw_graph(graph, num_robots, uri_list)

    num_components = count_connected_components(graph, num_robots)
    penalty = 0
    
    if (num_components == num_robots):
        penalty = num_components
    else:
        penalty = num_components - 1

    penalty_score = penalty * (total_area / num_robots)

    reward = total_area - overlap_area - penalty_score
    return reward, total_area, overlap_area, penalty, num_robots



## Take off, land and random movements commands to show reward

def take_off(scf):
    commander= scf.cf.high_level_commander
    commander.takeoff(1.0, 2.0)
    time.sleep(Pause)

def land(scf):
    commander= scf.cf.high_level_commander
    commander.land(0.0, 2.0)
    time.sleep(10)
    commander.stop()


# Define the function to send movement commands
def uav_commands(scf, command):
    commander = scf.cf.high_level_commander
    distance = 0.5
    duration = 1
    print(f"Sending command '{command}' to drone '{scf.cf.link_uri}'")  # Log the command
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
    time.sleep(Pause)


def save_data_to_json(data):
    print("Saving data to JSON file...")
    try:
        # Get the directory of the current script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # Define the path to the JSON file in the same directory as the script
        json_file_path = os.path.join(script_dir, 'JSONOutput_Implementation.json')
        
        with open(json_file_path, 'w') as f:
            json.dump(data, f, indent=4)
        print(f"Data successfully saved to {json_file_path}")
    except Exception as e:
        print(f"Error saving data to JSON file: {e}")


if __name__ == '__main__':

    cflib.crtp.init_drivers()
    factory = CachedCfFactory(rw_cache='./cache')

    with Swarm(uris, factory=factory) as swarm:
        print('Connected to Crazyflies')

        print("Initial Position:")
        print(swarm.get_estimated_positions())     

        swarm.parallel_safe(take_off)


        print("Take off Position:")        
        TakeOff_positions = swarm.get_estimated_positions()
        for uri, position in TakeOff_positions.items():
            x = position.x
            y = position.y
            z = position.z
            print(f'UAV {uri} - x: {x}, y: {y}, z: {z}')        
        reward_1, total_area_1, overlap_area_1, penalty_1, num_robots_1 = calculate_reward(TakeOff_positions, theta_x, theta_y)
        print(f'coverage Reward: {reward_1}, Total Area: {total_area_1}, Overlap Area: {overlap_area_1}, penalty: {penalty_1}, robots: {num_robots_1}')

        episode_data = {
                "udp://0.0.0.0:19850": [['stay']],
                "udp://0.0.0.0:19851": [['stay']],
                "udp://0.0.0.0:19852": [['stay']],
                "udp://0.0.0.0:19853": [['stay']],
                "rewards": [reward_1]
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


        k=1
        for commands in command_sets:
                print(f"Move {str(k)}: ")
                k=k+1
                swarm.parallel_safe(uav_commands, args_dict=commands)
                moved_positions = swarm.get_estimated_positions()
                reward, total_area, overlap_area, penalty, num_robots = calculate_reward(moved_positions, theta_x, theta_y)

                # Update episode data
                episode_data["rewards"].append(reward)
                for uri, command in commands.items():
                    if uri == 'udp://0.0.0.0:19850':
                        episode_data["udp://0.0.0.0:19850"].append(command)
                    elif uri == 'udp://0.0.0.0:19851':
                        episode_data["udp://0.0.0.0:19851"].append(command)
                    elif uri == 'udp://0.0.0.0:19852':
                        episode_data["udp://0.0.0.0:19852"].append(command)
                    elif uri == 'udp://0.0.0.0:19853':
                        episode_data["udp://0.0.0.0:19853"].append(command)

        
        time.sleep(5)
        # Store episode data
        data[f"ep_1"] = episode_data

        
        save_data_to_json(data)


        swarm.parallel_safe(land)
    