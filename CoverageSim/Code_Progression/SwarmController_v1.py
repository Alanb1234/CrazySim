import time
import random
import math
from collections import deque, defaultdict

import cflib.crtp

from cflib.crazyflie.swarm import CachedCfFactory, Swarm
from cflib.crazyflie import Crazyflie, syncCrazyflie

from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.crazyflie.high_level_commander import HighLevelCommander

import networkx as nx
import matplotlib.pyplot as plt

Pause = 4
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

def draw_graph(graph, num_nodes):
    # Draw the graph using networkx and matplotlib
    G = nx.Graph()
    for node in range(num_nodes):
        G.add_node(node)
    for node, neighbors in graph.items():
        for neighbor in neighbors:
            G.add_edge(node, neighbor)
    nx.draw(G, with_labels=True, node_color='lightblue', node_size=500, font_size=16, font_weight='bold')
    plt.show()

def calculate_reward(positions, theta_x, theta_y):
    total_area = 0
    overlap_area = 0
    fovs = []
    num_robots = len(positions)

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
    draw_graph(graph, num_robots)

    num_components = count_connected_components(graph, num_robots)

    penalty = 0
    
    if (num_components == num_robots):
        penalty = num_components
    else:
        penalty = num_components - 1


    penalty_score = penalty * (total_area / num_robots)

    reward = total_area - overlap_area - penalty_score
    return reward, total_area, overlap_area, penalty, num_robots

def take_off(scf):
    commander= scf.cf.high_level_commander
    commander.takeoff(1.0, 2.0)
    time.sleep(Pause)

def land(scf):
    commander= scf.cf.high_level_commander
    commander.land(0.0, 2.0)
    time.sleep(2)
    commander.stop()

def move_forward(scf, distance=1, duration=1):
    commander = scf.cf.high_level_commander
    commander.go_to(distance, 0, 0, 0, duration, relative=True)
    time.sleep(Pause)

def move_back(scf, distance=1, duration=1):
    commander = scf.cf.high_level_commander
    commander.go_to(-distance, 0, 0, 0, duration, relative=True)
    time.sleep(Pause)

def move_left(scf, distance=1, duration=1):
    commander = scf.cf.high_level_commander
    commander.go_to(0, distance, 0, 0, duration, relative=True)
    time.sleep(Pause)

def move_right(scf, distance=1, duration=1):
    commander = scf.cf.high_level_commander
    commander.go_to(0, -distance, 0, 0, duration, relative=True)
    time.sleep(Pause)

def hover(scf, duration=5):
    commander = scf.cf.high_level_commander
    commander.go_to(0, 0, 0, 0, duration, relative=True)
    time.sleep(Pause)

def random_movement(scf, movements=3, distance=1, duration=1):
    commander = scf.cf.high_level_commander
    for _ in range(movements):
        # 'back', 'right'
        direction = random.choice(['forward', 'left'])
        if direction == 'forward':
            commander.go_to(distance, 0, 0, 0, duration, relative=True)
        elif direction == 'back':
            commander.go_to(-distance, 0, 0, 0, duration, relative=True)
        elif direction == 'left':
            commander.go_to(0, distance, 0, 0, duration, relative=True)
        elif direction == 'right':
            commander.go_to(0, -distance, 0, 0, duration, relative=True)
        time.sleep(Pause)

# Define the function to send movement commands
def move_uav(scf, command, *args):
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


    

if __name__ == '__main__':

    cflib.crtp.init_drivers()
    factory = CachedCfFactory(rw_cache='./cache')


    with Swarm(uris, factory=factory) as swarm:
        print('Connected to Crazyflies')
        print("Initial Position:")
        print(swarm.get_estimated_positions())     

        swarm.parallel_safe(take_off)
        time.sleep(5)
        print("Take off Position:")
        
        TakeOff_positions = swarm.get_estimated_positions()
        for uri, position in TakeOff_positions.items():
            x = position.x
            y = position.y
            z = position.z
            print(f'UAV {uri} - x: {x}, y: {y}, z: {z}')
        
        reward1, total_area1, overlap_area1, penalty1, num_robots1 = calculate_reward(TakeOff_positions, theta_x, theta_y)
        print(f'coverage Reward: {reward1}, Total Area: {total_area1}, Overlap Area: {overlap_area1}, penalty: {penalty1}, robots: {num_robots1}')

        time.sleep(2)

    

        # Move UAVs in random directions
        #swarm.parallel_safe(random_movement)
        commands_1 = {
            'udp://0.0.0.0:19850': ['stay'],
            'udp://0.0.0.0:19851': ['forward'],
            'udp://0.0.0.0:19852': ['left'],
            'udp://0.0.0.0:19853': ['left']
        }

        # Move UAVs in random directions
        #swarm.parallel_safe(random_movement)
        commands_2 = {
            'udp://0.0.0.0:19850': ['forward'],
            'udp://0.0.0.0:19851': ['forward'],
            'udp://0.0.0.0:19852': ['forward'],
            'udp://0.0.0.0:19853': ['left']
        }

        # Move UAVs in random directions
        #swarm.parallel_safe(random_movement)
        commands_3 = {
            'udp://0.0.0.0:19850': ['stay'],
            'udp://0.0.0.0:19851': ['forward'],
            'udp://0.0.0.0:19852': ['stay'],
            'udp://0.0.0.0:19853': ['left']
        }

        # Send the commands in parallel 1
        swarm.parallel_safe(move_uav, args_dict=commands_1)
        time.sleep(5)
        print("Moved Position:")

        moved_positions = swarm.get_estimated_positions()
        for uri, position in moved_positions.items():
            print(f'UAV {uri} - x: {position.x}, y: {position.y}, z: {position.z}')

        reward2, total_area2, overlap_area2, penalty2, num_robots2 = calculate_reward(moved_positions, theta_x, theta_y)
        print(f'Coverage Reward: {reward2}, Total Area: {total_area2}, Overlap Area: {overlap_area2}, Penalty: {penalty2}, Robots: {num_robots2}')


        # Send the commands in parallel 2
        swarm.parallel_safe(move_uav, args_dict=commands_2)
        time.sleep(5)
        print("Moved Position:")

        moved_positions = swarm.get_estimated_positions()
        for uri, position in moved_positions.items():
            print(f'UAV {uri} - x: {position.x}, y: {position.y}, z: {position.z}')

        reward2, total_area2, overlap_area2, penalty2, num_robots2 = calculate_reward(moved_positions, theta_x, theta_y)
        print(f'Coverage Reward: {reward2}, Total Area: {total_area2}, Overlap Area: {overlap_area2}, Penalty: {penalty2}, Robots: {num_robots2}')


        # Send the commands in parallel 3
        swarm.parallel_safe(move_uav, args_dict=commands_3)
        time.sleep(5)
        print("Moved Position:")

        moved_positions = swarm.get_estimated_positions()
        for uri, position in moved_positions.items():
            print(f'UAV {uri} - x: {position.x}, y: {position.y}, z: {position.z}')

        reward2, total_area2, overlap_area2, penalty2, num_robots2 = calculate_reward(moved_positions, theta_x, theta_y)
        print(f'Coverage Reward: {reward2}, Total Area: {total_area2}, Overlap Area: {overlap_area2}, Penalty: {penalty2}, Robots: {num_robots2}')



        swarm.parallel_safe(hover)



        # UAV's land
        #swarm.parallel_safe(land)
