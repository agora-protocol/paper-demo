from toolformers.base import Tool, StringParameter, EnumParameter

weather_tool = Tool('get_current_temperature', 'Get the current temperature for a specific location', [
    StringParameter('location', 'The city and state, e.g., San Francisco, CA', True),
    EnumParameter('unit', 'The temperature unit to use. Infer this from the user\'s location.', ['Celsius', 'Fahrenheit'], True)
], lambda **data: 'The temperature in ' + data['location'] + ' is 72 degrees ' + data['unit'])

rain_tool = Tool('get_rain_probability', 'Get the probability of rain for a specific location', [
    StringParameter('location', 'The city and state, e.g., San Francisco, CA', True)
], lambda **data: 'The probability of rain in ' + data['location'] + ' is 20%')

