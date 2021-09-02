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
        network_object.subnets = [NetworkObjectRef(
            _id=subnet_res.id,
            name=get_name(subnet_res.tags, subnet_res.id),
        ) if subnet_res else None for subnet_res in self.resource.subnets.all()]

        igw_filter = list(self.resource.internet_gateways.all())
        internet_res = igw_filter[0] if igw_filter else None
        network_object.internet_gateway = NetworkObjectRef(
            _id=internet_res.id,
            name=get_name(internet_res.tags, internet_res.id),
        ) if internet_res else None

        rt_filter = list(self.resource.route_tables.filter(
            Filters=[{'Name': 'association.main', 'Values': ['true']}]))
        rt_res = rt_filter[0] if rt_filter else None
        network_object.main_route_table = NetworkObjectRef(
            _id=rt_res.id,
            name=get_name(rt_res.tags, rt_res.id),
        ) if rt_res else None

        nacl_filter = list(self.resource.network_acls.filter(
            Filters=[{'Name': 'default', 'Values': ['true']}]))
        nacl_res = nacl_filter[0] if nacl_filter else None
        network_object.main_network_acl = NetworkObjectRef(
            _id=nacl_res.id,
            name=get_name(nacl_res.tags, nacl_res.id),
        ) if nacl_res else None
        return network_object
