NUM_USERS = 80
MIN_CONVERSATIONS = 1
TOTAL_CONVERSATIONS = 100
NUM_ACTIONS = 5

import json

import numpy as np
import matplotlib.pyplot as plt
import scipy.stats as stats

import mocks.mock_tasks as mock_tasks

def generate_discrete_power_law(num_values, alpha, min_value, total):
    # print('Generating', num_values, 'values with total', total, 'and alpha', alpha)
    values = stats.pareto.pdf(np.arange(1, num_values + 1), alpha)

    values = values / sum(values) * (total - num_values * min_value) + min_value

    if max(values) < 1:
        values /= max(values)
    
    discrete_values = np.floor(values).astype(int)

    remainder = total - sum(discrete_values)

    if remainder == 0:
        return discrete_values
    
    discrete_values += generate_discrete_power_law(num_values, alpha, 0, remainder)

    return [x.item() for x in discrete_values]

def main():
    generator = np.random.default_rng()
    # For each user, decide how many conversations to have
    # For each user, pick a number of task-target pairs following a power law distribution
    # For each task, generate task data

    with open('config.json', 'r') as f:
        config = json.load(f)
    
    with open('names.json', 'r') as f:
        names = json.load(f)
    
    assert len(names) >= NUM_USERS
    names = names[:NUM_USERS]
    
    all_tasks = []

    for server_id, server_config in config['servers'].items():
        for ideal_task in server_config['idealTasks']:
            all_tasks.append((server_id, ideal_task))

    #all_tasks += [None, None, None, None, None]

    user_budgets = generate_discrete_power_law(NUM_USERS, 0.1, MIN_CONVERSATIONS, TOTAL_CONVERSATIONS)
    print(user_budgets)

    indices = np.arange(len(all_tasks))


    all_actions = []

    for user_name, user_budget in zip(names, user_budgets):
        action_budgets = generate_discrete_power_law(NUM_ACTIONS, 0.1, 1, user_budget)

        chosen_indices = generator.choice(indices, NUM_ACTIONS, replace=False)
        
        chosen_tasks = [all_tasks[chosen_index] for chosen_index in chosen_indices]

        for chosen_task, action_budget in zip(chosen_tasks, action_budgets):
            for i in range(action_budget):
                data = mock_tasks.__dict__[chosen_task[1]]()
                all_actions.append((user_name, chosen_task, data))
    
    generator.shuffle(all_actions)

    with open('actions.json', 'w') as f:
        json.dump(all_actions, f, indent=2)

    print(all_actions)

if __name__ == '__main__':
    main()