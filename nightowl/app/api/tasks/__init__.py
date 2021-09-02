import uuid
from datetime import datetime

from apscheduler.jobstores.base import JobLookupError
from flask import current_app, jsonify, request
from flask.views import MethodView
from mongoengine.errors import DoesNotExist, ValidationError

from nightowl.auth import require_auth
from nightowl.models import admin as admin_model, task as task_model
from nightowl.utils.datetime import utc_now
from nightowl.utils.flask import Blueprint


bp = Blueprint('tasks', __name__)



@bp.route('/tasks')
class Tasks(MethodView):

    @require_auth()
    def get(self):
        # pylint: disable=no-member
        tasks = task_model.Task.objects().order_by('created_at')
        data_list = []
        for task in tasks:
            last_result = None
            if task.last_result:
                try:
                    last_result = task.last_result.fetch()
                except DoesNotExist:
                    pass
            result_data = {
                'ran_at': last_result.ran_at,
                'status': last_result.status.value,
            } if last_result else {}
            task_job = task.job
            data_list.append({
                '_id': task._id,
                'status': task.status.value,
                'next_run_time': task_job['next_run_time'] if task_job else None,
                'last_result': result_data,
            })
        current_app.logger.info('Fetched task list')
        return jsonify(data_list), 200

    @require_auth()
    def post(self):
        task = task_model.Task(_id=uuid.uuid4())
        request_data = request.get_json()
        yaml_content = request_data.get('yaml_content')
        task.from_yaml(yaml_content)
        task.created_at = utc_now()
        task.last_activated_at = utc_now()
        try:
            task.save()
        except ValidationError as ex:
            current_app.logger.info(f'Failed to add task (error={ex})')
            return jsonify({'error': str(ex)}), 400
        current_app.logger.info(f'Added task (_id={task._id})')
        return '', 201


@bp.route('/tasks/<_id>')
class Task(MethodView):

    @require_auth()
    def get(self, _id):
        try:
            # pylint: disable=no-member
            task = task_model.Task.objects.get(pk=uuid.UUID(_id))
        except DoesNotExist:
            current_app.logger.info(
                f'Failed to fetch task (_id={_id}, error=Not found)')
            return '', 404

        data = {
            '_id': task._id,
            'type': task.type.value,
            'run_date': task.run_date,
            'hour': task.hour,
            'minute': task.minute,
            'second': task.second,
            'day_of_week': task.day_of_week,
            'start_date': task.start_date,
            'end_date': task.end_date,
        }
        current_app.logger.info('Fetched tasks')
        return jsonify(data), 200

    @require_auth()
    def put(self, _id):
        try:
            # pylint: disable=no-member
            task = task_model.Task.objects.get(pk=uuid.UUID(_id))
        except DoesNotExist:
            current_app.logger.info(
                f'Failed to update task (_id={_id}, error=Not found)')
            return '', 404
        request_data = request.get_json()
        yaml_content = request_data.get('yaml_content')
        task.from_yaml(yaml_content)
        try:
            task.save()
        except ValidationError as ex:
            current_app.logger.info(f'Failed to update task (_id={_id}, error={ex})')
            return jsonify({'error': str(ex)}), 400
        current_app.logger.info(f'Updated task (_id={_id})')
        return '', 200

    @require_auth()
    def delete(self, _id):
        try:
            # pylint: disable=no-member
            task = task_model.Task.objects.get(pk=uuid.UUID(_id))
        except DoesNotExist:
            current_app.logger.info(
                f'Failed to delete task (_id={_id}, error=Not Found)')
            return '', 404
        task.delete()
        current_app.logger.info(f'Deleted task (_id={_id})')
        return '', 204


@bp.route('/tasks/<_id>/results')
class TaskResults(MethodView):

    @require_auth()
    def get(self, _id):
        # pylint: disable=no-member
        task_results = task_model.TaskResult.objects(
            task_id=uuid.UUID(_id)).only('_id', 'status', 'ran_at').order_by('-ran_at')
        data_list = []
        for task_result in task_results:
            data_list.append({
                '_id': task_result._id,
                'status': task_result.status.value,
                'ran_at': task_result.ran_at,
            })
        current_app.logger.info(f'Fetched task results (_id={_id}')
        return jsonify(data_list), 200


@bp.route('/tasks/<_id>/results/<result_id>')
class TaskResult(MethodView):

    @require_auth()
    def get(self, _id, result_id):
        try:
            # pylint: disable=no-member
            task_result = task_model.TaskResult.objects.get(pk=uuid.UUID(result_id))
        except DoesNotExist:
            current_app.logger.info(
                f'Failed to fetch task result (_id={_id}, '
                f'result_id={result_id}, error=Not found)')
            return '', 404
        data = {
            '_id': task_result._id,
            'task_id': task_result.task_id,
            'status': task_result.status.value,
            'ran_at': task_result.ran_at,
            'ended_at': task_result.ended_at,
            'logs': [{
                'time': log.time,
                'message': log.message,
                'level': log.level.value,
            } for log in task_result.logs],
        }
        current_app.logger.info(f'Fetched task result (_id={_id}, result_id={result_id}')
        return jsonify(data), 200


@bp.route('/tasks/<_id>/activate')
class ActivateTask(MethodView):

    @require_auth()
    def post(self, _id):
        try:
            task = task_model.Task.objects.get(pk=uuid.UUID(_id))  # pylint: disable=no-member
        except DoesNotExist:
            return '', 404
        permissions = request.user.permissions
        required_permissions = getattr(task, 'permissions', [])
        result, _ = admin_model.Permission.check(permissions, required_permissions)
        if not result:
            return {'error': 'No permissions'}, 403
        task.last_activated_by = request.user.name
        task.last_activated_at = datetime.now()
        task.active = True
        task.save()
        current_app.logger.info(f'Activated task (_id={_id})')
        return '', 200


@bp.route('/tasks/<_id>/deactivate')
class DeactivateTask(MethodView):

    @require_auth()
    def post(self, _id):
        try:
            task = task_model.Task.objects.get(pk=uuid.UUID(_id))  # pylint: disable=no-member
        except DoesNotExist:
            return '', 404
        permissions = request.user.permissions
        required_permissions = getattr(task, 'permissions', [])
        result, _ = admin_model.Permission.check(permissions, required_permissions)
        if not result:
            return {'error': 'No permissions'}, 403
        if not task.active:
            current_app.logger.info('Skipped deactivating task (error=Already deactivated)')
            return '', 204
        try:
            current_app.logger.info(f'Deactivated task (_id={_id})')
        except JobLookupError:
            current_app.logger.info('Skipped deactivating task (error=No such job)')
        task.active = False
        task.save()
        return '', 204
