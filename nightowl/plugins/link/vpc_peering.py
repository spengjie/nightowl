import boto3
from mongoengine.errors import DoesNotExist

from nightowl.models.modules.credentials import AWSAccessSKey
from nightowl.models.nom import LinkType
from nightowl.models.nom.aws import VPCPeering
from nightowl.plugins.link.base import LinkBase
from nightowl.utils.aws import get_name


class LinkPlugin(LinkBase):
    name = 'VPC Peering'

    def build(self):
        aws_access_keys = AWSAccessSKey.objects().order_by('alias')
        for aws_access_key in aws_access_keys:
            settings = {
                'region_name': aws_access_key.region_name,
                'aws_access_key_id': aws_access_key.access_key,
                'aws_secret_access_key': aws_access_key.secret_key,
            }
            session = boto3.session.Session(**settings)
            resource = session.resource('ec2')
            for peering in resource.vpc_peering_connections.filter(
                    Filters=[{'Name': 'status-code', 'Values': ['active']}]):
                try:
                    # pylint: disable=no-member
                    vpc_peering = VPCPeering.objects.get(pk=peering.id)
                except DoesNotExist:
                    vpc_peering = VPCPeering()
                    vpc_peering._id = peering.id
                    vpc_peering.name = get_name(peering.tags, peering.id)
                    vpc_peering.noid1 = peering.requester_vpc_info['VpcId']
                    vpc_peering.noid2 = peering.accepter_vpc_info['VpcId']
                    vpc_peering.link_type = LinkType.TO_PEER
                vpc_peering.save()
