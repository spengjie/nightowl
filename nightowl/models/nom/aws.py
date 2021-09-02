import os

from mongoengine import fields

from nightowl.models import cusfields
from nightowl.models.nom.base import (
    NetworkInterface as NI, NetworkLink, NetworkNode, NetworkObjectRef)


class AWSCloud(NetworkNode):
    account_id = fields.StringField(required=True)
    fields.DynamicField

    is_group = True
    driver = 'nightowl.plugins.driver.aws.aws'
    type_icon = '/icons/aws-resource/group/aws-cloud.svg'
    icon = '/icons/aws-resource/group/aws-cloud.svg'
    color = '#242f3e'


class AWSService(NetworkNode):
    aws_tags = fields.ListField(field=fields.DictField())

    meta = {
        'allow_inheritance': True,
    }


class AWSNetworkInterface(NI):
    meta = {
        'allow_inheritance': True,
    }


class VPC(AWSService):
    cidr_block = fields.StringField(required=True)
    subnets = fields.EmbeddedDocumentListField(NetworkObjectRef)
    internet_gateway = fields.EmbeddedDocumentField(NetworkObjectRef)
    main_route_table = fields.EmbeddedDocumentField(NetworkObjectRef)
    main_network_acl = fields.EmbeddedDocumentField(NetworkObjectRef)

    is_group = True
    driver = 'nightowl.plugins.driver.aws.vpc'
    type_icon = '/icons/aws-service/networking-and-content-delivery/vpc.svg'
    icon = '/icons/aws-resource/group/vpc.svg'
    color = '#248814'


class Subnet(AWSService):
    cidr_block = fields.StringField(required=True)
    availability_zone = fields.StringField(required=True)
    vpc = fields.EmbeddedDocumentField(NetworkObjectRef, required=True)
    route_table = fields.EmbeddedDocumentField(NetworkObjectRef)
    network_acl = fields.EmbeddedDocumentField(NetworkObjectRef)

    is_group = True
    driver = 'nightowl.plugins.driver.aws.subnet'
    type_icon = '/icons/aws-resource/group/vpc-subnet.svg'
    icon = '/icons/aws-resource/group/vpc-subnet.svg'
    color = '#248814'


class EC2(AWSService):
    instance_type = fields.StringField(required=True)
    availability_zone = fields.StringField(required=True)
    vpc = fields.EmbeddedDocumentField(NetworkObjectRef, required=True)
    subnet = fields.EmbeddedDocumentField(NetworkObjectRef, required=True)
    launch_time = cusfields.DateTimeField(required=True)

    driver = 'nightowl.plugins.driver.aws.ec2'
    type_icon = '/icons/aws-service/compute/ec2.svg'

    @property
    def icon(self):
        instance_type = self.instance_type.split(".")[0]  # pylint: disable=no-member
        specific_icon = f'/icons/aws-resource/compute/ec2_{instance_type}.svg'
        if os.path.exists(f'./nightowl/app/static{specific_icon}'):
            return specific_icon
        return '/icons/aws-resource/compute/ec2_instance.svg'


class InternetGateway(AWSNetworkInterface):
    driver = 'nightowl.plugins.driver.aws.internet_gateway'
    icon = '/icons/aws-resource/networking-and-content-delivery/internet-gateway.svg'
    color = '#4D27AA'


class NetworkInterface(AWSNetworkInterface):
    driver = 'nightowl.plugins.driver.aws.network_interface'
    icon = '/icons/aws-resource/networking-and-content-delivery/elastic-network-interface.svg'
    color = '#4D27AA'


class VPCPeering(NetworkLink):
    icon = '/icons/aws-resource/networking-and-content-delivery/vpc-peering-connection.svg'
    color = '#4D27AA'
