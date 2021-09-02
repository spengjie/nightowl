from nightowl.models.nom.aws import NetworkInterface
from nightowl.plugins.driver.aws.base import AWSServiceDriverBase
from nightowl.plugins.parser.aws import network_interface as property_parser


class DriverPlugin(AWSServiceDriverBase):
    name = 'AWS Network Interface'
    data_model = NetworkInterface
    property_parser = property_parser
    service_name = 'ec2'

    @classmethod
    def get_resources(cls, connection):
        resources = connection.resource.network_interfaces.filter(
            Filters=[{'Name': 'attachment.status', 'Values': ['attached']}])
        return (res for res in resources if 'InstanceId' in res.attachment)
