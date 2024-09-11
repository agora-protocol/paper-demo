import sys
sys.path.append('.')

import dotenv
dotenv.load_dotenv()

import json
import os

import pymssql

def new_cursor():
    # We setup a new connection each time because pymssql
    # does not support concurrent queries for the same connection
    connection = pymssql.connect(
        server=os.environ.get('SQL_SERVER'),
        user=os.environ.get('SQL_USER'),
        password=os.environ.get('SQL_PASSWORD'),
        database=os.environ.get('SQL_DATABASE'),
        as_dict=True,
        autocommit=True
    )

    return connection.cursor()

def create_database_from_schema(table_schemas, server_name):
    name_mappings = {}
    for table_name, table_schema in table_schemas.items():
        actual_table_name = f'{server_name}_{table_name}'
        name_mappings[table_name] = actual_table_name

        infos = []
        
        for column_name, column_info in table_schema['columns'].items():
            infos.append(f'{column_name} {column_info}')

        for constraint in table_schema.get('constraints', []):
            infos.append(constraint)
        
        query = f"""
        CREATE TABLE {actual_table_name} (
            {', '.join(infos)}
        );
        """

        with new_cursor() as cursor:
            cursor.execute(query)
    
    return name_mappings

def run_query(query):
    with new_cursor() as cursor:
        cursor.execute(query)
        try:
            return json.dumps(cursor.fetchall())
        except Exception as e:
            if 'no resultset' in str(e):
                return 'No results'
            else:
                raise e

def insert(table_name, server_name, values):
    actual_table_name = f'{server_name}_{table_name}'
    columns = ', '.join(values.keys())
    values = ', '.join([f"'{x}'" for x in values.values()])
    query = f"""
    INSERT INTO {actual_table_name} ({columns}) VALUES ({values});
    """

    with new_cursor() as cursor:
        cursor.execute(query)
        return 'Done'

def get_all_tables():
    with new_cursor() as cursor:
        cursor.execute('SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES')
        result = cursor.fetchall()
        return [x['TABLE_NAME'] for x in result if x['TABLE_NAME'] != 'database_firewall_rules']

def reset_database():
    tables = get_all_tables()

    for table in tables:
        with new_cursor() as cursor:
            cursor.execute(f'DROP TABLE {table}')