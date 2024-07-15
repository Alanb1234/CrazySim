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
NUM_EPISODES = 2  # Number of episodes for testing
Pause = 4
SIMULATION_DURATION = 40 

data = {}
gz_process = None


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
    #draw_graph(graph, num_robots)

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
    time.sleep(10)
    commander.stop()


# Define the function to send movement commands
def uav_commands(scf, command, *args):
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


# Define the function to start Gazebo
def start_gazebo():
    global gz_process
    print("Starting Gazebo...")
    gz_process = subprocess.Popen(
        ["/bin/bash", "/home/alan/CrazySim/crazyflie-lib-python/launch_gazebo.sh", "start"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    # Wait until Gazebo is fully started
    time.sleep(20)  # Adjust this sleep time as needed

# Define the function to stop Gazebo
def stop_gazebo():
    print("Stopping Gazebo...")
    try:
        subprocess.run(['pkill', '-f', 'gz sim'], check=True)
        print("Gazebo terminated.")
    except subprocess.CalledProcessError as e:
        print(f"Error terminating Gazebo: {e}")
    time.sleep(20)

# Define the function to run episodes
def defined_episodes(episode):
    
    # Initialize Crazyflie swarm
    cflib.crtp.init_drivers()
    factory = CachedCfFactory(rw_cache='./cache')
    with Swarm(uris, factory=factory) as swarm:
        try:
            swarm.parallel_safe(take_off)
            time.sleep(5)

            # Run the coverage task and collect data
            TakeOff_positions = swarm.get_estimated_positions()
            for uri, position in TakeOff_positions.items():
                print(f'UAV {uri} - x: {position.x}, y: {position.y}, z: {position.z}')

            reward1, total_area1, overlap_area1, penalty1, num_robots1 = calculate_reward(TakeOff_positions, theta_x, theta_y)
            print(f'Coverage Reward: {reward1}, Total Area: {total_area1}, Overlap Area: {overlap_area1}, Penalty: {penalty1}, Robots: {num_robots1}')
            time.sleep(2)

            # Update shared data
            episode_data = {
                "robot1": [['stay']],
                "robot2": [['stay']],
                "robot3": [['stay']],
                "robot4": [['stay']],
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
            for commands in command_sets:
                swarm.parallel_safe(uav_commands, args_dict=commands)
                time.sleep(5)
                moved_positions = swarm.get_estimated_positions()
                for uri, position in moved_positions.items():
                    print(f'UAV {uri} - x: {position.x}, y: {position.y}, z: {position.z}')
                reward, total_area, overlap_area, penalty, num_robots = calculate_reward(moved_positions, theta_x, theta_y)
                print(f'Coverage Reward: {reward}, Total Area: {total_area}, Overlap Area: {overlap_area}, Penalty: {penalty}, Robots: {num_robots}')

                # Update episode data
                episode_data["rewards"].append(reward)
                for uri, command in commands.items():
                    if uri == 'udp://0.0.0.0:19850':
                        episode_data["robot1"].append(command)
                    elif uri == 'udp://0.0.0.0:19851':
                        episode_data["robot2"].append(command)
                    elif uri == 'udp://0.0.0.0:19852':
                        episode_data["robot3"].append(command)
                    elif uri == 'udp://0.0.0.0:19853':
                        episode_data["robot4"].append(command)

            # Store episode data
            data[f"ep{episode}"] = episode_data

            swarm.parallel_safe(land)
        except Exception as e:
            print(f"Error in episode {episode}: {e}")
        print(data)

def run_episode(episode):
    try:
        defined_episodes(episode)
    except Exception as e:
        print(f"Error during episode {episode}: {e}")

def main():
    NUM_EPISODES = 5  # Example number of episodes

    # Ensure Gazebo is not running at the start
    stop_gazebo()

    for episode in range(NUM_EPISODES):
        # Start Gazebo in a separate thread
        start_thread = threading.Thread(target=start_gazebo)
        start_thread.start()
        start_thread.join()  # Ensure Gazebo has started before continuing

        # Define a thread to run the episode
        episode_thread = threading.Thread(target=run_episode, args=(episode,))
        episode_thread.start()

        # Sleep for the duration of the episode
        episode_thread.join(65)  # Ensure the episode thread completes

        # Stop Gazebo
        stop_gazebo()
        print(f"Finished Episode {episode}")

    # Save the collected data to a JSON file
    print("Saving data to JSON file...")
    try:
        with open('actions_rewards.json', 'w') as f:
            json.dump(data, f, indent=4)
        print("Data successfully saved to actions_rewards.json")
    except Exception as e:
        print(f"Error saving data to JSON file: {e}")

    print("All episodes completed. Returning to terminal.")
    os._exit(0)

# Example usage
if __name__ == '__main__':
    main()