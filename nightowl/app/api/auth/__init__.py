import requests
from flask import current_app, jsonify, request
from flask.views import MethodView
from furl import furl
from mongoengine.errors import DoesNotExist

from nightowl.auth import authenticate, authorize, require_auth
from nightowl.config import app_config
from nightowl.models import admin as admin_model
from nightowl.utils.datetime import utc_now
from nightowl.utils.flask import Blueprint
from nightowl.utils.security import decrypt, encrypt, random, rsa_decrypt


bp = Blueprint('auth', __name__)


def get_data(settings):
    auth_type = settings.type
    data = {
        'type': auth_type.value,
    }
    if auth_type != 'local':
        sso_settings = settings.sso
        salt = sso_settings.salt
        data['sso'] = {
            'client_id': sso_settings.client_id,
            'client_secret': decrypt(sso_settings.client_secret, salt),
            'verify_certificate': sso_settings.verify_certificate,
            'auth_url': sso_settings.auth_url,
            'token_url': sso_settings.token_url,
            'user_api_url': sso_settings.user_api_url,
            'session_api_url': sso_settings.session_api_url,
            'logout_api_url': sso_settings.logout_api_url,
            'users_api_url': sso_settings.users_api_url,
            'groups_api_url': sso_settings.groups_api_url,
            'organization_api_url': sso_settings.organization_api_url,
            'username': sso_settings.username,
            'password': decrypt(sso_settings.password, salt),
        }
    return data


@bp.route('/auth')
class Auth(MethodView):

    @require_auth()
    def get(self):
        settings = admin_model.AuthSettings.get()
        data = get_data(settings)
        current_app.logger.info('Fetched authentication settings')
        return jsonify(data), 200

    @require_auth()
    def put(self):
        request_data = request.get_json()
        settings = admin_model.AuthSettings.put(**request_data)
        data = get_data(settings)
        current_app.logger.info('Updated authentication settings')
        return jsonify(data), 200


@bp.route('/auth/sso')
class AuthorizationSso(MethodView):

    def get(self):
        settings = admin_model.AuthSettings.get()

        result = {}
        auth_type = settings.type
        if auth_type in (admin_model.AuthType.LOCAL, admin_model.AuthType.BOTH):
            result['local'] = {}
        if auth_type in (admin_model.AuthType.SSO, admin_model.AuthType.BOTH):
            redirect_uri = request.args.get('redirect_uri')
            if not redirect_uri:
                error = "Invalid 'redirect_uri'"
                current_app.logger.error(f'Failed to get SSO info (error={error})')
                return jsonify({'error': error}), 400

            if redirect_uri.startswith('//'):
                schema = 'https' if app_config.ssl else 'http'
                redirect_uri = f'{schema}{redirect_uri}'
            elif redirect_uri.startswith('/'):
                redirect_uri = f'{app_config.base_url}{redirect_uri}'

            sso_settings = settings.sso
            if not sso_settings:
                current_app.logger.error(
                    'Failed to get SSO info (error=Invalid authentication settings)')
                return jsonify({'error': 'Server error'}), 500
            params = {
                'response_type': 'code',
                'client_id': sso_settings.client_id,
                'redirect_uri': redirect_uri,
                'state': random(20),
            }
            sso_url = furl(sso_settings.auth_url).set(params)
            params['url'] = sso_url.url
            result['sso'] = params
        current_app.logger.info('Got SSO info')
        return jsonify(result)


@bp.route('/auth/login')
class Login(MethodView):

    def post(self):
        request_data = request.get_json()
        username = rsa_decrypt(request_data.get('username'))
        password = rsa_decrypt(request_data.get('password'))
        auth_source = request_data.get('auth_source')
        result = authenticate(
            username, password, auth_source, request.client_ip)
        error_code = result['error_code']
        user_reason = result['user_message']
        admin_reason = result.get('admin_message', user_reason)
        if error_code == 20000:
            current_app.logger.info(f'Logged in (username={username})')
            return jsonify({
                'error_code': error_code,
                'message': user_reason,
                'token': result['token'],
            }), 200
        else:
            current_app.logger.warning(
                f'Failed to log in (username={username}, reason={admin_reason})')
            return jsonify({
                'error_code': error_code,
                'message': user_reason,
            }), 200


@bp.route('/auth/logout')
class Logout(MethodView):

    @require_auth()
    def post(self):
        session = request.session
        session.delete()
        current_app.logger.info('Logged out')
        access_token = session.sso_at
        if access_token:
            settings = admin_model.AuthSettings.get()
            sso_settings = settings.sso
            logout_api_url = sso_settings and settings.sso.logout_api_url
            if settings.type != admin_model.AuthType.LOCAL and logout_api_url:
                r = requests.post(logout_api_url,
                                  verify=sso_settings.verify_certificate,
                                  headers={'Authorization': 'Bearer ' + access_token})
                if r.ok:
                    response = r.json()
                    if response.get('error_code') == 20000:
                        current_app.logger.info('SSO logged out')
                    else:
                        current_app.logger.info(
                            f'SSO failed to log out (message={response.get("message")})')
                else:
                    current_app.logger.info(f'SSO failed to log out, {r.text}')
        return '', 200


@bp.route('/auth/authorization_code')
class AuthorizationCode(MethodView):

    def post(self):
        request_data = request.get_json()
        code = request_data.get('code')
        redirect_uri = request_data.get('redirect_uri')
        if not redirect_uri:
            error = "Invalid 'redirect_uri'"
            current_app.logger.error(f'Failed to log into SSO (reason={error})')
            return jsonify({'error': error}), 400

        if redirect_uri.startswith('//'):
            schema = 'https' if app_config.ssl else 'http'
            redirect_uri = f'{schema}{redirect_uri}'
        elif redirect_uri.startswith('/'):
            redirect_uri = f'{app_config.base_url}{redirect_uri}'

        result = authorize('authorization_code', request.client_ip,
                           code=code, redirect_uri=redirect_uri)
        error_code = result['error_code']
        user_reason = result['user_message']
        admin_reason = result.get('admin_message', user_reason)
        if error_code != 20000:
            if error_code == 40002:
                current_app.logger.warning(f'Failed to log into SSO (code={code}, '
                                           f'reason={admin_reason})')
                return jsonify({
                    'error_code': error_code,
                    'message': user_reason,
                }), 403
            else:
                current_app.logger.error(f'Failed to log into SSO (code={code}, '
                                         f'reason={admin_reason})')
                return jsonify({
                    'error_code': error_code,
                    'message': user_reason,
                }), 500
        current_app.logger.info(f'Logged into SSO (code={code})')
        return jsonify({
            'error_code': error_code,
            'message': user_reason,
            'token': result['token'],
        }), 200
