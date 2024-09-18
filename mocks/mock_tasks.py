import datetime
import random

def _random_date():
    chosen_date = datetime.datetime.now() - datetime.timedelta(days=random.randint(1, 365))
    # YYYY-MM-DD
    return chosen_date.strftime('%Y-%m-%d')

def _random_date_range():
    chosen_date = datetime.datetime.now() - datetime.timedelta(days=random.randint(1, 365))
    other_date = chosen_date + datetime.timedelta(days=random.randint(1, 20))

    return chosen_date.strftime('%Y-%m-%d'), other_date.strftime('%Y-%m-%d')

def queryWeather():
    return {
        'date': _random_date()
    }

def bookRoom():
    start_date, end_date = _random_date_range()
    return {
        'startDate': start_date,
        'endDate': end_date
    }

def suggestRestaurant():
    return {
        'date': _random_date()
    }

def rentSki():
    return {
        'date': _random_date(),
        'type': random.choice(["racing", "carving", "backcountry"])
    }

def currentWeather():
    return {}

def menu():
    return {}

def openingTimes():
    return {}

ENGLISH_NAMES = ['Brooke', 'Toby', 'Maxwell', 'Cliff', 'Manfred', 'Valerie', 'Kara', 'Nina', 'Madge', 'Laurel']
ENGLISH_SURNAMES = ['Smith', 'Jones', 'Johnson', 'Brown', 'Williams', 'Miller', 'Taylor', 'Wilson', 'Davis', 'White']

def bookTable():
    return {
        'fullName': f'{random.choice(ENGLISH_NAMES)} {random.choice(ENGLISH_SURNAMES)}',
        'date': _random_date(),
        'numPeople': random.randint(1, 10),
        'hour': random.randint(16, 23)
    }

def orderEverything():
    return {
        'deliveryAddress': f'{random.randint(1, 100)} {random.choice(ENGLISH_SURNAMES)} Street',
    }

def _get_movie_date():
    return f'2024-03-{random.randint(15, 18)}', # Note that there are no movies on the 18th

def availableMovies():
    return {
        'date': _get_movie_date()
    }

MOVIES = ['Forrest Gump', 'Stand by Me', 'The Silence of the Lambs']

def buyTickets():
    return {
        'date': _get_movie_date(),
        'hour': random.choice([18, 20]),
        'numTickets': random.randint(1, 6),
        'movie': random.choice(MOVIES)
    }

def callTaxi():
    return {
        'address': f'{random.randint(1, 100)} {random.choice(ENGLISH_SURNAMES)} Street',
        'time': f'{random.randint(0, 23)}:{random.randint(0, 59)}'
    }

CITIES = ['New York', 'Los Angeles', 'London', 'Vienna', 'Tokyo', 'Zurich', 'Cairo', 'Rome']

def getTraffic():
    return {
        'date': _random_date(),
        'location': random.choice(CITIES)
    }