from nightowl.utils.security import encrypt
import re
import uuid
from datetime import timedelta
from enum import Enum, unique

from mongoengine import Document, fields
from mongoengine.document import EmbeddedDocument
from mongoengine.errors import DoesNotExist, ValidationError

from nightowl.models import cusfields
from nightowl.models.task import Task
from nightowl.utils.datetime import add_tzinfo, utc_now


@unique
class OrganizationNodeType(Enum):
    PERSON = 'Person'
    GROUP = 'Group'


class SystemSettings(Document):
    _id = fields.StringField(primary_key=True)
    updated_at = cusfields.DateTimeField()

    meta = {'allow_inheritance': True}

    name = None
    encrypted_fields = []

    def __init__(self, *args, **values):
        values['_id'] = self.__class__.name
        super().__init__(*args, **values)

    @classmethod
    def fetch(cls):
        return cls.objects.first()  # pylint: disable=no-member

    @classmethod
    def get(cls):
        return cls.fetch() or cls(_id=cls.name)

    @classmethod
    def put(cls, **values):
        settings = cls(**values)
        settings.updated_at = utc_now()
        settings.save()
        return settings


@unique
class EmailAuthType(Enum):
    NONE = 'None'
    SSL = 'SSL'
    TLS = 'TLS'


class EmailSettings(SystemSettings):
    host = fields.StringField(required=True)
    port = fields.IntField(required=True)
    auth_type = fields.EnumField(EmailAuthType, required=True, default=EmailAuthType.NONE)
    email = fields.StringField(required=True)
    salt = fields.StringField(required=True)
    password = fields.StringField(required=True)

    name = 'email'


@unique
class AuthType(Enum):
    LOCAL = 'local'
    SSO = 'sso'
    BOTH = 'both'


class SSOSettings(EmbeddedDocument):
    client_id = fields.StringField(required=True)
    client_secret = fields.StringField(required=True)
    salt = fields.StringField(required=True)
    verify_certificate = fields.BooleanField(default=False)
    auth_url = fields.StringField(required=True)
    token_url = fields.StringField(required=True)
    user_api_url = fields.StringField(required=True)
    session_api_url = fields.StringField(required=True)
    logout_api_url = fields.StringField(required=True)
    users_api_url = fields.StringField(required=True)
    groups_api_url = fields.StringField(required=True)
    username = fields.StringField(required=True)
    password = fields.StringField(required=True)


class AuthSettings(SystemSettings):
    type = fields.EnumField(AuthType, default=AuthType.LOCAL)
    sso = fields.EmbeddedDocumentField(SSOSettings)

    name = 'auth'


class Permission:
    permissions = [
        'admin:read',
        'admin:write',
        'admin.groups:read',
        'admin.groups:write',
        'admin.groups:write.add',
        'admin.groups:write.delete',
        'admin.groups:write.edit',
        'admin.scheduler:read',
        'admin.settings:read',
        'admin.settings:write',
        'admin.settings.auth:read',
        'admin.settings.auth:write',
        'admin.settings.email:read',
        'admin.settings.email:write',
        'admin.users:read',
        'admin.users:write',
        'admin.users:write.add',
        'admin.users:write.delete',
        'admin.users:write.edit',
    ]

    @classmethod
    def list(cls):
        return cls.permissions

    @classmethod
    def check(cls, permissions, required_permissions):

        def get_regex(exp):
            regex_segs = []
            segs = [seg.replace('*', '[\\w.]+') for seg in exp.split('.')]
            length = len(segs)
            for index in range(length):
                regex_segs.append('\\.'.join(segs[0: length - index]))
            return f'({"|".join(regex_segs)})'

        missed = []
        for required in required_permissions:
            permitted = False
            for or_permission in required.split('|'):
                try:
                    module_exp, permission_exp = or_permission.split(':')
                except ValueError:
                    module_exp, permission_exp = or_permission, ''
                regex = re.compile(f'^{get_regex(module_exp)}:{get_regex(permission_exp)}$', re.I)
                for permission in permissions:
                    if regex.match(permission):
                        permitted = True
                        break

            if not permitted:
                missed.append(required)
        return bool(not missed), missed

    @staticmethod
    def _sort_key(permission):
        try:
            module_exp, permission_exp = permission.split(':')
        except ValueError:
            module_exp, permission_exp = permission, ''
        return (len(module_exp.split('.')), module_exp,
                len(permission_exp.split('.')), permission_exp)

    @classmethod
    def sort(cls, permissions):
        return sorted(permissions, key=cls._sort_key)

    @staticmethod
    def ancestors(permission):
        ancestors = set()
        try:
            module_exp, permission_exp = permission.split(':')
        except ValueError:
            module_exp, permission_exp = permission, ''
        module_segs = module_exp.split('.')
        permission_segs = permission_exp.split('.')
        ancestor_modules = ['.'.join(module_segs[:index + 1]) for index in range(len(module_segs))]
        ancestor_permissions = ['.'.join(permission_segs[:index + 1])
                                for index in range(len(permission_segs))]
        for amodule in ancestor_modules:
            for apermission in ancestor_permissions:
                ancestors.add(f'{amodule}:{apermission}')
        return ancestors

    @classmethod
    def merge(cls, permissions):
        permissions = Permission.sort(permissions)
        merged = set()
        for permission in permissions:
            if merged:
                ancestors = Permission.ancestors(permission)
                if ancestors & merged:
                    continue
            merged.add(permission)
        return Permission.sort(merged)


