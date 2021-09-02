from nightowl.worker.tasks.run import run_plugin


def main(context):
    task_group = []
    explorer_plugin = 'nightowl.plugins.explorer.network_object:ExplorerPlugin'
    plugin_sig = run_plugin.si(context, explorer_plugin, 'build')
    task_group.append(plugin_sig)
    return task_group
