import time
import cflib.crtp
from cflib.crazyflie.swarm import CachedCfFactory, Swarm
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.crazyflie.high_level_commander import HighLevelCommander

# Initialize URIs
uris = [
    'udp://0.0.0.0:19850',
    'udp://0.0.0.0:19851',
    'udp://0.0.0.0:19852',
    'udp://0.0.0.0:19853'
]

Pause = 4

def take_off(scf):
    commander= scf.cf.high_level_commander
    commander.takeoff(1.0, 2.0)
    time.sleep(Pause)

def land(scf):
    commander= scf.cf.high_level_commander
    commander.land(0.0, 2.0)
    time.sleep(2)
    commander.stop()


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
    time.sleep(Pause)

if __name__ == '__main__': 
    print("Hello 1")
    cflib.crtp.init_drivers()
    print("Hello 2")
    factory = CachedCfFactory(rw_cache='./cache')
    print("Hello 3")

    # Initialize the swarm
    with Swarm(uris, factory=factory) as swarm:
        # Define commands for each UAV
        commands = {
            'udp://0.0.0.0:19850': ['forward'],
            'udp://0.0.0.0:19851': ['forward'],
            'udp://0.0.0.0:19852': ['left'],
            'udp://0.0.0.0:19853': ['left']
        }


        print('Connected to Crazyflies')
        print("Initial Position:")
        print(swarm.get_estimated_positions())     

        swarm.parallel_safe(take_off)
        time.sleep(5)

        # Send the commands in parallel
        swarm.parallel_safe(move_uav, args_dict=commands)
