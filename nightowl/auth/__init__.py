import uuid
from datetime import timedelta
from functools import wraps
from json.decoder import JSONDecodeError

import requests
from flask import current_app, jsonify, request
from mongoengine.errors import DoesNotExist
from mongoengine.queryset.visitor import Q

from nightowl.models import admin as admin_model
from nightowl.utils.datetime import utc_now
from nightowl.utils.security import decrypt, sha256


# Token status codes:
#     Success status
#         20000: OK
#         20001: New token issued
#         20004: Unimportant failure
#     Permissions status
#         30001: No permissions
#     Login failed status
#         40001: Invalid credentials
#         40002: Unauthorized
#         40003: Too many failures
#         40100: Already logged in
#         41001: Invalid token
#         41002: Forced logout
#         42001: Weak password
#         59999: Server error


def authenticate(username, password, auth_source, client_ip):
    if auth_source != 'Local':
        return {
            'error_code': 40001,
            'user_message': 'Invalid credentials',
            'admin_message': "Invalid login source. It can only be 'Local'",
        }
    if not username or not password:
        return {
            'error_code': 40001,
            'user_message': 'Invalid credentials',
            'admin_message': 'Credentials cannot be empty',
        }

    try:
        user = admin_model.User.objects.get(  # pylint: disable=no-member
            Q(type='Local') & (Q(username=username) | Q(email=username))
        )
    except DoesNotExist:
        return {
            'error_code': 40001,
            'user_message': 'Invalid credentials',
            'admin_message': f"User '{username}' not found",
        }

    if not user.permissions:
        return {
            'error_code': 40002,
            'user_message': 'You are not authorized to log into this system',
            'admin_message': 'Unauthorized',
        }

    if user.password != sha256(password, user.salt):
        return {
            'error_code': 40001,
            'user_message': 'Invalid credentials',
        }
    session_id = uuid.uuid4()
    now = utc_now()
    session = admin_model.UserSession(
        _id=session_id,
        user=user,
        client_ip=client_ip,
        login_at=now,
        expires=now + timedelta(minutes=120),
        last_accessed=now,
    )
    session.save()
    return {
        'error_code': 20000,
        'user_message': 'Logged in',
        'token': session_id,
    }


def authorize(grant_type, client_ip=None, code=None, redirect_uri=None):
    try:
        settings = admin_model.AuthSettings.get()
        auth_settings = settings.value
        sso_settings = auth_settings.get('sso', {})
    except DoesNotExist:
        auth_settings = {'type': 'local'}
        sso_settings = {}

    if auth_settings.get('type') not in ('sso', 'both'):
        return {
            'error_code': 59999,
            'user_message': 'Server error',
            'admin_message': 'No SSO configured',
        }

    salt = sso_settings['salt']
    client_secret = decrypt(sso_settings['client_secret'], salt)
    if grant_type == 'authorization_code':
        if not code:
            return {
                'error_code': 59999,
                'user_message': 'Server error',
                'admin_message': 'Missing code',
            }
        if not redirect_uri:
            return {
                'error_code': 59999,
                'user_message': 'Server error',
                'admin_message': 'Missing redirect_uri',
            }
        payload = {
            'grant_type': 'authorization_code',
            'code': code,
            'client_id': sso_settings['client_id'],
            'client_secret': client_secret,
            'redirect_uri': redirect_uri,
        }
    elif grant_type == 'password':
        if not sso_settings['username'] or not sso_settings['password']:
            return {
                'error_code': 59999,
                'user_message': 'Server error',
                'admin_message': "Missing 'username' or 'password'",
            }
        password = decrypt(sso_settings['password'], salt)
        payload = {
            'grant_type': 'password',
            'username': sso_settings['username'],
            'password': password,
            'client_id': sso_settings['client_id'],
            'client_secret': client_secret,
        }
    r = requests.post(
        sso_settings['token_url'], verify=sso_settings.get('verify_certificate'),
        json=payload, headers={'Accept': 'application/json'})
    if r.ok:
        response = r.json()
    else:
        return {
            'error_code': 59999,
            'user_message': 'Server error',
            'admin_message': f'SSO server error (sso_response={r.text})',
        }
    access_token = response.get('access_token')
    if not access_token:
        return {
            'error_code': 59999,
            'user_message': 'Server error',
            'admin_message': f'SSO server error (sso_response={r.text})',
        }
    if grant_type == 'password':
        return {
            'error_code': 20000,
            'user_message': 'Logged in',
            'token': access_token,
        }

    r = requests.get(
        sso_settings['user_api_url'], verify=sso_settings.get('verify_certificate'),
        headers={'Authorization': 'Bearer ' + access_token})
    if r.ok:
        response = r.json()
    else:
        return {
            'error_code': 59999,
            'user_message': 'Server error',
            'admin_message': f'SSO server error (sso_response={r.text})',
        }
    user_id = response.get('_id')
    if not user_id:
        return {
            'error_code': 59999,
            'user_message': 'Server error',
            'admin_message': f'SSO server error (sso_response={r.text})',
        }
    try:
        user = admin_model.User.objects.get(pk=uuid.UUID(user_id))  # pylint: disable=no-member
    except DoesNotExist:
        for group in response['groups']:
            group['_id'] = uuid.UUID(group['_id'])
        user = admin_model.User(
            _id=user_id,
            username=response['username'],
            disabled=False,
            type='SSO',
            name=response['name'],
            email=response['email'],
            immutable_groups=response['groups'],
            created_at=utc_now(),
        )
        user.save()

    if not user.permissions:
        return {
            'error_code': 40002,
            'user_message': 'You are not authorized to log into this system',
            'admin_message': 'Unauthorized',
        }

    session_id = uuid.uuid4()
    now = utc_now()
    session = admin_model.UserSession(
        _id=session_id,
        user=user,
        client_ip=client_ip,
        login_at=now,
        expires=now + timedelta(minutes=120),
        last_accessed=now,
        sso_at=access_token,
    )
    session.save()

    return {
        'error_code': 20000,
        'user_message': 'Logged in',
        'token': session_id,
    }


