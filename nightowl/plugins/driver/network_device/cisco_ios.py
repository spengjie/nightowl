import re

from .base import NetworkDeviceDriverBase
from nightowl.models.nom.network_device import Router
from nightowl.plugins.parser.cisco import cisco_ios_interfaces, cisco_ios_route_table


class DriverPlugin(NetworkDeviceDriverBase):
    name = 'Cisco IOS Router'
    data_model = Router
    parsers = [cisco_ios_interfaces, cisco_ios_route_table]
    netmiko_device_type = 'cisco_ios'
    name_regex = re.compile(r'^(\S+)[>#]', re.M)
    config_command = 'show running-config'
