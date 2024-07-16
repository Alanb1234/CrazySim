# Training_Implementation.py
import time
import threading

import cflib.crtp
from cflib.crazyflie.swarm import CachedCfFactory, Swarm


import threading
from .Training_Components import GazeboController, UAVController, RewardCalculator, DataSaver

NUM_EPISODES = 4
CONNECTION_TIMEOUT = 45
episode_finished_event = threading.Event()

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

def run_episode(episode):
    global episode_finished_event
    try:
        cflib.crtp.init_drivers()
        factory = CachedCfFactory(rw_cache='./cache')

        with Swarm(uris, factory=factory) as swarm:
            print('Connected to Crazyflies')

            print("Initial Position:")
            print(swarm.get_estimated_positions())

            swarm.parallel_safe(uav_controller.take_off)

            print("Take off Position:")
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
                print(f"Command {k}:")
                swarm.parallel_safe(uav_controller.uav_commands, args_dict=commands)
                moved_positions = swarm.get_estimated_positions()
                reward, total_area, overlap_area, penalty, num_robots = reward_calculator.calculate_reward(moved_positions)
                print(f'Coverage Reward: {reward}, Total Area: {total_area}, Overlap Area: {overlap_area}, Penalty: {penalty}, Robots: {num_robots}')

                episode_data["rewards"].append(reward)
                for uri, command in commands.items():
                    episode_data[uri].append(command)

            time.sleep(5)
            data[f"ep{episode}"] = episode_data

            swarm.parallel_safe(uav_controller.land)
            episode_finished_event.set()
    except Exception as e:
        print(f"Error during episode: {e}")
        episode_finished_event.set()



def main():
    print(f"Number of active threads: {threading.active_count()}")

    gazebo_controller.start_gazebo()

    for episode in range(NUM_EPISODES):
        print(f"Starting Episode {episode + 1}")

        episode_finished_event.clear()

        episode_thread = threading.Thread(target=run_episode, args=(episode + 1,))
        episode_thread.start()

        if not episode_finished_event.wait(CONNECTION_TIMEOUT):
            print("Episode exceeded time limit or connection failed, stopping...")
            episode_finished_event.set()

        #episode_thread.join()


        time.sleep(5)

        print(f"Number of active threads: {threading.active_count()}")
        print(f"Finished Episode {episode + 1}")

    gazebo_controller.stop_gazebo()
    data_saver.save_data_to_json(data)

    print(f"Number of active threads: {threading.active_count()}")


if __name__ == '__main__':

    main()
   
