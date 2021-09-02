from mongoengine.errors import DoesNotExist

from nightowl.models.nom import NetworkObjectSettings
from nightowl.models.nom.aws import EC2
from nightowl.plugins.adapter.base import AdapterBase
from nightowl.plugins.connection import aws as aws_connection
from nightowl.utils.datetime import str_to_datetime


class AdapterPlugin(AdapterBase):
    name = 'CloudWatch'

    def __init__(self, context, noid):
        super().__init__(context, noid)
        if isinstance(self.network_object, EC2):
            self.namespace = 'AWS/EC2'
            self.dimensions = [{'Name': 'InstanceId', 'Value': noid}]
        else:
            raise TypeError('Unsupported network object type')
        settings = self.network_object.settings.to_dict()
        aws_access_key_data = settings['credentials'].get('aws_access_key')
        if not aws_access_key_data:
            raise ValueError('No AWS access key in settings')
        self.connection = aws_connection.ConnectionPlugin(
            context,
            'cloudwatch',
            region_name=aws_access_key_data['region_name'],
            aws_access_key_id=aws_access_key_data['access_key'],
            aws_secret_access_key=aws_access_key_data['secret_key'])

    def run(self, metric, start_time, end_time, period,
            statistics=None, extended_statistics=None, unit=None):
        start_time = str_to_datetime(start_time)
        end_time = str_to_datetime(end_time)
        if statistics is None and extended_statistics is None:
            raise ValueError("At least one of the parameters 'statistics' "
                             "or 'extended_statistics' must be specified.")

        metric_name = metric.name
        metric = self.connection.resource.Metric(self.namespace, metric_name)
        statistics_args = {
            'Dimensions': self.dimensions,
            'StartTime': start_time,
            'EndTime': end_time,
            'Period': period,
        }
        if statistics:
            statistics_args['Statistics'] = statistics
        if extended_statistics:
            statistics_args['ExtendedStatistics'] = extended_statistics
        if unit:
            statistics_args['Unit'] = unit
        statistics_response = metric.get_statistics(**statistics_args)
        data = []
        for datapoint in statistics_response['Datapoints']:
            data.append({
                'time': datapoint.pop('Timestamp'),
                'unit': datapoint.pop('Unit', None),
                **datapoint,
            })
        data.sort(key=lambda x: x['time'])
        return {
            '_id': metric_name,
            'name': metric_name,
            'data': data,
        }

    def get_metrics(self):
        return self.connection.resource.metrics.filter(
            Namespace='AWS/EC2',
            Dimensions=self.dimensions)

    def get_metric(self, metric_id):
        return self.connection.resource.Metric(self.namespace, metric_id)
