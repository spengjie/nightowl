from nightowl.models.modules.explorer import ExplorerNodeType
from nightowl.models.nom.aws import AWSService
from nightowl.models.nom.network_device import NetworkDevice
from nightowl.models.nom.server import Server
from nightowl.plugins.explorer.base import ExplorerBase, ExplorerNode
from nightowl.utils.word import analyze, pluralize


class ExplorerPlugin(ExplorerBase):
    name = 'Network Object'

    def build(self):
        for object_category in [AWSService, NetworkDevice, Server]:
            category_node = ExplorerNode(
                name=pluralize(analyze(object_category.__name__)),
                node_type=ExplorerNodeType.FOLDER,
            )
            object_types = {}
            # pylint: disable=no-member
            network_objects = object_category.objects().order_by('_cls', 'name')
            for network_object in network_objects:
                if network_object.type not in object_types:
                    type_node = ExplorerNode(
                        name=analyze(network_object.__class__.__name__),
                        node_type=ExplorerNodeType.FOLDER,
                    )
                    object_types[network_object.type] = type_node
                    category_node.add_child(type_node)
                    type_node.icon = network_object.type_icon
                else:
                    type_node = object_types[network_object.type]
                if network_object.name != network_object._id:
                    node_name = f'{network_object.name} ({network_object._id})'
                else:
                    node_name = network_object.name
                no_node = ExplorerNode(
                    name=node_name,
                    node_type=ExplorerNodeType.NODE,
                    ref_type=network_object.type,
                    ref_id=network_object._id,
                )
                no_node.icon = network_object.icon
                type_node.add_child(no_node)
            self.append(category_node)
        self.save()
