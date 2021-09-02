from celery import Celery
from celery.app.log import TaskFormatter
from celery.app.registry import TaskRegistry
from celery.signals import after_setup_logger, after_setup_task_logger, worker_process_init
from mongoengine import connect

from nightowl.config import amqp_config, mongodb_config, worker_config
from nightowl.utils.logging import DatetimeFormatter, setup_logger


class WorkerLogFormatter(DatetimeFormatter, TaskFormatter):

    def format(self, record):
        return TaskFormatter.format(self, record)


task_registry = TaskRegistry()
task_modules = [
    'nightowl.worker.tasks.run',
    'nightowl.worker.tasks.send_email',
]
app = Celery(__name__,
             broker=amqp_config.connection_str,
             backend=mongodb_config.connection_str,
             tasks=task_registry,
             include=task_modules)
app.conf.update(**worker_config.dict)


@worker_process_init.connect
def connect_mongodb(sender=None, conf=None, **kwargs):
    connect(host=mongodb_config.connection_str)


@after_setup_logger.connect
def setup_worker_logger(logger, *args, **kwargs):
    setup_logger(logger, worker_config.log_level, worker_config.log_file,
                 '[%(asctime)s][%(levelname)s][%(processName)s]: %(message)s',
                 WorkerLogFormatter)


@after_setup_task_logger.connect
def setup_worker_task_logger(logger, *args, **kwargs):
    setup_logger(logger, worker_config.log_level, worker_config.log_file,
                 '[%(asctime)s][%(levelname)s][%(processName)s]'
                 '[%(task_name)s(%(task_id)s)]: %(message)s',
                 WorkerLogFormatter)
