from nightowl.modules import build_explorers, build_links
from nightowl.worker.tasks.run import run_plugin


def main(context):
    task = context.task
    task_group = []
    if not task:
        return task_group
    for discovery_method in task.methods:
        if not discovery_method.options.enabled:
            continue
        plugin_context = context.clone()
        plugin_context['options'] = discovery_method.options.to_mongo()
        discovery_plugin = f'{discovery_method.type}:DiscoveryPlugin'
        plugin_sig = run_plugin.si(plugin_context, discovery_plugin, 'run')
        task_group.append(plugin_sig)
    if task.build_links:
        plugin_context = context.clone()
        plugin_context['source'] = 'discovery'
        task_group.extend(build_links.main(plugin_context))
    if task.build_explorers:
        plugin_context = context.clone()
        plugin_context['source'] = 'discovery'
        task_group.extend(build_explorers.main(plugin_context))
    return task_group
