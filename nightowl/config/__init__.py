import hashlib
import json
import os
import platform

from pytz import timezone

from nightowl.utils.aws import get_secret_data


default_config = {
    'secrets_manager': {
        'region_name': 'cn-northwest-1',
        'secret_id': None,
    },
    'app': {
        'host': 'localhost',
        'port': 80,
        'ssl': False,
        'database': 'nightowl',
        'timezone': 'Asia/Shanghai',
        'log_file': None,
        'log_level': 'INFO',
        'scheduler_url': 'http://localhost:6100',
    },
    'scheduler': {
        'collection': 'scheduler_job',
        'timezone': 'Asia/Shanghai',
        'log_file': None,
        'log_level': 'INFO',
    },
    'worker': {
        'worker_pool_restarts': True,
        'log_file': None,
        'log_level': 'INFO',
        # http://docs.celeryproject.org/en/latest/userguide/configuration.html
        'mongodb_backend_settings': {
            'database': 'nightowl',
            'taskmeta_collection': 'worker_task',
            'groupmeta_collection': 'worker_group',
        },
    },
    'amqp': {
        'host': 'localhost',
        'username': None,
        'password': None,
    },
    'redis': {
        'host': 'localhost',
        'port': 6379,
        'ssl': False,
        'password': None,
        'max_connections': 20,
    },
    'mongodb': {
        'host': 'localhost',
        'port': 27017,
        'username': None,
        'password': None,
        'auth_source': 'admin',
        'auth_mechanism': 'SCRAM-SHA-256',
        'tls': False,
        'tls_certificate_key_file': None,
        'tls_certificate_key_file_password': None,
        'tls_ca_file': None,
    },
    'security': {
        'secret_key': None,
        'aes_iv': None,
        'rsa_public_key': None,
        'rsa_private_key': None,
        'rsa_private_key_passphrase': None,
    },
}


class Singleton(type):
    _instances = {}

    def __call__(self, *args, **kwargs):
        if self not in self._instances:
            self._instances[self] = super().__call__(*args, **kwargs)
        return self._instances[self]


class Config(metaclass=Singleton):

    def __init__(self):
        self.dict = default_config
        self._load_local_config()
        self._load_cloud_config()

    def __str__(self):
        return str(self.dict)

    def _load_local_config(self):
        if platform.system() == 'Windows':
            config_path = f'{os.environ["UserProfile"]}\\.nightowl\\nightowl.json'
        else:
            config_path = '/etc/nightowl/nightowl.json'
        try:
            with open(config_path, encoding='utf-8') as uf:
                local_config = json.loads(uf.read())
        except Exception:
            local_config = {}
        self.local_config = local_config
        self.dict = self._mixin(self.dict, self.local_config)

    def _load_cloud_config(self):
        secret_id = self.get('secrets_manager', 'secret_id')
        region_name = self.get('secrets_manager', 'region_name')
        if not secret_id:
            return
        cloud_data = get_secret_data(secret_id, region_name)
        if not cloud_data:
            return
        cloud_config = {}
        for key_str, value in cloud_data.items():
            keys = key_str.split('.')
            self._set_dict_value(cloud_config, *keys, value=value)
            self.set(value, *keys)
        self.cloud_config = cloud_config

    def _mixin(self, *configs):
        target = {}
        if not configs:
            return target
        for config in configs:
            if not isinstance(config, dict):
                continue
            for key in config:
                if isinstance(config[key], dict):
                    target[key] = self._mixin(target.get(key, {}), config[key])
                else:
                    target[key] = config[key]
        return target

    def get(self, *keys, default=None):
        result = self.dict
        for key in keys:
            if key in result:
                result = result[key]
            else:
                return default
        return result

    def set(self, value, *keys):
        self._set_dict_value(self.dict, *keys, value)

    @staticmethod
    def _set_dict_value(target, *keys, value):
        parent_keys = keys[:-1]
        leaf_key = keys[-1]
        current = target
        for key in parent_keys:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[leaf_key] = value


class ConfigReaderBase:
    base = None

    def __init__(self):
        self.config = Config()
        if self.base:
            self.dict = self.config.get(self.base)
        else:
            self.dict = self.config.dict

    def get(self, *keys, default=None):
        if self.base:
            keys = [self.base, *keys]
        return self.config.get(*keys, default=default)

    def set(self, value, *keys):
        if self.base:
            keys = [self.base, *keys]
        self.config.set(value, *keys)


class AppConfig(ConfigReaderBase):
    base = 'app'

    @property
    def host(self):
        return self.get('host')

    @property
    def port(self):
        return self.get('port', default=80)

    @property
    def ssl(self):
        return self.get('ssl', default=False)

    @property
    def base_url(self):
        ssl_str = 'https' if self.ssl else 'http'
        if (self.ssl and self.port == 443) or (not self.ssl and self.port == 80):
            port_str = ''
        else:
            port_str = f':{self.port}'
        return f'{ssl_str}://{self.host}{port_str}'

    @property
    def database(self):
        return self.get('database')

    @property
    def timezone(self):
        return timezone(self.get('timezone'))

    @property
    def log_file(self):
        log_file = self.get('log_file')
        if log_file:
            return log_file
        if platform.system() == 'Windows':
            return f'{os.environ["TEMP"]}\\nightowl\\app.log'
        else:
            return '/var/log/nightowl/app.log'

    @property
    def log_level(self):
        return self.get('log_level')

    @property
    def scheduler_url(self):
        return self.get('scheduler_url')


