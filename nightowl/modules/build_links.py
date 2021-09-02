from nightowl.plugins.link.base import LinkBase
from nightowl.utils.model import as_model
from nightowl.worker.tasks.run import run_plugin


def main(context):
    task_group = []
    for plugin in LinkBase.plugins:
        plugin_sig = run_plugin.si(context, as_model(plugin), 'build')
        task_group.append(plugin_sig)
    return task_group
