import json
import os
import random

import requests as request_manager

import databases.mongo as mongo
import databases.sql as sql
from toolformers.base import Tool, StringParameter

from utils import get_query_id

TOOLS = []
ADDITIONAL_INFO = ''
NODE_URLS = {}

def get_additional_info():
    return ADDITIONAL_INFO

def add_mongo_database(external_name, schema):
    global ADDITIONAL_INFO
    # TODO: Support hot-loading?
    mongo.create_database_from_schema(external_name, schema)

    ADDITIONAL_INFO += f'You have access to a MongoDB database.\n'
    ADDITIONAL_INFO += 'The database has the following collections (with schemas):\n\n'

    for collection_name, collection_schema in schema['collections'].items():
        ADDITIONAL_INFO += f'=={collection_name}==\n'

        if 'startingValues' in collection_schema:
            del collection_schema['startingValues']

        ADDITIONAL_INFO += json.dumps(collection_schema, indent=2) + '\n\n'

def add_mongo_tools(server_name):
    def insert_element(collection, doc):
        doc = json.loads(doc)
        mongo.insert_one(server_name, collection, doc)
        return 'Done'

    insert_element_tool = Tool('insert_into_database', 'Insert into a database (MongoDB).', [
        StringParameter('collection', 'The collection to insert into', True),
        StringParameter('doc', 'The document to insert, as a formatted JSON string for MongoDB', True)
    ], insert_element)

    def query_database(collection, query):
        query = json.loads(query)
        output = mongo.query_database(server_name, collection, query)
        print(output)
        return json.dumps(output)

    find_in_database_tool = Tool('find_in_database', 'Find in a database (MongoDB). Returns a JSON formatted string with the result.', [
        StringParameter('collection', 'The collection to query', True),
        StringParameter('query', 'The query to run, as a formatted JSON string for MongoDB', True)
    ], query_database)

    def update_element(collection, query, update):
        query = json.loads(query)
        update = json.loads(update)
        mongo.update_one(server_name, collection, query, update)
        return 'Done'

    update_element_tool = Tool('update_one_in_database', 'Update an element in a database (MongoDB).', [
        StringParameter('collection', 'The collection to query', True),
        StringParameter('query', 'The query to run, as a formatted JSON string for MongoDB', True),
        StringParameter('update', 'The update to run, as a formatted JSON string for MongoDB. Remember the $ operator (e.g. {$set : {...}})', True)
    ], update_element)

    def delete_element(collection, query):
        query = json.loads(query)
        mongo.delete_one(server_name, collection, query)
        return 'Done'

    delete_element_tool = Tool('delete_element_in_database', 'Delete an element in a database (MongoDB).', [
        StringParameter('database', 'The database to query', True),
        StringParameter('collection', 'The collection to query', True),
        StringParameter('query', 'The query to run, as a formatted JSON string for MongoDB', True)
    ], delete_element)

    TOOLS.append(insert_element_tool)
    TOOLS.append(find_in_database_tool)
    TOOLS.append(update_element_tool)
    TOOLS.append(delete_element_tool)

    # TODO: Test insert and delete tools

def add_sql_database(table_schemas, server_name):
    global ADDITIONAL_INFO
    name_mappings = sql.create_database_from_schema(table_schemas, server_name)

    global ADDITIONAL_INFO

    ADDITIONAL_INFO += f'\n\nYou have access to an SQL Server database. You can run SQL queries on the database. The database has the following tables:\n\n'
    for table_name, table_schema in table_schemas.items():
        ADDITIONAL_INFO += f'=={table_name}==\n'
        ADDITIONAL_INFO += f'Description: {table_schema["description"]}\n'

        ADDITIONAL_INFO += 'Columns:\n'

        for column_name, column_data in table_schema['columns'].items():
            ADDITIONAL_INFO += f'\n- {column_name}: {column_data}'


        constraints = table_schema.get('constraints', [])
        if len(constraints) > 0:
            print('Constraints:', constraints)
            ADDITIONAL_INFO += '\n\nConstraints:\n'
            for constraint in constraints:
                ADDITIONAL_INFO += f'\n- {constraint}'

        extra_table_schema_info = table_schema.get('extraInfo', '')

        if extra_table_schema_info:
            ADDITIONAL_INFO += '\n\nOther info:' + extra_table_schema_info

        for starting_value in table_schema.get('startingValues', []):
            sql.insert(table_name, server_name, starting_value)
        
        ADDITIONAL_INFO += '\n\n========\n\n'
    
    ADDITIONAL_INFO += '\n'
    ADDITIONAL_INFO += 'For security reasons, you are not allowed to create other tables or modify the schema of the existing tables.\n\n'

    return name_mappings

