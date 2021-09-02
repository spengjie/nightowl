from flask import current_app, jsonify
from flask.views import MethodView
from mongoengine.errors import DoesNotExist

from nightowl.auth import require_auth
from nightowl.models.modules import explorer as explorer_model
from nightowl.utils.flask import Blueprint


bp = Blueprint('explorers', __name__)


@bp.route('/explorers')
class Explorers(MethodView):

    @require_auth()
    def get(self):
        # pylint: disable=no-member
        explorers = explorer_model.Explorer.objects().order_by('_id')
        current_app.logger.info('Fetched explorers')
        return jsonify([explorer.to_mongo() for explorer in explorers]), 200


@bp.route('/explorers/_info')
class ExplorerInfos(MethodView):

    @require_auth()
    def get(self):
        # pylint: disable=no-member
        explorers = explorer_model.Explorer.objects.only('pk').order_by('_id')
        current_app.logger.info('Fetched explorer informations')
        return jsonify([explorer.to_mongo() for explorer in explorers]), 200


@bp.route('/explorers/<_id>')
class Explorer(MethodView):

    @require_auth()
    def get(self, _id):
        # pylint: disable=no-member
        try:
            explorer = explorer_model.Explorer.objects.get(pk=_id).to_mongo()
            current_app.logger.info(f'Fetched explorer (_id={_id})')
            return jsonify(explorer), 200
        except DoesNotExist:
            current_app.logger.info(f'Failed to fetch explorer (_id={_id}, error=Not found)')
            return '', 404
