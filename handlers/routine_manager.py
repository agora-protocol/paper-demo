import sys
sys.path.append('.')

from pathlib import Path

from flask import Flask, request


app = Flask(__name__)


@app.route("/routines", methods=['GET'])
def get_routines():
    # List all routine files in the routines/ folder and strip the extension

    routines = [f.stem for f in Path('routines').iterdir() if f.is_file()]

    return {
        'status' : 200,
        'body' : routines
    }


@app.route("/call", methods=['POST'])
def call():
    protocol_hash = request.json['protocolHash']
    body = request.json['body']

    if Path(f'routines/{protocol_hash}.py').exists():
        routine = __import__(f'routines.{protocol_hash}')
        routine = getattr(routine, protocol_hash)

        if hasattr(routine, 'run'):
            # Note: this is ridiculously unsafe. In an actual production environment, all of this would be containerized
            output = routine.run(body)

            print('Routine output:', output)
            print('Output type:', type(output))

            return {
                'status' : 200,
                'body' : str(output)
            }
        else:
            return {
                'status' : 500,
                'error' : 'Misconfigured routine'
            }
    else:
        return {
            'status' : 400,
            'error' : 'Routine does not exist'
        }