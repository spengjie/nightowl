import uuid
from abc import abstractmethod

from mongoengine.errors import DoesNotExist

from nightowl.models.nom import DataTable
from nightowl.plugins import NightOwlPlugin


class ParserBase(NightOwlPlugin):

    def __init__(self, context, driver, network_object):
        super().__init__(context)
        self.driver = driver
        self.network_object = network_object

    @abstractmethod
    def execute(self):
        pass


class PropertyParser(ParserBase):
    pass


class TableParser(ParserBase):

    def __init__(self, context, driver, network_object):
        super().__init__(context, driver, network_object)
        noid = self.network_object._id
        try:
            # pylint: disable=no-member
            self.table = DataTable.objects.get(noid=noid, name=self.plugin_name)
        except DoesNotExist:
            table = DataTable()
            table._id = uuid.uuid4()
            table.noid = noid
            table.name = self.plugin_name
            self.table = table
