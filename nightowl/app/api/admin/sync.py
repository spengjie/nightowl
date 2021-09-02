from flask import current_app, jsonify, request
from flask.views import MethodView
from mongoengine.errors import DoesNotExist

from nightowl.auth import require_auth
from nightowl.models import admin as admin_model
from nightowl.models import task as task_model
from nightowl.utils.datetime import utc_now
from nightowl.utils.flask import Blueprint
from nightowl.utils.model import to_uuid
from nightowl.worker.tasks.run import run_task


bp = Blueprint('sync', __name__)


@bp.route('/sync/start')
class StartSync(MethodView):

    @require_auth(permissions=['admin.groups:write.add', 'admin.groups:write.edit',
                               'admin.users:write.add', 'admin.users:write.edit'])
    def post(self):
        sync_task = admin_model.SSOSyncTask.objects.first()  # pylint: disable=no-member
        if not sync_task:
            now = utc_now()
            sync_task = admin_model.SSOSyncTask(
                _id=to_uuid('sync'),
                active=True,
                created_at=now,
            )
            sync_task.day = '*'
            sync_task.save()
        run_task.delay(sync_task._id, request.user.name)
        current_app.logger.info('Started SSO sync')
        return '', 200


@bp.route('/sync/stop')
class StopSync(MethodView):

    @require_auth(permissions=['admin.groups:write.add', 'admin.groups:write.edit',
                               'admin.users:write.add', 'admin.users:write.edit'])
    def post(self):
        sync_task = admin_model.SSOSyncTask.objects.first()  # pylint: disable=no-member
        if not sync_task:
            current_app.logger.info('Failed to stop SSO sync (error=Not found)')
            return '', 404
        if sync_task.status != task_model.TaskStatus.RUNNING:
            current_app.logger.info('Failed to stop SSO sync (error=Already stopped)')
            return jsonify({'error': 'SSO sync has already been stopped'}), 200
        sync_task.status = task_model.TaskStatus.PENDING
        sync_task.save()
        current_app.logger.info('Stopped SSO sync')
        return '', 200


@bp.route('/sync/status')
class SyncStatus(MethodView):

    @require_auth(permissions=['admin.groups:write.add', 'admin.groups:write.edit',
                               'admin.users:write.add', 'admin.users:write.edit'])
    def get(self):
        sync_task = task_model.SSOSyncTask.objects.first()  # pylint: disable=no-member
        last_updated_at = ''
        if not sync_task:
            status = task_model.TaskStatus.PENDING
        else:
            status = sync_task.status
            last_result = sync_task.last_result
            if last_result:
                try:
                    task_result = last_result.fetch()
                    last_updated_at = task_result.ended_at
                except DoesNotExist:
                    pass
        current_app.logger.info('Got SSO sync status')
        return jsonify({
            'status': status.value,
            'last_updated_at': last_updated_at,
        }), 200
