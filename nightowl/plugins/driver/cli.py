from mongoengine.errors import DoesNotExist

from .base import DriverBase
from nightowl.plugins.connection import cli


class CLIDriverBase(DriverBase):
    netmiko_device_type = None
    name_regex = None

    def __init__(self, context, noid):
        if not self.name_regex:
            raise ValueError("'name_regex' must be set")

        super().__init__(context, noid)
        settings = self.network_object.settings.to_dict()
        cli_credentials = settings['credentials'].get('cli_credentials')
        self.cli_connection = cli.ConnectionPlugin(
            context, self.netmiko_device_type,
            host=self.network_object.host,
            port=None,
            username=cli_credentials['username'],
            password=cli_credentials['password'],
            private_key=cli_credentials['private_key'],
            private_key_file=cli_credentials['private_key_file'])

    @property
    def prompt(self):
        return self.cli_connection.prompt

    def execute_command(self, command):
        return self.cli_connection.execute_command(command)

    def discover(self):
        name = self.parse_name()
        if not name:
            return []
        try:
            network_object = self.data_model.objects.get(name=name)
        except DoesNotExist:
            network_object = self.data_model()  # pylint: disable=not-callable
            network_object._id = name
        network_object.name = name
        network_object.ip = self.cli_connection.host
        self.benchmark()
        network_object.save()
        return [network_object]

    def parse_name(self):
        name_search = self.name_regex.search(self.prompt)
        if not name_search:
            return None
        search_groups = name_search.groups()
        return search_groups[0] if search_groups else name_search.group(0)
