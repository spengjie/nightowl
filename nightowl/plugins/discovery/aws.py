from nightowl.models.modules.credentials import AWSAccessSKey
from nightowl.plugins.discovery.base import DiscoveryBase
from nightowl.plugins.driver.aws import aws as aws_driver


class DiscoveryPlugin(DiscoveryBase):
    name = 'AWS Discovery'

    def run(self):
        # pylint: disable=no-member
        aws_access_keys = AWSAccessSKey.objects().order_by('alias')
        for aws_access_key in aws_access_keys:
            driver_ins = aws_driver.DriverPlugin(self.context, None)
            driver_ins.discover(aws_access_key)
