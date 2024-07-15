import subprocess
import time
import threading
import os
import signal

NUM_EPISODES = 10  # Number of episodes for testing
SIMULATION_DURATION = 15  # Time to wait before stopping Gazebo

# Define the function to start Gazebo
def start_gazebo():
    print("Starting Gazebo...")
    global gz_process
    gz_process = subprocess.Popen(["/bin/bash", "/home/alan/CrazySim/crazyflie-lib-python/launch_gazebo.sh", "start"])

# Define the function to stop Gazebo
def stop_gazebo():
    print("Stopping Gazebo...")
    time.sleep(SIMULATION_DURATION)  # Wait for the specified simulation duration
    print("Terminating Gazebo...")
    try:
        subprocess.run(['pkill', '-f', 'gz sim'], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error terminating Gazebo: {e}")

# Thread class to handle Gazebo
class GazeboThread(threading.Thread):
    def __init__(self, function):
        threading.Thread.__init__(self)
        self.function = function

    def run(self):
        self.function()

# Main function for testing
def main():
    for episode in range(NUM_EPISODES):
        print(f"Starting Episode {episode + 1}")

        # Start Gazebo in a separate thread
        start_thread = GazeboThread(start_gazebo)
        start_thread.start()

        # Start the stop action in a separate thread
        stop_thread = GazeboThread(stop_gazebo)
        stop_thread.start()

        # Wait for both threads to complete
        start_thread.join()
        stop_thread.join()

        print(f"Finished Episode {episode + 1}")

# Entry point
if __name__ == '__main__':
    main()
