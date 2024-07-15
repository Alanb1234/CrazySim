# Training Implementation for 4 UAVs
# No need to run the bash script in terminal
# Without using mult-threading and insteading using a ros service
# start Gazebo, then an episode for one control signal. after episode 
# reset robots to initial location then repeat 2 more times. then close gazebo


import time
import subprocess
import time
import threading

import rclpy
from rclpy.node import Node
from std_srvs.srv import Empty



import cflib.crtp
from cflib.crazyflie.swarm import CachedCfFactory, Swarm



NUM_EPISODES = 2  # Number of episodes for testing
Pause = 4
CONNECTION_TIMEOUT = 40  # Timeout for connecting to the drones




# Create an event to signal the end of an episode
episode_finished_event = threading.Event()


uris = [
    'udp://0.0.0.0:19850',
    'udp://0.0.0.0:19851',
    'udp://0.0.0.0:19852',
    'udp://0.0.0.0:19853',
    # Add more URIs if you want more copters in the swarm
]

class ResetSim(Node):
    def __init__(self):
        super().__init__('reset_sim')
        self.reset_simulation_client = self.create_client(Empty, '/reset_simulation')
        
        while not self.reset_simulation_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('Simulation reset service not available, waiting again...')
        
    def reset_simulation(self):
        req = Empty.Request()
        self.reset_simulation_client.call_async(req)


# Define the function to start Gazebo
def start_gazebo():
    global gz_process
    print("Starting Gazebo...")
    gz_process = subprocess.Popen(
        ["/bin/bash", "/home/alan/CrazySim/CoverageSim/launch_gazebo.sh", "start"],
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


def run_episode():
    global episode_finished_event
    try:
        cflib.crtp.init_drivers()
        factory = CachedCfFactory(rw_cache='./cache')
        
        with Swarm(uris, factory=factory) as swarm:
            print('Connected to Crazyflies')
            swarm.parallel_safe(take_off)
            
            commands_1 = {
                'udp://0.0.0.0:19850': ['stay'],
                'udp://0.0.0.0:19851': ['forward'],
                'udp://0.0.0.0:19852': ['left'],
                'udp://0.0.0.0:19853': ['left']
            }

            swarm.parallel_safe(uav_commands, args_dict=commands_1)
            swarm.parallel_safe(land)
            episode_finished_event.set()
    except Exception as e:
        print(f"Error during episode: {e}")
        episode_finished_event.set()

def main():
    
    start_gazebo()


    rclpy.init()
    reset_node = ResetSim()


    for episode in range(NUM_EPISODES):
        print(f"Starting Episode {episode + 1}")
        episode_finished_event.clear()

        run_episode()
        time.sleep(5)  # Give some time for the episode to run

        print("Resetting robots for the next episode...")
        reset_node.reset_robots()
        time.sleep(5)  # Give some time for the reset to take effect

        print(f"Finished Episode {episode + 1}")

    stop_gazebo()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
