# Open Gazebo,  Move 4 UAVs for 2 commands and land. then close gazebo. And repeat 5 Times to make sure no issues
# No need to run the bash script in terminal

# It works, but sort out the threading...
# Number of active threads: 34!!! for 2 Episodes

import time
import subprocess
import time
import threading


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

def run_episode():
    global episode_finished_event
    try:
        cflib.crtp.init_drivers()
        factory = CachedCfFactory(rw_cache='./cache')
        
        with Swarm(uris, factory=factory) as swarm:
            print('Connected to Crazyflies')

            print("Initial Position:")
            print(swarm.get_estimated_positions())

            swarm.parallel_safe(take_off)

            print("Take off Position:")
            take_off_positions = swarm.get_estimated_positions()
            for uri, position in take_off_positions.items():
                print(f'UAV {uri} - x: {position.x}, y: {position.y}, z: {position.z}')

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

            command_sets = [commands_1, commands_2]

            for k, commands in enumerate(command_sets, start=1):
                print(f"Command {k}:")
                swarm.parallel_safe(uav_commands, args_dict=commands)
                moved_positions = swarm.get_estimated_positions()
                for uri, position in moved_positions.items():
                    print(f'UAV {uri} - x: {position.x}, y: {position.y}, z: {position.z}')

            swarm.parallel_safe(land)
            episode_finished_event.set()
    except Exception as e:
        print(f"Error during episode: {e}")
        episode_finished_event.set()


if __name__ == '__main__':
    print(f"Number of active threads: {threading.active_count()}")
    for episode in range(NUM_EPISODES):
        
        print(f"Starting Episode {episode + 1}")

        episode_finished_event.clear()

        start_thread = threading.Thread(target=start_gazebo)
        start_thread.start()
        start_thread.join()  # Ensure Gazebo has started before continuing

        episode_thread = threading.Thread(target=run_episode)
        episode_thread.start()

        # Wait until the episode is finished or timeout
        if not episode_finished_event.wait(CONNECTION_TIMEOUT):
            print("Episode exceeded time limit or connection failed, stopping...")
            episode_finished_event.set()  # Ensure the event is set

        # Stop Gazebo
        stop_thread = threading.Thread(target=stop_gazebo)
        stop_thread.start()
        stop_thread.join()  # Ensure Gazebo has stopped before starting the next episode

        # Print the number of active threads
        print(f"Number of active threads: {threading.active_count()}")

        print(f"Finished Episode {episode + 1}")

