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
        network_object.cidr_block = self.resource.cidr_block
        network_object.availability_zone = self.resource.availability_zone

        vpc_res = self.resource.vpc
        vpc_ref = NetworkObjectRef(
            _id=self.resource.vpc.id,
            name=get_name(vpc_res.tags, self.resource.vpc.id),
        ) if vpc_res else None
        network_object.group = vpc_ref
        network_object.vpc = vpc_ref

        rt_filter = list(vpc_res.route_tables.filter(
            Filters=[{'Name': 'association.subnet-id', 'Values': [self.resource.id]}])
        ) if vpc_res else None
        rt_res = rt_filter[0] if rt_filter else None
        network_object.route_table = NetworkObjectRef(
            _id=rt_res.id,
            name=get_name(rt_res.tags, rt_res.id),
        ) if rt_res else None

        nacl_filter = list(vpc_res.network_acls.filter(
            Filters=[{'Name': 'association.subnet-id', 'Values': [self.resource.id]}])
        ) if vpc_res else None
        nacl_res = nacl_filter[0] if nacl_filter else None
        network_object.network_acl = NetworkObjectRef(
            _id=nacl_res.id,
            name=get_name(nacl_res.tags, nacl_res.id),
        ) if nacl_res else None
        return network_object
