from nightowl.models.nom.aws import VPC
from nightowl.plugins.driver.aws.base import AWSServiceDriverBase
from nightowl.plugins.parser.aws import vpc as property_parser


class DriverPlugin(AWSServiceDriverBase):
    name = 'AWS VPC'
    data_model = VPC
    property_parser = property_parser
    service_name = 'ec2'

    @classmethod
    def get_resources(cls, connection):
        return connection.resource.vpcs.all()
