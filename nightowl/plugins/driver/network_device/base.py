from nightowl.models.nom.network_device import NetworkDeviceConfig
from nightowl.plugins.driver.cli import CLIDriverBase


class NetworkDeviceDriverBase(CLIDriverBase):
    config_command = None

    def update_config(self, config_outputs):
        config = NetworkDeviceConfig()
        config._id = self.noid
        config.config = config_outputs
        config.save()
        return config
