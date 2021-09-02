from mongoengine.errors import DoesNotExist

from nightowl.models.nom import LinkType, NetworkInterface
from nightowl.models.nom.l3_topology import L3Topology
from nightowl.plugins.link.base import LinkBase


class LinkPlugin(LinkBase):
    name = 'L3 Topology'

    def build(self):
        # pylint: disable=no-member
        for network_interface in NetworkInterface.objects(
                __raw__={'ipv4_addrs.addr': {'$ne': None}}):
            for ipv4_addr in network_interface.ipv4_addrs:
                l3_link_id = (f'{network_interface.noid}$${network_interface._id}'
                              f'$${ipv4_addr.addr}/{ipv4_addr.prefix_len}')
                try:
                    # pylint: disable=no-member
                    L3Topology.objects.get(pk=l3_link_id)
                    continue
                except DoesNotExist:
                    l3_link = L3Topology()
                    l3_link._id = l3_link_id
                    l3_link.name = network_interface.name
                    l3_link.noid1 = network_interface.noid
                    l3_link.noiid1 = network_interface._id
                    l3_link.noid2 = ipv4_addr.subnet
                    l3_link.link_type = LinkType.TO_MEDIUM
                    l3_link.save()
