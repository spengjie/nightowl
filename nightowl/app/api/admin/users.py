import json
import uuid

from flask import current_app, jsonify, request
from flask.views import MethodView
from mongoengine.errors import DoesNotExist, ValidationError
from pymongo.errors import DuplicateKeyError

from nightowl.auth import require_auth
from nightowl.models import admin as admin_model
from nightowl.utils.datetime import utc_now
from nightowl.utils.flask import Blueprint
from nightowl.utils.model import get_query_pipeline, get_search_query, to_lower
from nightowl.utils.security import random, rsa_decrypt, sha256, weak_password


bp = Blueprint('users', __name__)


def get_data(user):
    data = {
        '_id': user._id,
        'type': user.type,
        'disabled': user.disabled,
        'username': user.username,
        'password': '$encrypted',
        'email': user.email,
        'name': user.name,
        'is_employee': user.is_employee,
        'employee_id': user.employee_id,
        'english_name': user.english_name,
        'title': user.title,
        'dept': user.dept,
        'manager': user.manager,
        'is_manager': user.is_manager,
        'city': user.city,
        'immutable_groups': user.immutable_groups,
        'groups': user.groups,
    }
    return data


def get_data_list(users):
    data_list = []
    for user in users:
        data_list.append(get_data(user))
    return data_list


def update_user(user, request_data):
    group_data_list = request_data.get('groups', [])
    groups = []
    for group_data in group_data_list:
        try:
            group_data['_id'] = uuid.UUID(group_data['_id'])
            groups.append(group_data)
        except ValueError:
            continue
    user.groups = sorted(groups, key=lambda x: x['name'])
    if user.type != 'Local':
        return
    user.username = to_lower(rsa_decrypt(request_data.get('username')))
    user.name = request_data.get('name')
    password = rsa_decrypt(request_data.get('password'))
    if password:
        is_weak = weak_password(password)
        if is_weak:
            return jsonify({'error': is_weak}), 400
        user.salt = random(16)
        user.password = sha256(password, user.salt)
    user.email = to_lower(request_data.get('email'))
    user.is_employee = request_data.get('is_employee', False)
    user.employee_id = request_data.get('employee_id')
    user.english_name = request_data.get('english_name')
    user.title = request_data.get('title')
    user.dept = request_data.get('dept')
    manager_data = request_data.get('manager')
    if manager_data:
        if isinstance(manager_data, dict):
            manager_id = manager_data.get('_id')
        else:
            manager_id = manager_data
    else:
        manager_id = None
    user.set_manager(manager_id)
    user.is_manager = request_data.get('is_manager', False)
    user.city = request_data.get('city')


@bp.route('/users')
class Users(MethodView):

    @require_auth(permissions=['admin.users:read'])
    def get(self):
        users = admin_model.User.objects().order_by('username')  # pylint: disable=no-member
        data_list = get_data_list(users)
        current_app.logger.info('Fetched users')
        return jsonify(data_list), 200

    @require_auth(permissions=['admin.users:write.add'])
    def post(self):
        request_data = request.get_json()
        user = admin_model.User(
            _id=uuid.uuid4(),
            type='Local',
            created_at=utc_now(),
        )
        update_user(user, request_data)
        try:
            user.save()
        except DuplicateKeyError:
            error = f'Username {user.username} already exists'
            current_app.logger.info(
                f'Failed to add user (_id={user._id}, error={error})')
            return jsonify({'error': error}), 400
        except ValidationError as ex:
            current_app.logger.info(f'Failed to add user (error={ex})')
            return jsonify({'error': str(ex)}), 400
        current_app.logger.info(f'Added user (_id={user._id}, name={user.name})')
        return '', 201


@bp.route('/users/_bulk')
class UsersBulk(MethodView):

    @require_auth(permissions=['admin.users:write.delete'])
    def delete(self):
        request_data = request.get_json()
        user_ids = []
        for user_id in request_data.get('users', []):
            try:
                user_ids.append(uuid.UUID(user_id))
            except ValueError:
                continue
        db_query = {'_id': {'$in': user_ids}}
        for user in admin_model.User.objects(__raw__=db_query):  # pylint: disable=no-member
            user.set_manager(None)  # Remove itself from its manager's direct reports
        admin_model.User.objects(__raw__=db_query).delete()  # pylint: disable=no-member
        current_app.logger.info(f'Bulk deleted users (users={[str(_id) for _id in user_ids]})')
        return '', 204