def add_sql_tools(name_mappings):
    def run_query(query):
        for internal_table_name, external_table_name in name_mappings.items():
            query = query.replace(internal_table_name, external_table_name)
        print('Running SQL query:', query)
        response = sql.run_query(query)
        print('SQL Response:', response)
        return response
    
    tool_description = 'Run an SQL query. Returns a JSON-formatted list of results, where each element is an object ' \
        'with the column names as keys. You might need to parse it. If the query does not return any results, \"No results\" is returned.'

    query_tool = Tool('run_sql_query', tool_description, [
        StringParameter('query', 'The query to run', True)
    ], run_query)

    TOOLS.append(query_tool)


def prepare_mock_tool(tool_schema, internal_name):
    input_schema = tool_schema['input']

    required_parameter_names = input_schema['required']
    parameters = []

    for parameter_name, parameter_data in input_schema['properties'].items():
        if parameter_data['type'] == 'string':
            parameters.append(StringParameter(parameter_name, parameter_data['description'], parameter_name in required_parameter_names))
        else:
            raise ValueError('Unknown parameter type:', parameter_data['type'])

    def run_mock_tool(*args, **kwargs):
        return json.dumps(random.choice(tool_schema['mockValues']))

    mock_tool = Tool(internal_name, tool_schema['description'], parameters, run_mock_tool, output_schema=tool_schema['output'])

    return mock_tool

def prepare_external_tool(tool_schema, internal_name, external_server_name):
    input_schema = tool_schema['input']

    required_parameter_names = input_schema['required']
    parameters = []

    for parameter_name, parameter_data in input_schema['properties'].items():
        if parameter_data['type'] == 'string':
            parameters.append(StringParameter(parameter_name, parameter_data['description'], parameter_name in required_parameter_names))
        else:
            raise ValueError('Unknown parameter type:', parameter_data['type'])
        
    helper_id = os.environ.get('AGENT_ID') + '_helper'
    helper_url = NODE_URLS[helper_id]

    def run_external_tool(*args, **kwargs):
        for i, arg in enumerate(args):
            argument_name = parameters[i].name
            kwargs[argument_name] = arg

        # TODO: Check that the parameter names are correct?

        print('Running external tool:', internal_name, kwargs)
        query_parameters = {
            'type' : internal_name, # TODO: Use the schema name instead? Must be matched on the other side
            'data' : kwargs,
            'targetServer' : external_server_name,
            'queryId': get_query_id()
        }
        response = request_manager.post(helper_url + '/customRun', json=query_parameters)

        print('Response from external tool:', response.text)

        if response.status_code == 200:
            parsed_response = json.loads(response.text)

            return json.dumps(parsed_response)
            #if parsed_response['status'] == 'success':
            #    return parsed_response['body']
        return 'Failed to call the tool: ' + response.text

    external_tool = Tool(internal_name, tool_schema['description'], parameters, run_external_tool, output_schema=tool_schema['output'])

    return external_tool

def load_config(server_name):
    global ADDITIONAL_INFO
    with open('config.json') as f:
        config = json.load(f)

    with open('node_urls.json') as f:
        node_urls = json.load(f)
    for node_id, node_url in node_urls.items():
        NODE_URLS[node_id] = node_url
    
    server_config = config['servers'][server_name]

    ADDITIONAL_INFO += 'This is the description of the service provided by the server:\n====\n'
    ADDITIONAL_INFO += server_config['description']

    for action_description in server_config['actionDescriptions']:
        ADDITIONAL_INFO += f'\n- {action_description}'
    
    ADDITIONAL_INFO += '\n====\n\n'

    if server_config['internalDbSchema'] is not None:
        db_config = config['dbSchemas'][server_config['internalDbSchema']]

        if db_config['dbType'] == 'mongo':
            add_mongo_database(server_name, db_config)
            add_mongo_tools(server_name)
        elif db_config['dbType'] == 'sql':
            name_mappings = add_sql_database(db_config['tables'], server_name)
            add_sql_tools(name_mappings)
        else:
            raise ValueError('Unknown database type:', db_config['dbType'])

    for internal_name, schema_name in server_config.get('mockTools', {}).items():
        tool_schema = config['toolSchemas'][schema_name]
        tool = prepare_mock_tool(tool_schema, internal_name)
        TOOLS.append(tool)

    for internal_name, external_tool_config in server_config.get('externalTools', {}).items():
        schema_name = external_tool_config['schema']
        tool_schema = config['toolSchemas'][schema_name]
        tool_server = external_tool_config['server']
        tool = prepare_external_tool(tool_schema, internal_name, tool_server)
        TOOLS.append(tool)

    print('Final additional info:', ADDITIONAL_INFO)
    print('Final tools:', TOOLS)