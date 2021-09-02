from flask import current_app, jsonify
from flask.views import MethodView

from nightowl.auth import require_auth
from nightowl.models import admin as admin_model
from nightowl.utils.flask import Blueprint


bp = Blueprint('permissions', __name__)


@bp.route('/permissions')
class Permissions(MethodView):

    @require_auth()
    def get(self):
        permissions = admin_model.Permission.list()
        current_app.logger.info('Fetched permissions')
        return jsonify(permissions), 200
