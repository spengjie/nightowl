import re

from flask import current_app, jsonify, request
from flask.views import MethodView
from mongoengine.errors import DoesNotExist

from nightowl.auth import require_auth
from nightowl.models import admin as admin_model
from nightowl.worker.tasks import send_email
from nightowl.utils.datetime import utc_now
from nightowl.utils.flask import Blueprint
from nightowl.utils.security import encrypt, random, rsa_decrypt


bp = Blueprint('email', __name__)


def send_test_email(to_addr, email_settings):
    subject = 'NightOwl Network Development Platform Test Email'
    content = 'This is a test Email from NightOwl Network Development Platform.'
    try:
        send_email._send_email(to_addr, subject, content, format='plain',
                               email_settings=email_settings)
        return None
    except Exception as ex:
        return str(ex)


@bp.route('/email')
class EmailSettings(MethodView):

    @require_auth(permissions=['admin.settings.email:read'])
    def get(self):
        settings = admin_model.EmailSettings.get()
        data = {
            'host': settings.host,
            'port': settings.port,
            'auth_type': settings.auth_type,
            'email': settings.email,
            'password': '$encrypted' if 'password' in settings.password else None,
        }
        current_app.logger.info('Fetched Email settings')
        return jsonify(data), 200

    @require_auth(permissions=['admin.settings.email:write'])
    def put(self):
        request_data = request.get_json()
        settings = admin_model.EmailSettings.put(**request_data)
        data = {
            'host': settings.host,
            'port': settings.port,
            'auth_type': settings.auth_type.value,
            'email': settings.email,
            'password': '$encrypted' if settings.password else None,
        }
        current_app.logger.info('Updated Email settings')
        return jsonify(data), 200


@bp.route('/email/test')
class TestEmailSettings(MethodView):

    @require_auth(permissions=['admin.settings.email:write'])
    def post(self):
        request_data = request.get_json()
        try:
            to_addr = request_data.pop('to_addr')
        except KeyError:
            error = "'to_addr' must be set"
            current_app.logger.info(f'Failed to test Email (error={error})')
            return jsonify({'error': error}), 200
        if request_data:
            request_data['email'] = rsa_decrypt(request_data.get('email'))
            request_data['password'] = rsa_decrypt(request_data.get('password'))
        error = send_test_email(to_addr, request_data)
        if error:
            current_app.logger.info(f'Failed to test Email (error={error})')
            return jsonify({'error': error}), 200
        current_app.logger.info('Tested Email settings')
        return '', 200
