from io import StringIO

from netmiko import ConnectHandler, SSHDetect
from paramiko import RSAKey

from nightowl.plugins.connection.base import ConnectionBase
from nightowl.utils.model import import_model


def transform_pkey(private_key):
    if not private_key:
        return private_key
    return RSAKey.from_private_key(StringIO(private_key))


class ConnectionPlugin(ConnectionBase):

    def __init__(self, context, netmiko_device_type, host, method='ssh', port=None,
                 username=None, password=None, private_key=None, private_key_file=None):
        self._validate(
            method=method,
            username=username,
            password=password,
            private_key=private_key,
            private_key_file=private_key_file,
        )
        super().__init__(context)
        use_keys = bool(private_key) or bool(private_key_file)
        self.netmiko_device_type = netmiko_device_type
        self.host = host
        self.method = method
        self.session = ConnectHandler(
            host=host, port=port, device_type=self.netmiko_device_type,
            username=username, password=password,
            use_keys=use_keys, pkey=transform_pkey(private_key), key_file=private_key_file)

    def _validate(self, **options):
        if options.get('method') != 'ssh':
            raise ValueError("'method' must be 'ssh'")
        if options.get('username') is None:
            raise ValueError("'username' must be set")
        if options.get('password') is None \
                and options.get('private_key') is None \
                and options.get('private_key_file') is None:
            raise ValueError(
                "Either 'password' or 'private_key' or 'private_key_file' must be set")

    @property
    def prompt(self):
        return self.session.find_prompt()

    def execute_command(self, command):
        return self.session.send_command(command)


def cli_auto_detect(value, **kwargs):
    settings = {
        'host': value,
        'port': kwargs.get('port'),
        'device_type': 'autodetect',
        'username': kwargs.get('username'),
        'use_keys': 'private_key' in kwargs or 'private_key_file' in kwargs,
        'pkey': transform_pkey(kwargs.get('private_key')),
        'key_file': kwargs.get('private_key_file'),
    }
    ssh_detect = SSHDetect(**settings)
    best_match = ssh_detect.autodetect()
    if best_match is not None:
        return import_model(f'nightowl.plugins.driver.cli.{best_match}', 'DriverPlugin')
    return None
