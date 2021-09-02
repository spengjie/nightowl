import os

from flask import has_request_context, request
from mongoengine import connect

from nightowl.app import api, index
from nightowl.app.api import auth, network_objects, scheduler, tasks, user
from nightowl.app.api.admin import email, groups, permissions, sync, users
from nightowl.app.api.modules import credentials, discovery, explorers
from nightowl.config import app_config, mongodb_config
from nightowl.models.task import SchedulerClient
from nightowl.utils.flask import Flask
from nightowl.utils.logging import DatetimeFormatter, setup_logger


API_URL_PREFIX = '/api'


class AppLogFormatter(DatetimeFormatter):

    def format(self, record):
        if has_request_context():
            record.url = f'{request.method} {request.url}'
            record.ip = request.client_ip
            if hasattr(request, 'user'):
                record.user = f'{request.user.name}({request.user._id})'
            else:
                record.user = None
        else:
            record.url = None
            record.ip = None
            record.user = None
        record.pid = os.getpid()
        detail_def = {
            'URL': record.url,
            'IP': record.ip,
            'User': record.user,
        }
        details = []
        for key, value in detail_def.items():
            if value is None:
                continue
            details.append(f'{key}={value}')
        record.detail = f'[{", ".join(details)}]' if details else ''

        return super().format(record)


def create_app():
    connect(host=mongodb_config.connection_str)
    app = Flask(__name__, static_url_path='')
    setup_logger(app.logger, app_config.log_level, app_config.log_file,
                 '[%(asctime)s][%(levelname)s][%(pid)s]%(detail)s: '
                 '%(message)s', AppLogFormatter)

    app.register_blueprint(api.bp, url_prefix=API_URL_PREFIX)

    app.register_blueprint(auth.bp, url_prefix=API_URL_PREFIX)
    app.register_blueprint(user.bp, url_prefix=API_URL_PREFIX)

    app.register_blueprint(email.bp, url_prefix=API_URL_PREFIX)
    app.register_blueprint(groups.bp, url_prefix=API_URL_PREFIX)
    app.register_blueprint(permissions.bp, url_prefix=API_URL_PREFIX)
    app.register_blueprint(sync.bp, url_prefix=API_URL_PREFIX)
    app.register_blueprint(users.bp, url_prefix=API_URL_PREFIX)

    app.register_blueprint(credentials.bp, url_prefix=API_URL_PREFIX)
    app.register_blueprint(discovery.bp, url_prefix=API_URL_PREFIX)
    app.register_blueprint(explorers.bp, url_prefix=API_URL_PREFIX)

    app.register_blueprint(network_objects.bp, url_prefix=API_URL_PREFIX)

    app.register_blueprint(scheduler.bp, url_prefix=API_URL_PREFIX)
    app.register_blueprint(tasks.bp, url_prefix=API_URL_PREFIX)

    app.register_blueprint(index.bp)
    app.scheduler = SchedulerClient()
    app.logger.info('Started API server')  # pylint: disable=no-member
    return app
