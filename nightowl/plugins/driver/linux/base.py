from mongoengine.errors import DoesNotExist

from nightowl.plugins.connection import cli
from nightowl.plugins.driver.base import DriverBase


class LinuxDriverBase(DriverBase):
    netmiko_device_type = 'linux'
