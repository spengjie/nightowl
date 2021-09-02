from abc import ABCMeta
from copy import deepcopy

from nightowl.models import task as task_model
from nightowl.utils.model import classproperty


class PluginMeta(ABCMeta):
    _plugins = {}

    def __new__(cls, name, bases, namespace, **kwargs):
        plugin_cls = super().__new__(cls, name, bases, namespace, **kwargs)
        for base in bases:
            for m in base.__mro__:
                if m is object:
                    continue
                cls._plugins.setdefault(m.__name__, []).append(plugin_cls)
        return plugin_cls


class NightOwlPlugin(metaclass=PluginMeta):

    def __init__(self, context, **kwargs):
        self.context = task_model.Context(deepcopy(context))
        self.kwargs = kwargs

    @classproperty
    def plugins(cls):  # pylint: disable=no-self-argument
        return cls._plugins[cls.__name__]  # pylint: disable=no-member

    @classproperty
    def plugin_name(cls):  # pylint: disable=no-self-argument
        return getattr(cls, 'name', cls.__name__)  # pylint: disable=no-member

    @classproperty
    def plugin_path(cls):  # pylint: disable=no-self-argument
        return cls.__module__
