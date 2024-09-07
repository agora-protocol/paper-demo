import json
import os

import pymongo

client = pymongo.MongoClient(os.environ.get('MONGODB_URI'))

def create_database_from_schema(name, schema):
    db = client[name]

    for collection_name, collection_schema in schema['collections'].items():
        db.create_collection(collection_name)
        collection = db[collection_name]
        for doc in collection_schema['startingValues']:
            collection.insert_one(dict(doc))

def update_one(database, collection, query, update):
    db = client[database]
    collection = db[collection]
    collection.update_one(query, update)

def parse_mongo_output(output):
    # Replace the ObjectId with a string
    if '_id' in output:
        output['_id'] = str(output['_id'])
    return output

def full_reset():
    # Get all databases and drop them
    for db_name in client.list_database_names():
        if db_name in ['admin', 'config', 'local']:
            continue
        db = client[db_name]
        for collection_name in db.list_collection_names():
            db[collection_name].delete_many({})
        client.drop_database(db_name)

def query_database(database, collection, query):
    db = client[database]
    collection = db[collection]
    return [parse_mongo_output(x) for x in collection.find(query)]