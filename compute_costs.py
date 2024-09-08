from databases.mongo import query_database

COSTS = {
    'gpt-4o' : {
        'prompt_tokens' : 5e-6,
        'completion_tokens' : 15e-6
    },
    'gpt-4o-mini' : {
        'prompt_tokens' : 0.15e-6,
        'completion_tokens' : 0.6e-6
    }
}

def main():
    # Retrieve the costs from the database
    costs = query_database('usageLogs', 'main', {})

    total_cost = 0

    for cost in costs:
        model = cost['model']
        total_cost += cost['prompt_tokens'] * COSTS[model]['prompt_tokens']
        total_cost += cost['completion_tokens'] * COSTS[model]['completion_tokens']
    
    print(f'Total cost: {total_cost}')

if __name__ == '__main__':
    main()