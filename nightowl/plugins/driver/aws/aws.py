from mongoengine.errors import DoesNotExist

from nightowl.plugins.connection import aws as aws_connection
from nightowl.models.nom.aws import AWSCloud
from nightowl.plugins.driver.base import DriverBase
from nightowl.utils.datetime import utc_now
from nightowl.utils.model import import_model


class DriverPlugin(DriverBase):
    data_model = AWSCloud

    def discover(self, aws_access_key):
        connection = aws_connection.ConnectionPlugin(
            self.context,
            'sts',
            region_name=aws_access_key.region_name,
            aws_access_key_id=aws_access_key.access_key,
            aws_secret_access_key=aws_access_key.secret_key)
        response = connection.client.get_caller_identity()
        account_id = response['Account']
        try:
            # pylint: disable=no-member
            network_object = self.data_model.objects.get(pk=account_id)
        except DoesNotExist:
            network_object = self.data_model()  # pylint: disable=not-callable
            network_object._id = f'aws-{account_id}'
            network_object.account_id = account_id
            network_object.name = account_id
        network_object.last_discovered_at = utc_now()
        network_object.save()
        self.service_names = ['vpc', 'internet_gateway', 'network_interface', 'subnet', 'ec2']
        for service_name in self.service_names:
            service_driver = import_model(f'nightowl.plugins.driver.aws.{service_name}', 'DriverPlugin')
            service_driver.discover_resources(self.context, aws_access_key)
