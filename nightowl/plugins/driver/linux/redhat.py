import re

from .base import LinuxDriverBase
from nightowl.models.nom.server import Linux


class DriverPlugin(LinuxDriverBase):
    name = 'Red Hat'
    data_model = Linux
    name_regex = re.compile(r'@(\S+)', re.M)
