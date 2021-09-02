import uuid

from flask import current_app, jsonify, request
from flask.views import MethodView
from mongoengine.errors import DoesNotExist, NotUniqueError, ValidationError
from pymongo.errors import DuplicateKeyError

from nightowl.auth import require_auth
from nightowl.models.modules import credentials as credentials_model
from nightowl.utils.datetime import utc_now
from nightowl.utils.flask import Blueprint
from nightowl.utils.security import encrypt


bp = Blueprint('credentials', __name__)


@bp.route('/credentials/cli')
class CLICredentialss(MethodView):

    @require_auth()
    def get(self):
        # pylint: disable=no-member
        cli_credentials = credentials_model.CLICredentials.objects().order_by('alias')
        data_list = []
        for cli_credential in cli_credentials:
            data_list.append({
                '_id': cli_credential._id,
                'alias': cli_credential.alias,
                'username': cli_credential.username,
            })
        current_app.logger.info('Fetched CLI credentials list')
        return jsonify(data_list), 200

    @require_auth()
    def post(self):
        request_data = request.get_json()
        # encrypted_data = request_data.get('data')
        # if encrypted_data:
        #     decrypted_data = rsa_decrypt(request_data.get('data'))
        #     request_data = json.loads(decrypted_data)
        # else:
        #     request_data = {}
        cli_credential = credentials_model.CLICredentials(_id=uuid.uuid4())
        cli_credential.alias = request_data.get('alias')
        cli_credential.username = request_data.get('username')
        password = request_data.get('password')
        if password:
            cli_credential.password = encrypt(password)
        private_key = request_data.get('private_key')
        if private_key:
            cli_credential.private_key = private_key
        cli_credential.created_at = utc_now()
        try:
            cli_credential.save()
        except (DuplicateKeyError, NotUniqueError):
            error = 'CLI credential with same alias already exists'
            current_app.logger.info(f'Failed to add CLI credential (error={error})')
            return jsonify({'error': error}), 400
        except ValidationError as ex:
            current_app.logger.info(f'Failed to add CLI credential (error={ex})')
            return jsonify({'error': str(ex)}), 400
        current_app.logger.info(f'Added CLI credentials (_id={cli_credential._id})')
        return '', 201


@bp.route('/credentials/cli/<_id>')
class CLICredentials(MethodView):

    @require_auth()
    def get(self, _id):
        try:
            # pylint: disable=no-member
            cli_credential = credentials_model.CLICredentials.objects.get(pk=uuid.UUID(_id))
        except DoesNotExist:
            current_app.logger.info(
                f'Failed to fetch CLI credential (_id={_id}, error=Not found)')
            return '', 404
        data = {
            '_id': cli_credential._id,
            'alias': cli_credential.alias,
            'username': cli_credential.username,
            'password': '$encrypted' if cli_credential.password else None,
            'private_key': '$encrypted' if cli_credential.private_key else None,
        }
        current_app.logger.info(f'Fetched CLI credential (_id={_id})')
        return jsonify(data), 200

    @require_auth()
    def put(self, _id):
        try:
            # pylint: disable=no-member
            cli_credential = credentials_model.CLICredentials.objects.get(pk=uuid.UUID(_id))
        except DoesNotExist:
            current_app.logger.info(
                f'Failed to update CLI credential (_id={_id}, error=Not found)')
            return '', 404
        request_data = request.get_json()
        # encrypted_data = request_data.get('data')
        # if encrypted_data:
        #     decrypted_data = rsa_decrypt(request_data.get('data'))
        #     request_data = json.loads(decrypted_data)
        # else:
        #     request_data = {}
        cli_credential.alias = request_data.get('alias')
        cli_credential.username = request_data.get('username')
        password = request_data.get('password')
        private_key = request_data.get('private_key')
        if password and not private_key:
            cli_credential.password = encrypt(password)
            cli_credential.private_key = None
        if private_key and not password:
            cli_credential.password = None
            cli_credential.private_key = private_key
        cli_credential.updated_at = utc_now()
        try:
            cli_credential.save()
        except (DuplicateKeyError, NotUniqueError):
            error = 'CLI credential with same alias already exists'
            current_app.logger.info(
                f'Failed to update CLI credential (_id={_id}, error={error})')
            return jsonify({'error': error}), 400
        except ValidationError as ex:
            current_app.logger.info(f'Failed to update CLI credential (_id={_id}, error={ex})')
            return jsonify({'error': str(ex)}), 400
        current_app.logger.info(f'Updated CLI credential (_id={_id})')
        return '', 200

    @require_auth()
    def delete(self, _id):
        try:
            # pylint: disable=no-member
            cli_credential = credentials_model.CLICredentials.objects.get(pk=uuid.UUID(_id))
        except DoesNotExist:
            current_app.logger.info(
                f'Failed to delete CLI credential (_id={_id}, error=Not Found)')
            return '', 404
        cli_credential.delete()
        current_app.logger.info(f'Deleted CLI credential (_id={_id})')
        return '', 204


