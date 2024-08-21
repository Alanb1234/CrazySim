import time
import json


# Define the URIs for the Crazyflie drones
uris = [
    'radio://0/20/2M/E7E7E7E701',
    'radio://0/20/2M/E7E7E7E702',
    'radio://0/20/2M/E7E7E7E703',
    'radio://0/20/2M/E7E7E7E704',
]

# Map agent numbers to URIs
URI_MAPPING = {f'agent_{i}': uri for i, uri in enumerate(uris)}

def load_strategy(file_path):
    with open(file_path, 'r') as f:
        return json.load(f)



def execute_strategy(strategy_file):
    strategy = load_strategy(strategy_file)

    # Execute strategy for each agent
    max_steps = max(len(strategy[agent]['actions']) for agent in strategy if agent.startswith('agent_'))

    for step in range(max_steps):
        commands = {}
        for agent, uri in URI_MAPPING.items():
            if agent in strategy and step < len(strategy[agent]['actions']):
                commands[uri] = strategy[agent]['actions'][step]
            else:
                commands[uri] = 'stay'  # Default action if strategy is exhausted

        print(f"Step {step + 1}: Executing commands {commands}")
        time.sleep(1)  # Small delay between steps







if __name__ == '__main__':
    strategy_file = 'idqn_best_strategy.json'  # Path to JSON strategy file
    execute_strategy(strategy_file)
    



