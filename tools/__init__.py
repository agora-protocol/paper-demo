from .dummy import weather_tool, rain_tool

TOOLS = [weather_tool, rain_tool]

def call_tool(tool_name, **arguments):
    tool = next((tool for tool in TOOLS if tool.name == tool_name), None)

    if tool is not None:
        return tool.function(**arguments)
    else:
        return 'Tool not found'