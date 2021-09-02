from nightowl.models.nom.aws import Subnet
from nightowl.plugins.driver.aws.base import AWSServiceDriverBase
from nightowl.plugins.parser.aws import subnet as property_parser


class DriverPlugin(AWSServiceDriverBase):
    name = 'AWS Subnet'
    data_model = Subnet
    property_parser = property_parser
    service_name = 'ec2'

    @classmethod
    def get_resources(cls, connection):
        return connection.resource.subnets.all()
