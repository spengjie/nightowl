from enum import Enum, unique

from mongoengine import fields, Document, DynamicDocument, EmbeddedDocument
from mongoengine.errors import DoesNotExist

from nightowl.models import cusfields
from nightowl.models.modules import credentials as credential_model
from nightowl.utils.datetime import utc_now


class DocumentBase(Document):
    tags = fields.ListField(field=fields.StringField())
    created_at = cusfields.DateTimeField(required=True)
    updated_at = cusfields.DateTimeField()

    meta = {
        'abstract': True,
        'index_cls': False,
    }

    @property
    def type(self):
        return self._cls  # pylint: disable=no-member

    def save(self, *args, **kwargs):
        if not self.created_at:
            self.created_at = utc_now()
        self.updated_at = utc_now()
        super().save(*args, **kwargs)


@unique
class DataTableColumnCompareType(Enum):
    STANDARD = 1
    KEY = 2
    UNIMPORTANT = 3


class DataTableHeader(EmbeddedDocument):
    name = fields.StringField(required=True)
    display_name = fields.StringField(required=True)
    type = fields.StringField(default='str')
    compare_type = fields.EnumField(
        DataTableColumnCompareType,
        default=DataTableColumnCompareType.STANDARD)


class DataTable(DocumentBase):
    _id = fields.UUIDField(primary_key=True)
    noid = fields.StringField(required=True)
    name = fields.StringField(required=True)
    headers = fields.EmbeddedDocumentListField(DataTableHeader, required=True)
    rows = fields.ListField()
    attributes = fields.DictField()
    # hash = fields.StringField(required=True)

    meta = {
        'indexes': [
            'name',
            {
                'fields': ('noid', 'name'),
                'unique': True,
            }
        ]
    }


class NetworkObjectSettings(DynamicDocument):
    _id = fields.StringField(primary_key=True)
    credentials = fields.DictField()
    created_at = cusfields.DateTimeField(required=True)
    updated_at = cusfields.DateTimeField(required=True)

    def save(self, *args, **kwargs):
        if not self.created_at:
            self.created_at = utc_now()
        self.updated_at = utc_now()
        super().save(*args, **kwargs)

    def update(self, *args, **kwargs):
        super().update(set__updated_at=utc_now(), *args, **kwargs)

    def to_dict(self):
        credentials = {}
        for name, value in self.credentials.items():
            if isinstance(value, dict) and 'ref' in value:
                try:
                    credential_mapping = credential_model.get_credential_mapping()
                    credential_cls = credential_mapping[name]
                    credential = credential_cls.objects.get(pk=value['ref'])
                    credentials[name] = credential.to_mongo().to_dict()
                except DoesNotExist:
                    credentials[name] = None
        data = self.to_mongo().to_dict()
        data['credentials'] = credentials
        return data


class NetworkObject(DocumentBase):
    _id = fields.StringField(primary_key=True)
    name = fields.StringField(required=True)

    meta = {
        'abstract': True,
    }

    @staticmethod
    def get_settings(noid):
        try:
            # pylint: disable=no-member
            settings = NetworkObjectSettings.objects.get(pk=noid)
            return settings
        except DoesNotExist:
            return NetworkObjectSettings()

    @property
    def settings(self):
        return self.get_settings(self._id)


class NetworkObjectRef(EmbeddedDocument):
    _id = fields.StringField(required=True)
    name = fields.StringField(required=True)


class NetworkNode(NetworkObject):
    group = fields.EmbeddedDocumentField(NetworkObjectRef)
    last_discovered_at = cusfields.DateTimeField(required=True)

    is_group = False
    driver = None
    color = None
    type_icon = None
    icon = None

    meta = {
        'allow_inheritance': True,
        'indexes': [
            'name',
        ]
    }


class NetworkObjectGroup(NetworkObject):
    members = fields.EmbeddedDocumentListField(NetworkObjectRef)
    created_at = cusfields.DateTimeField(required=True)
    updated_at = cusfields.DateTimeField()

    color = None
    type_icon = None
    icon = None

    meta = {
        'allow_inheritance': True,
        'indexes': [
            'name',
        ]
    }


class NetworkIPv4Address(EmbeddedDocument):
    addr = fields.StringField(required=True)
    prefix_len = fields.IntField(required=True)
    subnet = fields.StringField(required=True)


class NetworkInterface(NetworkObject):
    noid = fields.StringField(required=True)
    is_boundary = fields.BooleanField()
    ipv4_addrs = fields.EmbeddedDocumentListField(NetworkIPv4Address)
    last_discovered_at = cusfields.DateTimeField(required=True)

    color = None
    type_icon = None
    icon = None

    meta = {
        'allow_inheritance': True,
        'indexes': [
            'noid',
            'is_boundary',
        ]
    }


@unique
class LinkType(Enum):
    TO_PEER = 1
    TO_MEDIUM = 2


class NetworkLink(NetworkObject):
    _id = fields.StringField(primary_key=True)
    name = fields.StringField()
    noid1 = fields.StringField(required=True)
    noid2 = fields.StringField(required=True)
    noiid1 = fields.StringField()
    noiid2 = fields.StringField()
    link_type = fields.EnumField(LinkType, default=LinkType.TO_PEER)

    color = None
    type_icon = None
    icon = None

    meta = {
        'allow_inheritance': True,
        'indexes': [
            'name',
        ]
    }