class SchedulerConfig(ConfigReaderBase):
    base = 'scheduler'

    @property
    def database(self):
        return self.get('database') or app_config.database

    @property
    def collection(self):
        return self.get('collection')

    @property
    def timezone(self):
        return timezone(self.get('timezone'))

    @property
    def log_file(self):
        log_file = self.get('log_file')
        if log_file:
            return log_file
        if platform.system() == 'Windows':
            return f'{os.environ["TEMP"]}\\nightowl\\scheduler.log'
        else:
            return '/var/log/nightowl/scheduler.log'

    @property
    def log_level(self):
        return self.get('log_level')


# http://docs.celeryproject.org/en/latest/userguide/configuration.html
class WorkerConfig(ConfigReaderBase):
    base = 'worker'

    @property
    def log_file(self):
        log_file = self.get('log_file')
        if log_file:
            return log_file
        if platform.system() == 'Windows':
            return f'{os.environ["TEMP"]}\\nightowl\\worker.log'
        else:
            return '/var/log/nightowl/worker.log'

    @property
    def log_level(self):
        return self.get('log_level')


class AMQPConfig(ConfigReaderBase):
    base = 'amqp'

    @property
    def host(self):
        return self.get('host')

    @property
    def username(self):
        return self.get('username')

    @property
    def password(self):
        return self.get('password')

    # amqp_URI       = "amqp://" amqp_authority [ "/" vhost ]
    # amqp_authority = [ amqp_userinfo "@" ] host [ ":" port ]
    # amqp_userinfo  = username [ ":" password ]
    # username       = *( unreserved / pct-encoded / sub-delims )
    # password       = *( unreserved / pct-encoded / sub-delims )
    # vhost          = segment
    @property
    def connection_str(self):
        if self.username and self.password:
            authen_str = f'{self.username}:{self.password}@'
        else:
            authen_str = ''
        return f'amqp://{authen_str}{self.host}/'


class RedisConfig(ConfigReaderBase):
    base = 'redis'

    @property
    def host(self):
        return self.get('host')

    @property
    def port(self):
        port = self.get('port')
        if port == 6379:
            port = None
        return port

    @property
    def password(self):
        return self.get('password')

    @property
    def ssl(self):
        return self.get('ssl')

    @property
    def max_connections(self):
        return self.get('max_connections')

    # redis://[:password]@host:port/db    # TCP连接
    # rediss://[:password]@host:port/db   # Redis TCP+SSL 连接
    @property
    def connection_str(self):
        protocol = 'rediss' if self.ssl else 'redis'
        port_str = f':{self.port}' if self.port else ''
        password_str = f':{self.password}@' if self.password else ''
        return f'{protocol}://{password_str}{self.host}{port_str}'


class MongoDBConfig(ConfigReaderBase):
    base = 'mongodb'

    @property
    def host(self):
        return self.get('host')

    @property
    def port(self):
        port = self.get('port')
        if port == 27017:
            port = None
        return port

    @property
    def username(self):
        return self.get('username')

    @property
    def password(self):
        return self.get('password')

    @property
    def auth_source(self):
        return self.get('auth_source')

    @property
    def auth_mechanism(self):
        return self.get('auth_mechanism')

    @property
    def tls(self):
        return self.get('tls')

    @property
    def tls_certificate_key_file(self):
        return self.get('tls_certificate_key_file')

    @property
    def tls_certificate_key_file_password(self):
        return self.get('tls_certificate_key_file_password')

    @property
    def tls_ca_file(self):
        return self.get('tls_ca_file')

    # mongodb://[username:password@]host1[:port1][,...hostN[:portN]][/[defaultauthdb][?options]]
    # https://docs.mongodb.com/manual/reference/connection-string/#connections-connection-options
    # https://api.mongodb.com/python/current/examples/tls.html
    @property
    def connection_str(self):
        port_str = f':{self.port}' if self.port else ''
        database_str = self.config.get('app', 'database')
        authen_str = f'{self.username}:{self.password}@' if self.username and self.password else ''

        options = []
        if self.auth_source:
            options.append(f'authSource={self.auth_source}')
        if self.auth_mechanism:
            options.append(f'authMechanism={self.auth_mechanism}')
        if self.tls:
            options.append('tls=true')
            if self.tls_certificate_key_file:
                options.append(f'tlsCertificateKeyFile={self.tls_certificate_key_file}')
            if self.tls_certificate_key_file_password:
                options.append(
                    f'tlsCertificateKeyFilePassword={self.tls_certificate_key_file_password}')
            if self.tls_ca_file:
                options.append(f'tlsCAFile={self.tls_ca_file}')
        options_str = f'?{"&".join(options)}' if options else ''
        return f'mongodb://{authen_str}{self.host}{port_str}/{database_str}{options_str}'


class SecurityConfig(ConfigReaderBase):
    base = 'security'

    @property
    def secret_key(self):
        return self.get('secret_key')

    @property
    def aes_iv(self):
        iv = self.get('aes_iv', default='')
        if len(iv) != 8:
            raise ValueError(f'Invalid IV: {iv}')
        return iv

    @property
    def aes_key(self):
        return hashlib.sha256(self.secret_key.encode()).hexdigest()[:32]

    @property
    def rsa_public_key(self):
        return self.get('rsa_public_key')

    @property
    def rsa_private_key(self):
        return self.get('rsa_private_key')

    @property
    def rsa_private_key_passphrase(self):
        return self.get('rsa_private_key_passphrase')


app_config = AppConfig()
scheduler_config = SchedulerConfig()
worker_config = WorkerConfig()
amqp_config = AMQPConfig()
redis_config = RedisConfig()
mongodb_config = MongoDBConfig()
security_config = SecurityConfig()
