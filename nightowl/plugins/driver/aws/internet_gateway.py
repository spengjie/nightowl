from nightowl.models.nom.aws import InternetGateway
from nightowl.plugins.driver.aws.base import AWSServiceDriverBase
from nightowl.plugins.parser.aws import internet_gateway as property_parser


class DriverPlugin(AWSServiceDriverBase):
    name = 'AWS Internet Gateway'
    data_model = InternetGateway
    property_parser = property_parser
    service_name = 'ec2'

    @classmethod
    def get_resources(cls, connection):
        return connection.resource.internet_gateways.filter(
            Filters=[{'Name': 'attachment.state', 'Values': ['available']}])
