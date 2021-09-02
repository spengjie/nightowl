from enum import Enum, unique

from mongoengine import Document, EmbeddedDocument, fields
from mongoengine.errors import ValidationError

from nightowl.models import cusfields


@unique
class ExplorerNodeType(Enum):
    FOLDER = 'Folder'
    NODE = 'Node'


class ExplorerNode(EmbeddedDocument):
    name = fields.StringField(required=True)
    type = fields.EnumField(ExplorerNodeType, required=True)
    ref_type = fields.StringField()
    ref_id = fields.StringField()
    icon = fields.StringField()
    path = fields.StringField()
    level = fields.IntField(default=0)
    parent = fields.StringField()
    children = fields.ListField()

    def clean(self):
        if self.type == ExplorerNodeType.NODE and (not self.ref_type or not self.ref_id):
            raise ValidationError(
                "'ref_type' and 'ref_id' must be set")


class Explorer(Document):
    name = fields.StringField(primary_key=True)
    nodes = fields.EmbeddedDocumentListField(ExplorerNode)
    updated_at = cusfields.DateTimeField(required=True)
