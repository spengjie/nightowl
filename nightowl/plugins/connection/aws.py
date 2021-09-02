import boto3
from boto3.exceptions import ResourceNotExistsError

from nightowl.models.modules.credentials import AWSAccessSKey
from nightowl.plugins.connection.base import ConnectionBase


class ConnectionPlugin(ConnectionBase):

    def __init__(self, context, service_name, region_name,
                 aws_access_key_id, aws_secret_access_key):
        super().__init__(context)
        self.session = boto3.session.Session(
            region_name=region_name,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key)
        self.client = self.session.client(service_name)
        try:
            self.resource = self.session.resource(service_name)
        except ResourceNotExistsError:
            self.resource = self.client
