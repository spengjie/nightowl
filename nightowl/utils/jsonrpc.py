import json
import uuid

import requests
from flask import request

from nightowl.utils.flask import JSONEncoder


class JsonRpcServer:

    def __init__(self, app):
        self.app = app
        self.app.add_url_rule('/', 'index', self.receive, methods=('POST', ))

    def receive(self):
        request_data = request.get_json()
        if request_data is None:
            return {
                'jsonrpc': '2.0',
                'error': {
                    'code': -32700,
                    'message': 'Parse error',
                },
                'id': None,
            }
        request_id = request_data.get('id')
        if not request_id:  # It is a notification
            return {
                'jsonrpc': '2.0',
                'error': {
                    'code': -32600,
                    'message': 'Invalid Request',
                },
                'id': None,
            }
        func_name = request_data.get('method')
        if not func_name or not hasattr(self, func_name):
            return {
                'jsonrpc': '2.0',
                'error': {
                    'code': -32601,
                    'message': 'Method not found',
                },
                'id': request_id,
            }
        func = getattr(self, func_name)
        params = request_data.get('params', {})
        args = params.pop('_', [])
        kwargs = params
        try:
            result = func(*args, **kwargs)
        except Exception as ex:
            ex_type = type(ex)
            return {
                'jsonrpc': '2.0',
                'error': {
                    'code': -32600,
                    'message': 'Invalid Request',
                    'data': {
                        'exception': {
                            'module': ex_type.__module__,
                            'name': ex_type.__name__,
                            'args': ex.args,
                        }
                    }
                },
                'id': request_id,
            }
        else:
            return {
                'jsonrpc': '2.0',
                'result': result,
                'id': request_id,
            }


class JsonRpcClient:

    def __init__(self, url):
        self.url = url

    def send(self, func, *args, **kwargs):
        request_id = str(uuid.uuid4())
        payload = json.dumps({
            'jsonrpc': '2.0',
            'method': func,
            'params': {'_': args, **kwargs},
            'id': str(uuid.uuid4()),
        }, cls=JSONEncoder)

        r = requests.post(self.url, data=payload, headers={
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        })
        try:
            return r.json()
        except Exception as ex:
            ex_type = type(ex)
            return {
                'jsonrpc': '2.0',
                'error': {
                    'code': -32000,
                    'message': 'Server error',
                    'data': {
                        'exception': {
                            'module': ex_type.__module__,
                            'name': ex_type.__name__,
                            'args': ex.args,
                        }
                    }
                },
                'id': request_id,
            }
