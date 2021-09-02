from mongoengine import Document, fields
from mongoengine.errors import ValidationError

from nightowl.models import cusfields


class CredentialBase(Document):
    _id = fields.UUIDField(primary_key=True)
    alias = fields.StringField(required=True)
    created_at = cusfields.DateTimeField(required=True)
    updated_at = cusfields.DateTimeField()

    meta = {
        'abstract': True,
        'indexes': [
            {
                'fields': ['alias'],
                'unique': True,
            }
        ]
    }


class CLICredentials(CredentialBase):
    username = fields.StringField(required=True)
    password = fields.StringField()
    private_key = fields.StringField()
    private_key_file = fields.StringField()

    meta = {
        'collection': 'cli_credentials',
    }

    def clean(self):
        if not self.password and not self.private_key and not self.private_key_file:
            raise ValidationError(
                "'password', 'private_key' or 'private_key_file' must be set")


class AWSAccessSKey(CredentialBase):
    region_name = fields.StringField(required=True)
    access_key = fields.StringField(required=True)
    secret_key = fields.StringField(required=True)

    meta = {
        'collection': 'aws_access_key',
    }


def get_credential_mapping():
    return {c._get_collection_name(): c for c in (CLICredentials, AWSAccessSKey)}
