from abc import abstractmethod

from mongoengine.errors import DoesNotExist

from nightowl.plugins import NightOwlPlugin


class DriverBase(NightOwlPlugin):
    data_model = None
    parsers = []

    def __init__(self, context, noid):
        super().__init__(context)
        self.noid = noid
        self._network_object = None
        if not self.data_model:
            raise ValueError("'data_model' must be set")

    @abstractmethod
    def discover(self):
        pass

    @property
    def network_object(self):
        if self._network_object:
            return self._network_object
        try:
            # pylint: disable=no-member
            self._network_object = self.data_model.objects.get(pk=self.noid)
        except DoesNotExist:
            # pylint: disable=not-callable
            self._network_object = self.data_model(_id=self.noid)
        return self._network_object

    def benchmark(self):
        network_object = self.network_object
        if not network_object:
            return
        self.execute_parsers()

    def execute_parsers(self):
        for parser_module in self.parsers:
            parser = parser_module.ParserPlugin
            parser_result = parser(
                self.context, self, self.network_object).execute()
            if not parser_result:
                continue
            if isinstance(parser_result, list):
                for result in parser_result:
                    result.save()
            else:
                parser_result.save()