@bp.route('/users/_query')
class QueryUsers(MethodView):

    @require_auth(permissions=['admin.users:read'])
    def get(self):
        key = request.args.get('key')
        extra_query_arg = request.args.get('extra_query')
        try:
            if extra_query_arg:
                extra_query = json.loads(extra_query_arg)
            else:
                extra_query = {}
        except json.decoder.JSONDecodeError:
            extra_query = {}
        if not key:
            users = admin_model.User.objects(  # pylint: disable=no-member
                __raw__=extra_query).order_by('username')
            data_list = []
            for user in users:
                data_list.append({
                    '_id': user._id,
                    'username': user.username,
                    'name': user.name,
                })
            current_app.logger.info(f'Queried users (query={extra_query})')
            return jsonify(data_list), 200
        q = request.args.get('q')
        pipeline = []
        if key in ('groups._id', 'groups.name'):
            pipeline.extend([
                {'$addFields': {'groups': {'$ifNull': ['$groups', []]}}},
                {'$addFields': {'immutable_groups': {'$ifNull': ['$immutable_groups', []]}}},
                {'$addFields': {'groups': {'$setUnion': ['$groups', '$immutable_groups']}}},
            ])
            unwind_key = 'groups'
        else:
            unwind_key = key
        pipeline.extend(
            get_query_pipeline(key, q, unwind_key=unwind_key,
                               extra_query=extra_query))
        data_list = [
            result['_id'] for result in
            admin_model.User.objects.aggregate(pipeline)]  # pylint: disable=no-member
        current_app.logger.info(f'Queried users (key={key}, q={q}), extra={extra_query_arg}')
        return jsonify(data_list), 200


@bp.route('/users/_search')
class SearchUsers(MethodView):

    @require_auth(permissions=['admin.users:read'])
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
                f'Failed to fetch users (start={start}, limit={limit}, '
                f'filters={filters}, keyword_filter_keys={keyword_filter_keys}, error={error})')
            return jsonify({'error': str(error)}), 400
        if limit > 500:
            error = "'limit' must be less than or equal to 500"
            current_app.logger.info(
                f'Failed to fetch users (start={start}, limit={limit}, '
                f'filters={filters}, keyword_filter_keys={keyword_filter_keys}, error={error})')
            return jsonify({'error': str(error)}), 400

        try:
            db_query = get_search_query(filters, keyword_filter_keys=keyword_filter_keys)
        except ValueError as ex:
            current_app.logger.info(
                f'Failed to fetch users (start={start}, limit={limit}, '
                f'filters={filters}, keyword_filter_keys={keyword_filter_keys}, error={ex})')
            return jsonify({'error': str(ex)}), 400

        query_list = db_query.get('$and', [])
        new_query_list = []
        for query in query_list:
            key, value = list(query.items())[0]
            if key == 'groups._id':
                new_query_list.append({'$or': [{'groups._id': value},
                                      {'immutable_groups._id': value}]})
                continue
            if key == 'groups.name':
                new_query_list.append({'$or': [{'groups.name': value},
                                      {'immutable_groups.name': value}]})
                continue
            if key == '$or':
                or_key = list(value[0].keys())[0]
                if or_key == 'groups._id':
                    or_list = []
                    for or_value in map(lambda x: list(x.values())[0], value):
                        or_list.append({'groups._id': or_value})
                        or_list.append({'immutable_groups._id': or_value})
                    new_query_list.append({'$or': or_list})
                    continue
                if or_key == 'groups.name':
                    or_list = []
                    for or_value in map(lambda x: list(x.values())[0], value):
                        or_list.append({'groups.name': or_value})
                        or_list.append({'immutable_groups.name': or_value})
                    new_query_list.append({'$or': or_list})
                    continue
            new_query_list.append({key: value})
        db_query = {'$and': new_query_list} if new_query_list else {}

        query_qs = admin_model.User.objects(__raw__=db_query)  # pylint: disable=no-member
        paging_qs = query_qs.skip(start).limit(limit).order_by('username')
        data_list = get_data_list(paging_qs)
        current_app.logger.info(
            f'Fetched users (start={start}, limit={limit}, '
            f'filters={filters}, keyword_filter_keys={keyword_filter_keys})')
        return jsonify({
            'users': data_list, 'total': query_qs.count()
        }), 200


