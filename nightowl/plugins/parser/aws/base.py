from nightowl.plugins.parser.base import PropertyParser

class AWSPropertyParserBase(PropertyParser):

    def __init__(self, context, driver, network_object, resource):
        super().__init__(context, driver, network_object)
        self.resource = resource
