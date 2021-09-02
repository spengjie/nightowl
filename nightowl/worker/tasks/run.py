import traceback
import uuid

from celery import chord
from celery.utils.log import get_task_logger
from mongoengine.errors import DoesNotExist

from nightowl.models import task as task_model
from nightowl.utils.datetime import utc_now
from nightowl.utils.model import as_model, import_model
from nightowl.worker import app


logger = get_task_logger(__name__)


@app.task()
def run_task(task_id, by):
    logger.info(f'Start to run task (_id={task_id})')
    task_not_found = False
    if isinstance(task_id, str):
        try:
            task_id = uuid.UUID(task_id)
        except Exception:
            task_not_found = True
    try:
        task = task_model.Task.objects.get(pk=task_id)  # pylint: disable=no-member
    except DoesNotExist:
        task_not_found = True

    if task_not_found:
        logger.error(f'Failed to run task (_id={task_id}, error=Not found)')
        return None

    if task.status == task_model.TaskStatus.RUNNING:
        return
    now = utc_now()
    task.status = task_model.TaskStatus.RUNNING
    task.last_ran_by = by
    task.last_ran_at = now
    task_result = task.task_result_model(
        _id=uuid.uuid4(),
        task_id=task._id,
        ran_by=task.last_ran_by,
        ran_at=task.last_ran_at,
    )
    task_result.save()
    task.last_result = task_result
    task.save()
    context = task_model.Context({
        'task': {'_id': str(task._id)},
        'task_result': {'_id': str(task_result._id)},
    })
    try:
        if task.func:
            return import_model(task.func)(context)
        elif task.module:
            return run_module(context, task.module)
        raise NotImplementedError()
    except Exception as ex:
        logger.exception(f'Failed to run task (_id={task_id}, error={traceback.format_exc()})')
        task_result.add_log(f'Failed to run task (error={ex})', task_model.LogLevel.EXCEPTION)
        task_result.status = task_model.TaskResultStatus.EXCEPTION
        task_result.ended_at = utc_now()
        task_result.save()
    finally:
        task.status = task_model.TaskStatus.PENDING
        task.save()


def module_callback(results, context):
    context = task_model.Context(context)
    task = context.task
    task_result = context.task_result
    if task_result and task_result.status == task_model.TaskResultStatus.RUNNING:
        task_result.add_log('Ran module successfully')
        task_result.status = task_model.TaskResultStatus.SUCCESS
        task_result.ended_at = utc_now()
        task_result.save()
    if task:
        task.status = task_model.TaskStatus.PENDING
        task.save()


def module_error_callback(worker_task_result_id, context):
    context = task_model.Context(context)
    task = context.task
    task_result = context.task_result
    if task_result:
        task_result.add_log(
            f'Ran module interrupted with error (worker_task={worker_task_result_id})',
            task_model.LogLevel.EXCEPTION)
        task_result.status = task_model.TaskResultStatus.EXCEPTION
        task_result.ended_at = utc_now()
        task_result.save()
    if task:
        task.status = task_model.TaskStatus.PENDING
        task.save()


@app.task()
def run_module(context, module_model):
    context = task_model.Context(context)
    task_result = context.task_result
    message = f'Start to run module (module={module_model})'
    logger.info(message)
    task_result.add_log(message)
    try:
        module = __import__(module_model, fromlist=['main'])
    except LookupError:
        message = (f'Failed to run module (module={module_model}, '
                   'error=Not found)')
        logger.error(message)
        task_result.add_log(message, task_model.LogLevel.ERROR)
        return
    try:
        main = getattr(module, 'main')
    except Exception:
        message = (f'Failed to run module (module={module_model}, '
                   'error=main not found)')
        logger.error(message)
        task_result.add_log(message, task_model.LogLevel.ERROR)
        return
    task_group = main(context)
    sig = chord(
        task_group,
        run_callback.s(context, as_model(module_callback))
    ).on_error(
        run_callback.s(context, as_model(module_error_callback))
    )
    sig.delay()


@app.task()
def run_plugin(context, plugin_model, method_name, *args, **kwargs):
    context = task_model.Context(context)
    task_result = context.task_result
    message = f'Start to run plugin (plugin={plugin_model}, method={method_name})'
    logger.info(message)
    task_result.add_log(message)
    try:
        plugin = import_model(plugin_model)
    except LookupError:
        message = (f'Failed to run plugin (plugin={plugin_model}, method={method_name}, '
                   'error=Not found)')
        logger.error(message)
        task_result.add_log(message, task_model.LogLevel.ERROR)
        return None
    plugin_ins = plugin(context)
    try:
        method = getattr(plugin_ins, method_name)
    except Exception:
        message = (f'Failed to run plugin (plugin={plugin_model}, method={method_name}, '
                   'error=Method not found)')
        logger.error(message)
        task_result.add_log(message, task_model.LogLevel.ERROR)
        return None
    return method(*args, **kwargs)


@app.task()
def run_callable(callable, *args, **kwargs):
    logger.info(f'Start to run callable (callable={callable})')
    try:
        model = import_model(callable)
    except LookupError:
        logger.error(
            f'Failed to run callable (callable={callable}, '
            'error=Not found)')
        return None
    return model(*args, **kwargs)


@app.task()
def run_callback(result, context, callback, *args, **kwargs):
    logger.info(f'Start to run callback (callback={callback})')
    try:
        model = import_model(callback)
    except LookupError:
        logger.error(
            f'Failed to run callback (callback={callback}, '
            'error=Not found)')
        return None
    return model(result, context, *args, **kwargs)
