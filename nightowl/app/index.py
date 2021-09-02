import traceback

from flask import current_app, Blueprint, jsonify, request


bp = Blueprint('index', __name__)


@bp.route('/')
def index():
    return '<pre>This is an API server for NightOwl Network Development Platform.</pre>'


@bp.app_errorhandler(404)
def page_not_found(error):
    return jsonify({'error': 'API not found'}), 404


@bp.app_errorhandler(500)
def server_error(error):
    current_app.logger.error(f'Server error (error={traceback.format_exc()})')
    return jsonify({'error': 'Server error'}), 500


@bp.before_app_request
def before_request_func():
    request.client_ip = request.headers.get('X-Real-Ip', request.remote_addr)
