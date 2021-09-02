import logging
import os
import traceback
import uuid

from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.jobstores.mongodb import MongoDBJobStore
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
from mongoengine import connect

from nightowl.config import mongodb_config, scheduler_config
from nightowl.models import task as task_model
from nightowl.utils.datetime import str_to_datetime, utc_now
from nightowl.utils.flask import Flask
from nightowl.utils.jsonrpc import JsonRpcServer
from nightowl.utils.logging import DatetimeFormatter, setup_logger


class SchedulerLogFormatter(DatetimeFormatter):

    def format(self, record):
        record.pid = os.getpid()
        return super().format(record)


jobstores = {
    'default': MemoryJobStore(),
    'mongo': MongoDBJobStore(
        database=scheduler_config.database,
        collection=scheduler_config.collection,
        host=mongodb_config.connection_str,
    ),
}


class SchedulerServer(JsonRpcServer):

    def __init__(self, app):
        super().__init__(app)
        connect(host=mongodb_config.connection_str)
        try:
            self._scheduler = BackgroundScheduler(
                jobstores=jobstores,
                timezone=scheduler_config.timezone)
            self._scheduler.start()
            apscheduler_logger = logging.getLogger('apscheduler.scheduler')
            setup_logger(apscheduler_logger, scheduler_config.log_level,
                         scheduler_config.log_file,
                         '[%(asctime)s][%(levelname)s][scheduler]: %(message)s')
            setup_logger(app.logger, scheduler_config.log_level,
                         scheduler_config.log_file,
                         '[%(asctime)s][%(levelname)s][%(pid)s]: %(message)s',
                         SchedulerLogFormatter)
            app.logger.info('Started Scheduler')
        except Exception:
            app.logger.error(f'Failed to start scheduler (error={traceback.format_exc()})')
            return
        self.restore_jobs()

    def restore_jobs(self):
        try:
            # pylint: disable=no-member
            tasks = task_model.Task.objects(active=True)
            for task in tasks:
                task_id = str(task._id)
                should_add_job = True
                if task.type == task_model.TaskType.DATE:
                    should_add_job = str_to_datetime(task.run_date) > utc_now() \
                        if task.run_date else False
                if should_add_job:
                    self.app.logger.info(f'Resoring task {task_id}')
                    self.add_job(
                        'nightowl.worker.tasks.run:run_task.delay', args=(task_id, 'scheduler'),
                        id=task_id, name=task.name, **task.trigger_args)
                    self.app.logger.info(f'Restored task {task_id}')
        except Exception:
            self.app.logger.error(
                f'Failed to restore the tasks in scheduler (error={traceback.format_exc()})')

    def add_job(self, func, *args, **kwargs):
        kwargs['id'] = kwargs.get('id', str(uuid.uuid4()))
        job = self._scheduler.add_job(func, *args, **kwargs)
        self.app.logger.info(f'Added job (_id={job.id}, func={job.func_ref}, '
                             f'args={job.args}, kwargs={job.kwargs})')
        return job.id

    def modify_job(self, job_id, jobstore=None, **changes):
        job = self._scheduler.modify_job(job_id, jobstore, **changes)
        self.app.logger.info(f'Modified job (_id={job.id}, func={job.func_ref}, '
                             f'args={job.args}, kwargs={job.kwargs})')
        return job.id

    def reschedule_job(self, job_id, jobstore=None, trigger=None, **trigger_args):
        job = self._scheduler.reschedule_job(job_id, jobstore, trigger, **trigger_args)
        self.app.logger.info(f'Rescheduled job (_id={job.id}, func={job.func_ref}, '
                             f'args={job.args}, kwargs={job.kwargs})')
        return job.id

    def pause_job(self, job_id, jobstore=None):
        job = self._scheduler.pause_job(job_id, jobstore)
        self.app.logger.info(f'Paused job (_id={job.id})')
        return job.id

    def resume_job(self, job_id, jobstore=None):
        job = self._scheduler.resume_job(job_id, jobstore)
        self.app.logger.info(f'Resumed job (_id={job.id})')
        return job.id

    def remove_job(self, job_id, jobstore=None):
        self._scheduler.remove_job(job_id, jobstore)
        self.app.logger.info(f'Removed job (_id={job_id})')

    def _get_job_data(self, job):

        def get_trigger_data(trigger):
            if isinstance(trigger, CronTrigger):
                fields = {f.name: str(f) for f in trigger.fields}
                return {
                    'type': 'cron',
                    **fields,
                    'start_date': trigger.start_date,
                    'end_date': trigger.end_date,
                }
            if isinstance(trigger, DateTrigger):
                return {
                    'type': 'date',
                    'run_date': trigger.run_date,
                }
            if isinstance(trigger, IntervalTrigger):
                return {
                    'type': 'interval',
                    'interval': trigger.interval_length,
                }
            raise TypeError()

        return {
            '_id': job.id,
            'name': job.name,
            'trigger': get_trigger_data(job.trigger),
            'next_run_time': job.next_run_time,
            'func': job.func_ref,
            'args': job.args,
            'kwargs': job.kwargs,
        }

    def get_job(self, job_id):
        job = self._scheduler.get_job(job_id)
        if not job:
            self.app.logger.info(
                f'Failed to get job (_id={job_id}, error=Not found)')
            return None
        self.app.logger.info(f'Got job (_id={job_id})')
        return self._get_job_data(job)

    def get_jobs(self, jobstore=None):
        jobs = self._scheduler.get_jobs(jobstore)
        data_list = [self._get_job_data(job) for job in jobs]
        self.app.logger.info('Got jobs')
        return data_list


def create_app():
    app = Flask(__name__)
    SchedulerServer(app)
    return app