def verify_token(token):
    if not token:
        return None
    try:
        # pylint: disable=no-member
        session = admin_model.UserSession.objects.get(pk=uuid.UUID(token))
    except DoesNotExist:
        return None
    if session.expired():
        session.delete()
        return None
    return session


def verify_authorization(authorization):
    if not authorization:
        return None
    segs = authorization.split()
    if len(segs) != 2:
        return None
    token_type, token = segs
    if token_type.lower() != 'bearer':
        return None
    return verify_token(token)


def verify_permissions(user, permissions):
    lacked_permissions = user.lack(permissions)
    if lacked_permissions:
        return {
            'error_code': 30001,
            'user_message': 'No permissions',
            'admin_message': f'No permissions (required={permissions}, '
                             f'missed={lacked_permissions})',
        }
    else:
        return {
            'error_code': 20000,
            'user_message': 'Verified permissions',
        }


def require_auth(permissions=None):
    def wrapper_outter(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            authorization = request.headers.get('Authorization')
            session = verify_authorization(authorization)
            if not session:
                current_app.logger.info('Failed to verify token (reason=Invalid token)')
                return jsonify({'token_response': {
                    'error_code': 41001,
                    'message': 'Invalid token',
                }}), 401
            try:
                user = session.user
                if not user:
                    current_app.logger.warning('Failed to verify token (reason=User not found)')
                    return jsonify({'token_response': {
                        'error_code': 41001,
                        'message': 'Invalid token',
                    }}), 401
            except DoesNotExist:
                current_app.logger.warning('Failed to verify token (reason=User not found)')
                return jsonify({'token_response': {
                    'error_code': 41001,
                    'message': 'Invalid token',
                }}), 401

            request.session = session  # pylint: disable=assigning-non-slot
            request.user = session.user  # pylint: disable=assigning-non-slot

            if permissions:
                result = verify_permissions(session.user, permissions)
                error_code = result['error_code']
                user_reason = result['user_message']
                admin_reason = result.get('admin_message', user_reason)
                if error_code != 20000:
                    current_app.logger.info(f'Failed to verify permissions (reason={admin_reason})')
                    return jsonify({'token_response': {
                        'error_code': error_code,
                        'message': user_reason,
                    }}), 403
                else:
                    current_app.logger.debug(admin_reason)

            # Verify SSO session
            access_token = session.sso_at
            if access_token:
                settings = admin_model.AuthSettings.get()
                sso_settings = settings.sso
                r = requests.get(sso_settings.session_api_url,
                                 verify=sso_settings.verify_certificate,
                                 headers={'Authorization': 'Bearer ' + access_token})
                try:
                    response = r.json()
                    error_code = response.get('error_code')
                except JSONDecodeError:
                    error_code = 59999
                if error_code != 20000:
                    message = 'SSO session expired'
                    current_app.logger.info(message)
                    result = {
                        'error_code': 41001,
                        'message': message,
                    }
                    session.delete()
                    return jsonify({'token_response': result}), 401
                elif error_code == 59999:
                    current_app.logger.error(f'SSO server error (sso_response={r.text})')
                    result = {
                        'error_code': 59999,
                        'message': 'Server error',
                    }
                    return jsonify({'token_response': result}), 500

            session.refresh()
            ret = func(*args, **kwargs)
            return ret
        return wrapper
    return wrapper_outter
