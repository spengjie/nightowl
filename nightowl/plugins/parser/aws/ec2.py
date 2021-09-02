from nightowl.models.nom import NetworkObjectRef
from nightowl.plugins.parser.aws.base import AWSPropertyParserBase
from nightowl.utils.aws import get_name


class ParserPlugin(AWSPropertyParserBase):

    def execute(self):
        network_object = self.network_object
        aws_tags = self.resource.tags or []
        network_object.name = get_name(aws_tags, self.resource.id)
        network_object.aws_tags = [
            {'key': tag['Key'], 'value': tag['Value']} for tag in aws_tags]
        network_object.instance_type = self.resource.instance_type
        network_object.availability_zone = self.resource.placement['AvailabilityZone']
        network_object.launch_time = self.resource.launch_time

        vpc_data = self.resource.vpc
        vpc_ref = NetworkObjectRef(
            _id=self.resource.vpc.vpc_id,
            name=get_name(vpc_data.tags, self.resource.vpc.vpc_id),
        ) if vpc_data else None
        subnet_data = self.resource.subnet
        subnet_ref = NetworkObjectRef(
            _id=subnet_data.subnet_id,
            name=get_name(subnet_data.tags, subnet_data.subnet_id),
        ) if subnet_data else None
        network_object.group = subnet_ref
        network_object.vpc = vpc_ref
        network_object.subnet = subnet_ref
        return network_object