@bp.route('/credentials/aws_access_keys')
class AWSAccessKeys(MethodView):

    @require_auth()
    def get(self):
        access_keys = credentials_model.AWSAccessSKey.objects(  # pylint: disable=no-member
            ).order_by('alias')
        data_list = []
        for access_key in access_keys:
            data_list.append({
                '_id': access_key._id,
                'alias': access_key.alias,
                'region_name': access_key.region_name,
                'access_key': access_key.access_key,
            })
        current_app.logger.info('Fetched AWS access keys')
        return jsonify(data_list), 200

    @require_auth()
    def post(self):
        request_data = request.get_json()
        # encrypted_data = request_data.get('data')
        # if encrypted_data:
        #     decrypted_data = rsa_decrypt(request_data.get('data'))
        #     request_data = json.loads(decrypted_data)
        # else:
        #     request_data = {}
        access_key = credentials_model.AWSAccessSKey(_id=uuid.uuid4())
        access_key.alias = request_data.get('alias')
        access_key.region_name = request_data.get('region_name')
        access_key.access_key = request_data.get('access_key')
        secret_key = request_data.get('secret_key')
        if secret_key:
            access_key.secret_key = secret_key
        access_key.created_at = utc_now()
        try:
            access_key.save()
        except (DuplicateKeyError, NotUniqueError):
            error = 'AWS access key with same alias already exists'
            current_app.logger.info(f'Failed to add AWS access key (error={error})')
            return jsonify({'error': error}), 400
        except ValidationError as ex:
            current_app.logger.info(f'Failed to add AWS access key (error={ex})')
            return jsonify({'error': str(ex)}), 400
        current_app.logger.info(f'Added AWS access key (_id={access_key._id})')
        return '', 200


@bp.route('/credentials/aws_access_keys/<_id>')
class AWSAccessKey(MethodView):

    @require_auth()
    def get(self, _id):
        try:
            # pylint: disable=no-member
            access_key = credentials_model.AWSAccessSKey.objects.get(pk=uuid.UUID(_id))
        except DoesNotExist:
            current_app.logger.info(
                f'Failed to fetch AWS access key (_id={_id}, error=Not found)')
            return '', 404
        data = {
            '_id': access_key._id,
            'alias': access_key.alias,
            'region_name': access_key.region_name,
            'access_key': access_key.access_key,
            'secret_key': '$encrypted' if access_key.secret_key else None,
        }
        current_app.logger.info(f'Fetched AWS access key (_id={_id})')
        return jsonify(data), 200

    @require_auth()
    def put(self, _id):
        try:
            # pylint: disable=no-member
            access_key = credentials_model.AWSAccessSKey.objects.get(pk=uuid.UUID(_id))
        except DoesNotExist:
            current_app.logger.info(
                f'Failed to update AWS access key (_id={_id}, error=Not found)')
            return '', 404
        request_data = request.get_json()
        # encrypted_data = request_data.get('data')
        # if encrypted_data:
        #     decrypted_data = rsa_decrypt(request_data.get('data'))
        #     request_data = json.loads(decrypted_data)
        # else:
        #     request_data = {}
        access_key.alias = request_data.get('alias')
        access_key.region_name = request_data.get('region_name')
        access_key.access_key = request_data.get('access_key')
        secret_key = request_data.get('secret_key')
        if secret_key:
            access_key.secret_key = secret_key
        access_key.updated_at = utc_now()
        try:
            access_key.save()
        except (DuplicateKeyError, NotUniqueError):
            error = 'AWS access key with same alias already exists'
            current_app.logger.info(
                f'Failed to update AWS access key (_id={_id}, error={error})')
            return jsonify({'error': error}), 400
        except ValidationError as ex:
            current_app.logger.info(f'Failed to update AWS access key (_id={_id}, error={ex})')
            return jsonify({'error': str(ex)}), 400
        current_app.logger.info(f'Updated AWS access key (_id={_id})')
        return '', 200

    @require_auth()
    def delete(self, _id):
        try:
            # pylint: disable=no-member
            access_key = credentials_model.AWSAccessSKey.objects.get(pk=uuid.UUID(_id))
        except DoesNotExist:
            current_app.logger.info(
                f'Failed to delete AWS access key (_id={_id}, error=Not Found)')
            return '', 404
        access_key.delete()
        current_app.logger.info(f'Deleted AWS access key (_id={_id})')
        return '', 204
