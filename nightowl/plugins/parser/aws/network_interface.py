from nightowl.models.nom import NetworkIPv4Address
from nightowl.plugins.parser.aws.base import AWSPropertyParserBase
from nightowl.utils.aws import get_name


class ParserPlugin(AWSPropertyParserBase):

    def execute(self):
        network_object = self.network_object
        network_object.noid = self.resource.attachment['InstanceId']
        network_object.name = get_name(self.resource.tag_set, self.resource.id)
        network_object.aws_tags = [
            {'key': tag['Key'], 'value': tag['Value']} for tag in self.resource.tag_set]
        private_ip_address = self.resource.private_ip_address
        cidr_block = self.resource.subnet.cidr_block
        prefix_len = int(cidr_block.split('/')[1])
        network_object.ipv4_addrs = [NetworkIPv4Address(
            addr=private_ip_address,
            prefix_len=prefix_len,
            subnet=cidr_block,
        )]
        return network_object
