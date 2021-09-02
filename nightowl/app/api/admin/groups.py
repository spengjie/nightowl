import uuid

from flask import current_app, jsonify, request
from flask.views import MethodView
from mongoengine.errors import DoesNotExist, ValidationError

from nightowl.auth import require_auth
from nightowl.models import admin as admin_model
from nightowl.utils.datetime import utc_now
from nightowl.utils.flask import Blueprint
from nightowl.utils.model import get_query_pipeline, get_search_query


bp = Blueprint('groups', __name__)


def get_data(group):
    return {
        '_id': group._id,
        'type': group.type,
        'name': group.name,
        'permissions': group.permissions or [],
    }


def get_data_list(groups):
    data_list = []
    for group in groups:
        data_list.append(get_data(group))
    return data_list


@bp.route('/groups')
class Groups(MethodView):

    @require_auth(permissions=['admin.groups:read'])
    def get(self):
        groups = admin_model.Group.objects().order_by('name')  # pylint: disable=no-member
        data_list = get_data_list(groups)
        current_app.logger.info('Fetched groups')
        return jsonify(data_list), 200

    @require_auth(permissions=['admin.groups:write.add'])
    def post(self):
        request_data = request.get_json()
        group = admin_model.Group(
            _id=uuid.uuid4(),
            type='Local',
            name=request_data['name'],
            permissions=admin_model.Permission.merge(request_data.get('permissions', [])),
            created_at=utc_now(),
        )
        try:
            group.save()
        except ValidationError as ex:
            current_app.logger.info(f'Failed to add group (error={ex})')
            return jsonify({'error': str(ex)}), 400
        current_app.logger.info(f'Added group (_id={group._id})')
        return '', 201


@bp.route('/groups/_bulk')
class GroupsBulk(MethodView):

    @require_auth(permissions=['admin.groups:write.delete'])
    def delete(self):
        request_data = request.get_json()
        group_ids = []
        for group_id in request_data.get('groups', []):
            try:
                group_ids.append(uuid.UUID(group_id))
            except ValueError:
                continue
        db_query = {'_id': {'$in': group_ids}}
        admin_model.Group.objects(__raw__=db_query).delete()  # pylint: disable=no-member
        current_app.logger.info(f'Bulk deleted groups (groups={[str(_id) for _id in group_ids]})')
        return '', 204


@bp.route('/groups/_info')
class GroupInfos(MethodView):

    @require_auth()
    def get(self):
        groups = admin_model.Group.objects().order_by('name')  # pylint: disable=no-member
        data_list = []
        for group in groups:
            data_list.append({
                '_id': group._id,
                'name': group.name,
            })
        current_app.logger.info('Fetched group informations')
        return jsonify(data_list), 200


@bp.route('/groups/_query')
class QueryGroups(MethodView):

    @require_auth(permissions=['admin.groups:read'])
    def get(self):
        key = request.args.get('key')
        q = request.args.get('q')
        pipeline = get_query_pipeline(key, q)
        data_list = [
            result['_id'] for result in
            admin_model.Group.objects.aggregate(pipeline)]  # pylint: disable=no-member
        current_app.logger.info(f'Queried groups (key={key}, q={q})')
        return jsonify(data_list), 200


@bp.route('/groups/_search')
class SearchGroups(MethodView):

    @require_auth(permissions=['admin.groups:read'])
    def post(self):
        request_data = request.get_json()
        start = request_data.get('start', 0)
        if start < 0:
            start = 0
        limit = request_data.get('limit', 0)
        filters = request_data.get('filters', [])
        keyword_filter_keys = request_data.get('keyword_filter_keys', [])

        if start > 1000000:
            error = "'start' must be less than or equal to 1000000"
            current_app.logger.info(
                f'Failed to fetch groups (start={start}, limit={limit}, '
                f'filters={filters}, keyword_filter_keys={keyword_filter_keys}, error={error})')
            return jsonify({'error': str(error)}), 400
        if limit > 500:
            error = "'limit' must be less than or equal to 500"
            current_app.logger.info(
                f'Failed to fetch groups (start={start}, limit={limit}, '
                f'filters={filters}, keyword_filter_keys={keyword_filter_keys}, error={error})')
            return jsonify({'error': str(error)}), 400

        try:
            db_query = get_search_query(filters, keyword_filter_keys=keyword_filter_keys)
        except ValueError as ex:
            current_app.logger.info(
                f'Failed to fetch groups (start={start}, limit={limit}, '
                f'filters={filters}, keyword_filter_keys={keyword_filter_keys}, error={ex})')
            return jsonify({'error': str(ex)}), 400
        query_qs = admin_model.Group.objects(__raw__=db_query)  # pylint: disable=no-member
        paging_qs = query_qs.skip(start).limit(limit).order_by('name')
        data_list = get_data_list(paging_qs)
        current_app.logger.info(
            f'Fetched groups (start={start}, limit={limit}, '
            f'filters={filters}, keyword_filter_keys={keyword_filter_keys})')
        return jsonify({
            'groups': data_list, 'total': query_qs.count()
        }), 200


@bp.route('/groups/<_id>')
class Group(MethodView):

    @require_auth(permissions=['admin.groups:read'])
    def get(self, _id):
        try:
            group = admin_model.Group.objects.get(pk=uuid.UUID(_id))  # pylint: disable=no-member
        except DoesNotExist:
            current_app.logger.info(f'Failed to fetch group (_id={_id}, error=Not found)')
            return '', 404
        current_app.logger.info(f'Fetched group (_id={_id})')
        return jsonify(get_data(group)), 200

    @require_auth(permissions=['admin.groups:write.edit'])
    def put(self, _id):
        try:
            group = admin_model.Group.objects.get(pk=uuid.UUID(_id))  # pylint: disable=no-member
        except DoesNotExist:
            current_app.logger.info(f'Failed to update group (_id={_id}, error=Not found)')
            return '', 404
        request_data = request.get_json()
        group_name = request_data.get('name')
        if group.type == 'Local' and group_name:
            group.name = group_name
        group.permissions = admin_model.Permission.merge(request_data.get('permissions', []))
        group.updated_at = utc_now()
        try:
            group.save()
        except ValidationError as ex:
            current_app.logger.info(f'Failed to update group (_id={_id}, error={ex})')
            return jsonify({'error': str(ex)}), 400
        current_app.logger.info(f'Updated group (_id={_id})')
        return '', 200

    @require_auth(permissions=['admin.groups:write.delete'])
    def delete(self, _id):
        try:
            # pylint: disable=no-member
            group = admin_model.Group.objects.get(pk=uuid.UUID(_id))
        except DoesNotExist:
            current_app.logger.info(f'Failed to delete group (_id={_id}, error=Not Found)')
            return '', 404
        group.delete()
        current_app.logger.info(f'Deleted group (_id={_id})')
        return '', 204
