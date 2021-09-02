from mongoengine import fields

from nightowl.models.nom.base import NetworkInterface, NetworkNode


class Server(NetworkNode):
    host = fields.StringField(required=True)
    proxy = fields.UUIDField()

    meta = {
        'allow_inheritance': True,
    }


class LinuxNetworkInterface(NetworkInterface):
    meta = {
        'allow_inheritance': True,
    }

    type_icon = '/icons/server/linux.svg'


class Linux(Server):
    meta = {
        'allow_inheritance': True,
    }

    driver = 'nightowl.plugins.driver.cli.linux'
    type_icon = '/icons/server/linux.svg'
    icon = '/icons/server/linux.svg'


class Redhat(Linux):
    driver = 'nightowl.plugins.driver.cli.linux.redhat'
    icon = '/icons/server/redhat.png'