class Group(Document):
    _id = fields.UUIDField(primary_key=True)
    type = fields.StringField(required=True)
    name = fields.StringField(required=True)
    permissions = fields.ListField(field=fields.StringField())
    created_at = cusfields.DateTimeField(required=True)
    updated_at = cusfields.DateTimeField()


class User(Document):
    _id = fields.UUIDField(primary_key=True)
    type = fields.StringField(required=True)
    disabled = fields.BooleanField(default=False)
    name = fields.StringField(required=True)
    salt = fields.StringField()
    username = fields.StringField(required=True)
    password = fields.StringField()
    email = fields.EmailField(required=True)

    is_employee = fields.BooleanField(default=False)
    employee_id = fields.StringField()
    english_name = fields.StringField()
    hire_date = cusfields.DateTimeField()
    title = fields.StringField()
    dept = fields.StringField()
    manager = fields.DictField()
    is_manager = fields.BooleanField(default=False)
    direct_reports = fields.ListField(field=fields.DictField())
    city = fields.StringField()
    immutable_groups = fields.ListField(field=fields.DictField())
    groups = fields.ListField(field=fields.DictField())
    created_at = cusfields.DateTimeField(required=True)
    updated_at = cusfields.DateTimeField()
    meta = {
        'indexes': [
            'disabled',
            'name',
            'email',
            'is_employee',
            {
                'fields': ['username'],
                'unique': True,
            },
        ]
    }

    @property
    def all_groups(self):
        return sorted([*self.immutable_groups, *self.groups], key=lambda x: x['name'])

    @property
    def active_direct_reports(self):
        return [dr for dr in self.direct_reports if not dr['disabled']]

    @property
    def _permissions(self):
        permissions = []
        for group_info in self.all_groups:
            try:
                group = Group.objects.get(pk=group_info['_id'])  # pylint: disable=no-member
            except DoesNotExist:
                continue
            permissions.extend(group.permissions)
        return Permission.merge(permissions)

    @property
    def permissions(self):
        return Permission.sort(self._permissions)

    def lack(self, required_permissions):
        required_permissions = Permission.merge(required_permissions)
        _, missed = Permission.check(self._permissions, required_permissions)
        return missed

    def set_manager(self, manager_id):
        if self.type != 'Local':
            return
        if not self.manager and not manager_id:
            return
        if manager_id:
            if not isinstance(manager_id, uuid.UUID):
                manager_id = uuid.UUID(manager_id)
            if self.manager and self.manager['_id'] == manager_id:
                return

        # Remove from old manager's direct reports
        if self.manager:
            old_manager = User.objects.get(pk=self.manager['_id'])  # pylint: disable=no-member
            for index, direct_report in enumerate(old_manager.direct_reports):
                if direct_report['_id'] == self._id:
                    old_manager.direct_reports.pop(index)
                    old_manager.save()
                    break

        if not manager_id:
            self.manager = None
            return
        try:
            new_manager = User.objects.get(pk=manager_id)  # pylint: disable=no-member
        except DoesNotExist:
            self.manager = None
            return
        self.manager = {
            '_id': new_manager._id,
            'name': new_manager.name,
        }
        # Add into new manager's direct reports
        for direct_report in new_manager.direct_reports:
            if direct_report['_id'] == self._id:
                break
        else:
            new_manager.direct_reports.append({
                '_id': self._id,
                'name': self.name,
                'disabled': self.disabled,
            })
            new_manager.save()


class Organization(Document):
    _id = fields.UUIDField(primary_key=True)
    name = fields.StringField(required=True)
    type = fields.EnumField(OrganizationNodeType, required=True)
    path = fields.StringField(required=True)
    children = fields.ListField()
    updated_at = cusfields.DateTimeField(required=True)

    meta = {
        'indexes': [
            'name',
            {
                'fields': ['path'],
                'unique': True,
            }
        ]
    }

    def to_tree(self):
        return {
            '_id': self._id,
            'name': self.name,
            'type': self.type.value,  # pylint: disable=no-member
            'path': self.path,
            'children': self.children,
        }

    @staticmethod
    def iter_tree(root):

        def _iter_node(node):
            yield node
            if node['type'] == OrganizationNodeType.GROUP.value:
                for child in node['children']:
                    for child_node in _iter_node(child):
                        yield child_node
        if not root:
            yield []
            return
        yield root
        for child in root['children']:
            for node in _iter_node(child):
                yield node

    @staticmethod
    def get_sub_tree(root, person_ids):
        if root['type'] == OrganizationNodeType.GROUP.value:
            children = []
            tree_node = {
                '_id': root['_id'],
                'name': root['name'],
                'type': root['type'],
                'path': root['path'],
                'children': children,
            }
            for child in root['children']:
                sub_tree = Organization.get_sub_tree(child, person_ids)
                if sub_tree:
                    children.append(sub_tree)
            if not children:
                tree_node = None
        else:
            if root['_id'] in person_ids:
                tree_node = root
            else:
                tree_node = None
        return tree_node


class UserSession(Document):
    _id = fields.UUIDField(primary_key=True)
    user = fields.ReferenceField(User)
    client_ip = fields.StringField(required=True)
    login_at = cusfields.DateTimeField(required=True)
    expires = cusfields.DateTimeField(required=True)
    last_accessed = cusfields.DateTimeField(required=True)
    sso_at = fields.StringField()  # SSO access token

    def refresh(self):
        now = utc_now()
        expire = timedelta(days=30)
        self.expires = now + expire
        self.last_accessed = now
        self.save()

    def expired(self):
        return add_tzinfo(self.expires) < utc_now()


class SSOSyncTask(Task):
    name = 'SSO Sync'
    func = 'nightowl.utils.sync:sync'
