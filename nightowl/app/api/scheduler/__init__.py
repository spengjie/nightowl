from flask import current_app, jsonify
from flask.views import MethodView

from nightowl.auth import require_auth
from nightowl.utils.flask import Blueprint


bp = Blueprint('scheduler', __name__)


@bp.route('/scheduler/jobs')
class Projects(MethodView):

    @require_auth(permissions=['admin.scheduler:read'])
    def get(self):
        jobs = current_app.scheduler.get_jobs()
        current_app.logger.info('Fetched scheduler jobs')
        return jsonify(jobs), 200
