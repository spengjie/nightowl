import uuid
from datetime import datetime

import requests

from nightowl.plugins.adapter.base import AdapterBase
from nightowl.utils.datetime import add_tzinfo, str_to_datetime


class AdapterPlugin(AdapterBase):
    name = 'Zabbix'

    def __init__(self, context, noid):
        super().__init__(context, noid)
        zabbix_credentials = ''  # To be implemented
        self.api_url = zabbix_credentials.api_url
        self.username = zabbix_credentials.username
        self.password = zabbix_credentials.password
        self.token = self.get_token()
        self.host_id = self.get_host_id()

    def run(self, item, start_time, end_time):
        start_time = str_to_datetime(start_time)
        end_time = str_to_datetime(end_time)
        value_type = item['value_type']
        payload = {
            'jsonrpc': '2.0',
            'method': 'history.get',
            'params': {
                'history': value_type,
                'itemids': item['itemid'],
                'time_from': int(start_time.timestamp()),
                'time_till': int(end_time.timestamp()),
                'sortfield': 'clock',
                'sortorder': 'ASC',
            },
            'auth': self.token,
            'id': str(uuid.uuid4()),
        }
        r = requests.post(self.api_url, json=payload)
        result = self.get_jsonrpc_result(r, default=[])
        data = []
        for history in result:
            value = history['value']
            if value_type == '0':  # numeric float
                value = float(value)
            elif value_type == '3':  # numeric unsigned
                value = int(value)
            data.append({
                'time': add_tzinfo(
                    datetime.utcfromtimestamp(
                        float(f'{history["clock"]}.{history["ns"]}'))),
                'unit': item['units'],
                'value': value,
            })
        return {
            '_id': item['itemid'],
            'name': item['name'],
            'data': data,
        }

    def get_metrics(self):
        if not self.host_id:
            return []
        payload = {
            'jsonrpc': '2.0',
            'method': 'item.get',
            'params': {
                'hostids': self.host_id,
                'sortfield': 'name'
            },
            'auth': self.token,
            'id': str(uuid.uuid4()),
        }
        r = requests.post(self.api_url, json=payload)
        return self.get_jsonrpc_result(r, default=[])

    def get_metric(self, metric_id):
        if not self.host_id:
            return []
        payload = {
            'jsonrpc': '2.0',
            'method': 'item.get',
            'params': {
                'hostids': self.host_id,
                'itemids': metric_id,
                'sortfield': 'name'
            },
            'auth': self.token,
            'id': str(uuid.uuid4()),
        }
        r = requests.post(self.api_url, json=payload)
        result = self.get_jsonrpc_result(r)
        if result:
            return result[0]
        return None

    def get_token(self):
        payload = {
            'jsonrpc': '2.0',
            'method': 'user.login',
            'params': {
                'user': self.username,
                'password': self.password,
            },
            'id': str(uuid.uuid4()),
        }
        r = requests.post(self.api_url, json=payload)
        return self.get_jsonrpc_result(r)

    def get_host_id(self):
        payload = {
            'jsonrpc': '2.0',
            'method': 'host.get',
            'params': {
                'filter': {
                    'host': [
                        self.network_object.name,
                    ]
                }
            },
            'auth': self.token,
            'id': str(uuid.uuid4()),
        }
        r = requests.post(self.api_url, json=payload)
        result = self.get_jsonrpc_result(r)
        if result:
            return result[0]['hostid']
        return None

    def get_jsonrpc_result(self, r, default=None):
        if r.ok:
            response_data = r.json()
            if 'result' in response_data:
                return response_data['result']
        return default
