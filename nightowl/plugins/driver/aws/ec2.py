from nightowl.models.nom.aws import EC2
from nightowl.plugins.driver.aws.base import AWSServiceDriverBase
from nightowl.plugins.parser.aws import ec2 as property_parser


class DriverPlugin(AWSServiceDriverBase):
    name = 'AWS EC2'
    data_model = EC2
    property_parser = property_parser
    service_name = 'ec2'

    @classmethod
    def get_resources(cls, connection):
        return connection.resource.instances.all()
