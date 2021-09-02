from flask import current_app, jsonify, request
from flask.views import MethodView

from nightowl.auth import require_auth
from nightowl.utils.flask import Blueprint


bp = Blueprint('user', __name__)


@bp.route('/user')
class User(MethodView):

    @require_auth()
    def get(self):
        user = request.user
        data = {
            '_id': user._id,
            'username': user.username,
            'name': user.name,
            'email': user.email,
            'groups': user.all_groups,
            'permissions': user.permissions,
        }
        current_app.logger.info('Fetched user info')
        return jsonify(data), 200
