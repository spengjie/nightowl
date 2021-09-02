from abc import abstractmethod

from nightowl.models.modules.explorer import (
    Explorer as DBExplorer,
    ExplorerNode as DBExplorerNode,
    ExplorerNodeType,
)
from nightowl.plugins import NightOwlPlugin
from nightowl.utils.datetime import utc_now


class ExplorerNode:

    def __init__(self, name, node_type, ref_type=None, ref_id=None):
        self.name = name
        self.type = node_type
        self.ref_type = ref_type
        self.ref_id = ref_id
        self.icon = None
        self._parent = None
        self._children = []

    @property
    def path(self):
        path_list = [self.name]
        parent = self._parent
        while parent:
            path_list.append(parent.name)
            parent = parent.parent
        path_list.reverse()
        return '/'.join(path_list)

    @property
    def level(self):
        level = 1
        parent = self._parent
        while parent:
            level += 1
            parent = parent._parent
        return level

    @property
    def parent(self):
        return self._parent

    @property
    def children(self):
        return self._children

    def add_child(self, node):
        self._children.append(node)
        node._parent = self

    def remove_child(self, node):
        self._children.remove(node)

    @classmethod
    def load(cls, data):
        node = ExplorerNode(
            data['name'],
            ExplorerNodeType(data['type']),
            data['ref_type'],
            data['ref_id'],
        )
        node.icon = data.get('icon')
        children_data = data.get('children', [])
        for child_data in children_data:
            child = cls.load(child_data)
            node.add_child(child)
        return node

    def dump(self):
        node_data = {
            'name': self.name,
            'type': self.type.value,
            'ref_type': self.ref_type,
            'ref_id': self.ref_id,
            'icon': self.icon,
            'path': self.path,
            'level': self.level,
            'parent': self.parent.name if self.parent else None,
            'children': [child.dump() for child in self._children],
        }
        return node_data

    def __iter__(self):
        yield self
        for child in self._children:
            for item in child:
                yield item

    def __eq__(self, other):
        if isinstance(other, ExplorerNode):
            return self.name == other.name and self.type == other.type

    def __str__(self):
        return self.name

    def format(self):
        space = ' ' * self.level
        children_str = '\n' + '\n'.join(
            [child.format() for child in self._children]) if self._children else ''
        return f'{space}{self.name}{children_str}'


class ExplorerBase(NightOwlPlugin):

    def __init__(self, context):
        super().__init__(context)
        self.nodes = []


    @abstractmethod
    def build(self):
        pass

    def append(self, node, parent=None):
        if parent:
            parent.add_child(node)
        else:
            self.nodes.append(node)

    def remove(self, node):
        if node.parent:
            node.parent.remove_child(node)
        else:
            self.nodes.remove(node)

    def get(self, node_path):
        for node in self:
            if node.path == node_path:
                return node
        return None

    def search(self, node_name, node_type=None):
        for node in self:
            if node.name == node_name and \
                    (node.type == node_type or not node_type):
                return node
        return None

    def filter(self, node_name, node_type=None):
        nodes = []
        for node in self:
            if node.name == node_name and \
                    (node.type == node_type or not node_type):
                nodes.append(node)
        return nodes

    def load(self, data):
        for node_data in data:
            self.nodes.append(ExplorerNode.load(node_data))

    def dump(self):
        return [node.dump() for node in self.nodes]

    def save(self):
        dbexplorer = DBExplorer(name=self.plugin_name)
        for node in self.nodes:
            dbnode = DBExplorerNode(**node.dump())
            dbexplorer.nodes.append(dbnode)
        dbexplorer.updated_at = utc_now()
        return dbexplorer.save()

    def __iter__(self):
        for node in self.nodes:
            for item in node:
                yield item

    def __str__(self):
        return '\n'.join([node.format() for node in self.nodes])
