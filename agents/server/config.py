import json

import databases.mongo as mongo
from toolformers.base import Tool, StringParameter

TOOLS = []
ADDITIONAL_INFO = ''
def get_additional_info():
    return ADDITIONAL_INFO

def add_mongo_database(internal_name, external_name, schema):
    global ADDITIONAL_INFO
    # TODO: Support hot-loading?
    mongo.create_database_from_schema(external_name, schema)

    ADDITIONAL_INFO += f'You have access to a database named {internal_name}.\n'
    ADDITIONAL_INFO += 'The database has the following collections (with schemas):\n\n'

    for collection_name, collection_schema in schema['collections'].items():
        ADDITIONAL_INFO += f'=={collection_name}==\n'
        ADDITIONAL_INFO += json.dumps(collection_schema, indent=2) + '\n\n'

def add_mongo_tools(name_mappings):
    def query_database(database, collection, query):
        query = json.loads(query)
        external_name = name_mappings[database]
        output = mongo.query_database(external_name, collection, query)
        print(output)
        return json.dumps(output)


    find_in_database_tool = Tool('find_in_database', 'Find in a database (MongoDB).', [
        StringParameter('database', 'The database to query', True),
        StringParameter('collection', 'The collection to query', True),
        StringParameter('query', 'The query to run, as a formatted JSON string for MongoDB', True)
    ], query_database)

    def update_element(database, collection, query, update):
        query = json.loads(query)
        update = json.loads(update)
        external_name = name_mappings[database]
        mongo.update_one(external_name, collection, query, update)
        return 'Done'

    update_element_tool = Tool('update_element_in_database', 'Update an element in a database (MongoDB).', [
        StringParameter('database', 'The database to query', True),
        StringParameter('collection', 'The collection to query', True),
        StringParameter('query', 'The query to run, as a formatted JSON string for MongoDB', True),
        StringParameter('update', 'The update to run, as a formatted JSON string for MongoDB', True)
    ], update_element)

    TOOLS.append(find_in_database_tool)
    TOOLS.append(update_element_tool)

def load_config(server_name):
    global ADDITIONAL_INFO
    with open('config.json') as f:
        config = json.load(f)
    
    server_config = config['servers'][server_name]

    ADDITIONAL_INFO += 'This is the description of the service provided by the server:\n====\n'
    ADDITIONAL_INFO += server_config['description']

    for action_description in server_config['actionDescriptions']:
        ADDITIONAL_INFO += f'\n- {action_description}'
    
    ADDITIONAL_INFO += '\n====\n\n'

    databases = []

    if server_config['internalDbSchema'] is not None:
        databases.append(('internalDb', server_name, server_config['internalDbSchema']))
    
    databases += [(x, x, x) for x in server_config['externalDbs']]
    
    has_mongo_db = False
    for internal_name, external_name, schema_name in databases:
        schema = config['dbSchemas'][schema_name]
        if schema['dbType'] == 'mongo':
            add_mongo_database(internal_name, external_name, schema)
            has_mongo_db = True
    
    if has_mongo_db:
        add_mongo_tools({x[0]: x[1] for x in databases})
