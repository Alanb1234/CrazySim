# Training_Implementation.py
import time
import threading

import cflib.crtp
from cflib.crazyflie.swarm import CachedCfFactory, Swarm


import threading
from Training_Components import GazeboController, UAVController, RewardCalculator, DataSaver

NUM_EPISODES = 4


uris = [
    'udp://0.0.0.0:19850',
    'udp://0.0.0.0:19851',
    'udp://0.0.0.0:19852',
    'udp://0.0.0.0:19853',
]

gazebo_controller = GazeboController()
uav_controller = UAVController()
reward_calculator = RewardCalculator()
data_saver = DataSaver()
data = {}

def run_episodes(episodes):
    cflib.crtp.init_drivers()
    factory = CachedCfFactory(rw_cache='./cache')
    try:
        with Swarm(uris, factory=factory) as swarm:
            print('Connected to Crazyflies')
            print("Initial Position:")
            print(swarm.get_estimated_positions())


            ## Sart of the episodes
            for i in range(episodes):
                print(f"Starting episode {i + 1}/{episodes}")

                swarm.parallel_safe(uav_controller.take_off) 
                take_off_positions = swarm.get_estimated_positions()
                reward_1, total_area_1, overlap_area_1, penalty_1, num_robots_1 = reward_calculator.calculate_reward(take_off_positions)

                episode_data = {
                    "udp://0.0.0.0:19850": [['stay']],
                    "udp://0.0.0.0:19851": [['stay']],
                    "udp://0.0.0.0:19852": [['stay']],
                    "udp://0.0.0.0:19853": [['stay']],
                    "rewards": [reward_1]
                }

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
                    #print(f"Command {k}:")
                    swarm.parallel_safe(uav_controller.uav_commands, args_dict=commands)
                    moved_positions = swarm.get_estimated_positions()
                    reward, total_area, overlap_area, penalty, num_robots = reward_calculator.calculate_reward(moved_positions)
                    #print(f'Coverage Reward: {reward}, Total Area: {total_area}, Overlap Area: {overlap_area}, Penalty: {penalty}, Robots: {num_robots}')

                    episode_data["rewards"].append(reward)
                    for uri, command in commands.items():
                        episode_data[uri].append(command)

                time.sleep(5)
                data[f"ep_{i}"] = episode_data

                swarm.parallel_safe(uav_controller.land)  # Add timeout
                print(f"Resetting UAVs for the next episode {i + 1}")
                gazebo_controller.reset_uavs()
                
                print(f"Completed episode {i + 1}/{episodes}")
                print(f"Number of active threads: {threading.active_count()}")


            data_saver.save_data_to_json(data)
            time.sleep(5)

            gazebo_controller.stop_gazebo()
            swarm.close_links()

    except Exception as e:
        print(f"Error during episode: {e}")


def main():
    print(f"Number of active threads: {threading.active_count()}")

    # Start Gazebo
    gazebo_controller.start_gazebo()

    # Run episodes

    run_episodes(NUM_EPISODES)

    time.sleep(5)

    print(f"Number of active threads: {threading.active_count()}")
    print("Completed all episodes and shut down gazebo.")

    return 0




if __name__ == "__main__":
    main()
