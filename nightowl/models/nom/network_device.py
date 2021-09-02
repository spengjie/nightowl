from mongoengine import fields
from mongoengine.errors import DoesNotExist

from nightowl.models.nom.base import DocumentBase, NetworkInterface, NetworkNode


class NetworkDeviceConfig(DocumentBase):
    _id = fields.StringField(primary_key=True)
    config = fields.StringField(required=True)


class NetworkDevice(NetworkNode):
    host = fields.StringField(required=True)
    proxy = fields.UUIDField()

    meta = {
        'allow_inheritance': True,
    }

    @staticmethod
    def get_config(noid):
        try:
            # pylint: disable=no-member
            settings = NetworkDeviceConfig.objects.get(pk=noid)
            return settings
        except DoesNotExist:
            return NetworkDeviceConfig()

    @property
    def config(self):
        return self.get_config(self._id)


class NetworkDeviceInterface(NetworkInterface):
    meta = {
        'allow_inheritance': True,
    }


class Router(NetworkDevice):
    driver = 'nightowl.plugins.driver.cli.cisco_ios'
    type_icon = '/icons/network-device/router.png'
    icon = '/icons/network-device/router.png'