@bp.route('/users/<_id>')
class User(MethodView):

    @require_auth(permissions=['admin.users:read'])
    def get(self, _id):
        try:
            user = admin_model.User.objects.get(pk=uuid.UUID(_id))  # pylint: disable=no-member
        except DoesNotExist:
            current_app.logger.info(f'Failed to fetch user (_id={_id}, error=Not found)')
            return '', 404
        current_app.logger.info(f'Fetched user (_id={user._id}, name={user.name})')
        return jsonify(get_data(user)), 200

    @require_auth(permissions=['admin.users:write.edit'])
    def put(self, _id):
        try:
            user = admin_model.User.objects.get(pk=uuid.UUID(_id))  # pylint: disable=no-member
        except DoesNotExist:
            current_app.logger.info(f'Failed to update user (_id={_id}, error=Not found)')
            return '', 404
        request_data = request.get_json()
        update_user(user, request_data)
        user.updated_at = utc_now()
        try:
            user.save()
        except DuplicateKeyError:
            error = f'Username {user.username} already exists'
            current_app.logger.info(
                f'Failed to update user (_id={user._id}, error={error})')
            return jsonify({'error': error}), 400
        except ValidationError as ex:
            current_app.logger.info(f'Failed to update user (_id={_id}, error={ex})')
            return jsonify({'error': str(ex)}), 400
        current_app.logger.info(f'Updated user (_id={user._id}, name={user.name})')
        return '', 200

    @require_auth(permissions=['admin.users:write.delete'])
    def delete(self, _id):
        try:
            user = admin_model.User.objects.get(pk=uuid.UUID(_id))  # pylint: disable=no-member
            user.set_manager(None)  # Remove itself from its manager's direct reports
        except DoesNotExist:
            current_app.logger.info(f'Failed to delete user (_id={_id}, error=Not found)')
            return '', 404
        user.delete()
        current_app.logger.info(f'Deleted user (_id={user._id}, name={user.name})')
        return '', 204


@bp.route('/employees')
class Employees(MethodView):

    @require_auth(permissions=['projects:write.edit'])
    def get(self):
        employees = admin_model.User.objects(  # pylint: disable=no-member
            disabled=False, is_employee=True).order_by('username')
        data_list = []
        for employee in employees:
            data_list.append({
                '_id': employee._id,
                'employee_id': employee.employee_id,
                'email': employee.email,
                'name': employee.name,
                'english_name': employee.english_name,
                'title': employee.title,
                'dept': employee.dept,
                'manager': employee.manager or None,
                'city': employee.city,
            })
        current_app.logger.info('Fetched employees')
        return jsonify(data_list), 200


@bp.route('/employees/_search')
class SearchEmployees(MethodView):

    @require_auth()
    def post(self):
        request_data = request.get_json()
        filters = request_data.get('filters', [])
        filters.append({'key': 'disabled', 'value': False, 'type': 'bool'})
        filters.append({'key': 'is_employee', 'value': True, 'type': 'bool'})
        keyword_filter_keys = ['employee_id', 'name', 'english_name', 'email', 'dept']

        try:
            db_query = get_search_query(filters, keyword_filter_keys=keyword_filter_keys)
        except ValueError as ex:
            current_app.logger.info(
                f'Failed to fetch employees (filters={filters}, error={ex})')
            return jsonify({'error': str(ex)}), 400

        query_qs = admin_model.User.objects(__raw__=db_query)  # pylint: disable=no-member
        paging_qs = query_qs.order_by('employee_id')
        data_list = []
        for user in paging_qs:
            data_list.append({
                '_id': user._id,
                'employee_id': user.employee_id,
                'name': user.name,
                'english_name': user.english_name,
                'email': user.email,
                'dept': user.dept,
            })
        current_app.logger.info(
            f'Fetched employees (filters={filters})')
        return jsonify(data_list), 200
