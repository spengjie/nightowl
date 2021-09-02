import re

from mongoengine.errors import DoesNotExist
from netaddr import IPNetwork

from nightowl.models.nom import NetworkIPv4Address
from nightowl.models.nom.network_device import NetworkDeviceInterface
from nightowl.plugins.parser.base import ParserBase


'''Sample 1
ip-10-10-1-12#show interfaces
GigabitEthernet1 is up, line protocol is up
  Hardware is CSR vNIC, address is 0a30.a285.16a6 (bia 0a30.a285.16a6)
  Internet address is 10.10.1.12/24
  MTU 1500 bytes, BW 1000000 Kbit/sec, DLY 10 usec,
     reliability 255/255, txload 1/255, rxload 1/255
  Encapsulation ARPA, loopback not set
  Keepalive set (10 sec)
  Full Duplex, 1000Mbps, link type is auto, media type is Virtual
  output flow-control is unsupported, input flow-control is unsupported
  ARP type: ARPA, ARP Timeout 04:00:00
  Last input 00:00:00, output 00:00:00, output hang never
  Last clearing of "show interface" counters never
  Input queue: 0/375/0/0 (size/max/drops/flushes); Total output drops: 0
  Queueing strategy: fifo
  Output queue: 0/40 (size/max)
  5 minute input rate 0 bits/sec, 0 packets/sec
  5 minute output rate 0 bits/sec, 0 packets/sec
     103914 packets input, 5414445 bytes, 0 no buffer
     Received 0 broadcasts (0 IP multicasts)
     0 runts, 0 giants, 0 throttles
     0 input errors, 0 CRC, 0 frame, 0 overrun, 0 ignored
     0 watchdog, 0 multicast, 0 pause input
     109958 packets output, 8626460 bytes, 0 underruns
     0 output errors, 0 collisions, 1 interface resets
     0 unknown protocol drops
     0 babbles, 0 late collision, 0 deferred
     0 lost carrier, 0 no carrier, 0 pause output
     0 output buffer failures, 0 output buffers swapped out
VirtualPortGroup0 is up, line protocol is up
  Hardware is Virtual Port Group, address is 001e.f645.febd (bia 001e.f645.febd)
  Internet address is 192.168.35.101/24
  MTU 1500 bytes, BW 750000 Kbit/sec, DLY 1000 usec,
     reliability 255/255, txload 1/255, rxload 1/255
  Encapsulation ARPA, loopback not set
  Keepalive not supported
  ARP type: ARPA, ARP Timeout 04:00:00
  Last input never, output 4w3d, output hang never
  Last clearing of "show interface" counters never
  Input queue: 0/375/0/0 (size/max/drops/flushes); Total output drops: 0
  Queueing strategy: fifo
  Output queue: 0/40 (size/max)
  5 minute input rate 0 bits/sec, 0 packets/sec
  5 minute output rate 0 bits/sec, 0 packets/sec
     736 packets input, 51616 bytes, 0 no buffer
     Received 0 broadcasts (0 IP multicasts)
     0 runts, 0 giants, 0 throttles
     0 input errors, 0 CRC, 0 frame, 0 overrun, 0 ignored
     0 input packets with dribble condition detected
     1 packets output, 60 bytes, 0 underruns
     0 output errors, 0 collisions, 0 interface resets
     0 unknown protocol drops
     0 babbles, 0 late collision, 0 deferred
     0 lost carrier, 0 no carrier
     0 output buffer failures, 0 output buffers swapped out
'''


class ParserPlugin(ParserBase):

    def _parse(self, outputs):
        interfaces = []
        intf_blocks = re.findall(
            r'(^(\S+) is [ \S]+, line protocol is .+?)(?=^\S+|\Z)', outputs, re.M | re.S)
        device_name = self.network_object.name
        for intf_block, intf_name in intf_blocks:
            intf_id = f'{device_name}$${intf_name}'
            try:
                interface = NetworkDeviceInterface.objects.get(  # pylint: disable=no-member
                    pk=intf_id)
            except DoesNotExist:
                interface = NetworkDeviceInterface()
                interface._id = intf_id
                interface.noid = device_name
                interface.name = intf_name
            ip_search = re.search(r'Internet address is (\S+)/(\d+)', intf_block, re.M)
            addr, prefix_len = ip_search.groups() if ip_search else (None, None)
            if addr:
                ip_addr = f'{addr}/{prefix_len}'
                interface.ipv4_addrs = [NetworkIPv4Address(
                    addr=addr,
                    prefix_len=prefix_len,
                    subnet=f'{IPNetwork(ip_addr).network}/{prefix_len}',
                )]
            interfaces.append(interface)
        return interfaces

    def execute(self):
        intfs_outputs = self.driver.execute_command('show interfaces')
        if not intfs_outputs:
            return None
        return self._parse(intfs_outputs)
