from abc import abstractmethod

from mongoengine.errors import DoesNotExist

from nightowl.models.nom import NetworkNode
from nightowl.plugins import NightOwlPlugin


class AdapterBase(NightOwlPlugin):

    def __init__(self, context, noid):
        super().__init__(context)
        self.noid = noid
        self._network_object = None

    @property
    def network_object(self):
        if self._network_object:
            return self._network_object
        try:
            # pylint: disable=no-member
            self._network_object = NetworkNode.objects.get(pk=self.noid)
        except DoesNotExist:
            # pylint: disable=not-callable
            self._network_object = NetworkNode(_id=self.noid)
        return self._network_object

    @abstractmethod
    def run(self):
        pass

    @abstractmethod
    def get_metrics(self):
        pass

    @abstractmethod
    def get_metric(self, metric_key):
        pass
