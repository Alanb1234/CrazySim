import json
import time
import cflib.crtp
from cflib.crazyflie.swarm import CachedCfFactory, Swarm
from Training_Components import GazeboController, UAVController, RewardCalculator
import threading


NUM_RUNS = 1  # Number of times to run the strategy


# Load the strategy from the JSON file
def load_strategy(file_path):
    with open(file_path, 'r') as f:
        return json.load(f)

# Map agent numbers to URIs
URI_MAPPING = {
    'agent_0': 'udp://0.0.0.0:19850',
    'agent_1': 'udp://0.0.0.0:19851',
    'agent_2': 'udp://0.0.0.0:19852',
    'agent_3': 'udp://0.0.0.0:19853',
}

def execute_strategy(strategy_file):
    # Initialize components
    gazebo_controller = GazeboController()
    uav_controller = UAVController()
    reward_calculator = RewardCalculator()

    # Load the strategy
    strategy = load_strategy(strategy_file)

    # Start Gazebo
    gazebo_controller.start_gazebo()

    # Initialize CRTP
    cflib.crtp.init_drivers()
    factory = CachedCfFactory(rw_cache='./cache')
    with Swarm(URI_MAPPING.values(), factory=factory) as swarm:

        print('Connected to Crazyflies')

        for i in range(NUM_RUNS):
            print(f"\nStarting run {i+1}")

            time.sleep(2)
            # Take off
            swarm.parallel_safe(uav_controller.take_off)

            # Execute strategy for each agent
            max_steps = max(len(strategy[agent]['actions']) for agent in strategy if agent.startswith('agent_'))

            for step in range(max_steps):
                commands = {}
                for agent, uri in URI_MAPPING.items():
                    if agent in strategy and step < len(strategy[agent]['actions']):
                        commands[uri] = [strategy[agent]['actions'][step]]
                    else:
                        commands[uri] = ['stay']  # Default action if strategy is exhausted

                print(f"Step {step + 1}: Executing commands {commands}")
                swarm.parallel_safe(uav_controller.uav_commands, args_dict=commands)

                time.sleep(4)  # Small delay between steps




            # Land the drones
            swarm.parallel_safe(uav_controller.land)

            print(f"Resetting UAVs")
            gazebo_controller.reset_uavs()





        # Create threads for closing swarm links and stopping Gazebo
        swarm_linkClose_thread = threading.Thread(target=swarm.close_links)
        gazebo_stop_thread = threading.Thread(target=gazebo_controller.stop_gazebo)

        # Start both threads
        print("Starting cleanup...")
        swarm_linkClose_thread.start()
        print("Swarm links closed.")
        time.sleep(4)
        gazebo_stop_thread.start()
        print("Gazebo stopped.")    


        # Wait for both threads to complete
        swarm_linkClose_thread.join()
        print("Swarm links closed.")
        gazebo_stop_thread.join()
        print("Gazebo stopped.")    





    


if __name__ == "__main__":
    strategy_file = 'idqn_best_strategy.json'  # Path to your JSON strategy file
    execute_strategy(strategy_file)