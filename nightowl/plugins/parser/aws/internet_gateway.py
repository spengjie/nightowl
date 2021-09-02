from nightowl.plugins.parser.aws.base import AWSPropertyParserBase
from nightowl.utils.aws import get_name


class ParserPlugin(AWSPropertyParserBase):

    def execute(self):
        network_object = self.network_object
        network_object.noid = self.resource.attachments[0]['VpcId']
        aws_tags = self.resource.tags or []
        network_object.name = get_name(aws_tags, self.resource.id)
        network_object.aws_tags = [
            {'key': tag['Key'], 'value': tag['Value']} for tag in aws_tags]
        network_object.is_boundary = True
        return network_object
