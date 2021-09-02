
from nightowl.models.modules.credentials import CLICredentials
from nightowl.plugins.discovery.base import DiscoveryBase, DriverSelector
from nightowl.utils.ip import IPList


def discover_one_ip(context, task_result, ip_addr):
    driver_selector = DriverSelector()
    selected_driver = driver_selector.match(ip_addr)
    if not selected_driver:
        return
    driver = selected_driver(context, host=ip_addr)
    discovered_network_objects = driver.discover()
    for network_object in discovered_network_objects:
        task_result.add_discovered(network_object, ip_addr)


class DiscoveryPlugin(DiscoveryBase):
    name = 'IP Discovery'
    credential_cls = CLICredentials

    def run(self):
        options = self.context.get('options', {})
        if options.get('use_all'):
            cli_credentials = CLICredentials.objects().order_by('alias')
        else:
            setting_ids = options.get('credentials', [])
            cli_credentials = CLICredentials.objects(pk__in=setting_ids).order_by('alias')
        options_data = options.get('data', {})
        ip_list = IPList(options_data.get('ip_list'))
        task_result = self.context.task_result

        for ip_addr in ip_list:
            discover_one_ip(self.context, task_result, str(ip_addr), cli_credentials)
