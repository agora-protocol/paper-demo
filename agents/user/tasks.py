"""TASK_INFOS = {
    'rental': {
        'description' : 'Rent a car',
        'parameters': {
            'pickup_location': {
                'type': 'string',
                'description': 'The location where the car will be picked up'
            },
            'pickup_date': {
                'type': 'date',
                'description': 'The date when the car will be picked up'
            },
            'return_location': {
                'type': 'string',
                'description': 'The location where the car will be returned'
            },
            'return_date': {
                'type': 'date',
                'description': 'The date when the car will be returned'
            },
            'car_type': {
                'type': 'enum',
                'description': 'The type of car to rent',
                'values': ['compact', 'midsize', 'fullsize', 'luxury']
            },
            'required': ['pickup_location', 'pickup_date', 'return_location', 'return_date', 'car_type']
        },
    }
}"""

TASK_SCHEMAS = {
    'addition' : {
        'description': 'Add two numbers',
        'parameters': {
            'number1': {
                'type': 'number',
                'description': 'The first number to add'
            },
            'number2': {
                'type': 'number',
                'description': 'The second number to add'
            },
            'required': ['number1', 'number2']
        }
    }
}





def get_task():
    # return 'rental', {
    #     'pickup_location': 'San Francisco, CA',
    #     'pickup_date': '2021-09-01',
    #     'return_location': 'San Francisco, CA',
    #     'return_date': '2021-09-05',
    #     'car_type': 'compact'
    # }

    return 'addition', {
        'number1': 2,
        'number2': 5
    }
