import functools
import uuid
from copy import deepcopy
from enum import Enum, unique

from mongoengine import Document, fields
from mongoengine.document import EmbeddedDocument
from mongoengine.errors import DoesNotExist

from nightowl.config import app_config
from nightowl.models import cusfields
from nightowl.utils.datetime import str_to_datetime, utc_now
from nightowl.utils.jsonrpc import JsonRpcClient
from nightowl.utils.model import import_model


class SchedulerClient(JsonRpcClient):

    def __init__(self):
        super().__init__(app_config.scheduler_url)

    def execute(self, func, *args, **kwargs):
        result_data = self.send(func, *args, **kwargs)
        if 'result' in result_data:
            return result_data['result']
        error_data = result_data['error']
        exception_data = error_data.get('data', {}).get('exception')
        if exception_data:
            ex_module = exception_data['module']
            ex_name = exception_data['name']
            ex_args = exception_data['args']
            ex_type = import_model(ex_module, ex_name)
            try:
                exception = ex_type(*ex_args)
            except Exception:
                exception = Exception(*ex_args)
            raise exception
        raise Exception()

    def __getattr__(self, name):
        return functools.partial(self.execute, name)


@unique
class TaskStatus(Enum):
    PENDING = 'Pending'
    RUNNING = 'Running'


@unique
class TaskType(Enum):
    DATE = 'date'
    INTERVAL = 'interval'
    CRON = 'cron'


@unique
class TaskResultStatus(Enum):
    RUNNING = 0
    SUCCESS = 1
    MANUALLY_STOPPED = -1
    FAILURE = -2
    EXCEPTION = -10


@unique
class LogLevel(Enum):
    DEBUG = 0
    INFO = 1
    WARNING = 2
    ERROR = 3
    EXCEPTION = 4


class TaskLog(EmbeddedDocument):
    time = cusfields.DateTimeField(required=True)
    message = fields.StringField(required=True)
    level = fields.EnumField(LogLevel, default=LogLevel.INFO)


class TaskResult(Document):
    _id = fields.UUIDField(primary_key=True)
    task_id = fields.UUIDField(required=True)
    status = fields.EnumField(TaskResultStatus, default=TaskResultStatus.RUNNING)
    ran_by = fields.StringField(required=True)
    ran_at = cusfields.DateTimeField(required=True)
    logs = fields.EmbeddedDocumentListField(TaskLog)
    ended_at = cusfields.DateTimeField()

    meta = {'allow_inheritance': True}

    def add_log(self, message, level=None):
        task_log = TaskLog(
            time=utc_now(),
            message=message,
        )
        if level is not None:
            task_log.level = level
        self.update(push__logs=task_log)


class Context(dict):

    def get_value(self, *keys, default=None):
        d = self
        for key in keys:
            if key not in d:
                return default
            d = d[key]
        return d

    def set_value(self, *keys, value):
        if not keys:
            raise ValueError('Please provide at least one key')
        d = self
        for key in keys[:-1]:
            if key not in d:
                d[key] = {}
            d = d[key]
        d[keys[-1]] = value

    def clone(self):
        return deepcopy(self)

    @property
    def task(self):
        task_id = self.get_value('task', '_id')
        if not task_id:
            return None
        try:
            # pylint: disable=no-member
            return Task.objects.get(pk=uuid.UUID(task_id))
        except DoesNotExist:
            return None

    @property
    def task_result(self):
        task_id = self.get_value('task_result', '_id')
        if not task_id:
            return None
        try:
            # pylint: disable=no-member
            return TaskResult.objects.get(pk=uuid.UUID(task_id))
        except DoesNotExist:
            return None


class Task(Document):
    _id = fields.UUIDField(primary_key=True)
    type = fields.EnumField(TaskType, required=True)
    descr = fields.StringField()
    active = fields.BooleanField(default=True)
    status = fields.EnumField(TaskStatus, default=TaskStatus.PENDING)
    yaml_content = fields.StringField(required=True)
    last_activated_at = cusfields.DateTimeField()
    last_activated_by = fields.StringField()
    last_ran_by = fields.StringField()
    last_ran_at = cusfields.DateTimeField()
    last_result = fields.LazyReferenceField(TaskResult)
    created_at = cusfields.DateTimeField(required=True)
    updated_at = cusfields.DateTimeField()

    # Date task
    run_date = cusfields.DateTimeField()

    # Interval task
    weeks = fields.IntField()
    days = fields.IntField()
    hours = fields.IntField()
    minutes = fields.IntField()
    seconds = fields.IntField()

    # CRON task
    year = fields.StringField()
    month = fields.StringField()
    day = fields.StringField()
    week = fields.StringField()
    # Number of weekday (0-6 for mon, tue, wed, thu, fri, sat, sun)
    day_of_week = fields.StringField()
    hour = fields.StringField()
    minute = fields.StringField()
    second = fields.StringField()

    # Interval task and CRON task
    start_date = cusfields.DateTimeField()
    end_date = cusfields.DateTimeField()

    task_result_model = TaskResult
    scheduler = SchedulerClient()

    meta = {'allow_inheritance': True}

    @property
    def trigger_args(self):
        if self.type == TaskType.DATE:
            return {
                'trigger': 'date',
                'run_date': self.run_date,
            }
        if self.type == TaskType.INTERVAL:
            return {
                'trigger': 'interval',
                'weeks': self.weeks,
                'days': self.days,
                'hours': self.hours,
                'minutes': self.minutes,
                'seconds': self.seconds,
                'start_date': self.start_date,
                'end_date': self.end_date,
            }
        if self.type == TaskType.CRON:
            return {
                'trigger': 'cron',
                'year': self.year,
                'month': self.month,
                'day': self.day,
                'week': self.week,
                'day_of_week': self.day_of_week,
                'hour': self.hour,
                'minute': self.minute,
                'second': self.second,
                'start_date': self.start_date,
                'end_date': self.end_date,
            }
        return {}

    @property
    def job(self):
        return self.scheduler.get_job(str(self._id))

    @property
    def name(self):
        return self.__class__.__name__

    func = None

    def from_yaml(self, yaml_content):
        # To be implemented
        pass

    def save(self, *args, **kwargs):
        task_id = str(self._id)
        if self.scheduler.get_job(task_id):
            if self.active:
                self.scheduler.reschedule_job(task_id, **self.trigger_args)
            else:
                self.scheduler.remove_job(task_id)
        elif self.active:
            should_add_job = True
            task_id = str(self._id)
            if self.type == TaskType.DATE:
                should_add_job = str_to_datetime(self.run_date) > utc_now() \
                    if self.run_date else False
            if should_add_job:
                self.scheduler.add_job(
                    'nightowl.worker.tasks.run:run_task.delay', args=(task_id, 'scheduler'),
                    id=task_id, name=self.name, **self.trigger_args)
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        scheduler = SchedulerClient()
        task_id = str(self._id)
        if self.active:
            try:
                scheduler.remove_job(task_id)
            except Exception:
                pass
        super().delete(*args, **kwargs)
