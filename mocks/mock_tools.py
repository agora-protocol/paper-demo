import random
import datetime

def weather(location, date):
    temperature = random.randint(-10, 30)
    precipitation = random.randint(0, 100)

    if precipitation > 50:
        if temperature > 0:
            return {
                'temperature': temperature,
                'precipitation': precipitation,
                'weather': 'rainy'
            }
        else:
            return {
                'temperature': temperature,
                'precipitation': precipitation,
                'weather': 'snowy'
            }
    else:
        return {
            'temperature': temperature,
            'precipitation': random.randint(0, 100),
            'weather': random.choice(['sunny', 'cloudy'])
        }

def currentDate():
    date_start = '2019-01-15'
    date_end = '2024-09-30'

    start = datetime.datetime.strptime(date_start, '%Y-%m-%d')
    end = datetime.datetime.strptime(date_end, '%Y-%m-%d')

    delta = end - start

    chosen_date = start + datetime.timedelta(days=random.randint(0, delta.days))

    return {
        'date': chosen_date.strftime('%Y-%m-%d')
    }

MENUS = {
    'italian': [
        {
            'name': 'Pizza Margherita',
            'price': 10
        },
        {
            'name': 'Carbonara',
            'price': 12
        },
        {
            'name': 'Lasagna',
            'price': 11
        }
    ],
    'chinese': [
        {
            'name': 'Kung Pao Chicken',
            'price': 15
        },
        {
            'name': 'Sweet and Sour Pork',
            'price': 14
        },
        {
            'name': 'Mapo Tofu',
            'price': 12
        }
    ],
    'indian': [
        {
            'name': 'Butter Chicken',
            'price': 16
        },
        {
            'name': 'Chana Masala',
            'price': 14
        },
        {
            'name': 'Palak Paneer',
            'price': 15
        }
    ],
    'british': [
        {
            'name': 'Fish and Chips',
            'price': 13
        },
        {
            'name': 'Shepherd\'s Pie',
            'price': 12
        },
        {
            'name': 'Bangers and Mash',
            'price': 11
        }
    ]
}

def getMenu(cuisineType):
    return {
        "menu": MENUS[cuisineType.lower()]
    }

def dayOfTheWeek(date):
    date_obj = datetime.datetime.strptime(date, '%Y-%m-%d')
    return {
        'day': date_obj.strftime('%A')
    }

def sendDriver(restaurant, address):
    return {
        'status': 'success'
    }

def trafficInfo(date, location):
    return {
        'traffic': random.choice(['clear', 'light', 'moderate', 'heavy', 'accident'])
    }

LETTERS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'

def getAvailableTaxi(time):
    available = random.random() < 0.85

    if available:
        taxis_id = random.choices(LETTERS, k=4) + random.choices('0123456789', k=2)
        return {
            'taxiId': ''.join(taxis_id)
        }
    else:
        return {
            'taxiId': None
        }
    
def assignTaxi(taxiId, time, address):
    return {
        'status': 'success'
    }