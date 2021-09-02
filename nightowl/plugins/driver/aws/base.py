from abc import abstractmethod

from mongoengine.errors import DoesNotExist

from nightowl.models import nom
from nightowl.plugins.connection import aws as aws_connection
from nightowl.plugins.driver.base import DriverBase
from nightowl.utils.datetime import utc_now


class AWSServiceDriverBase(DriverBase):
    service_name = None
    property_parser = None

    def discover(self, resource):
        # pylint: disable=not-callable
        return [
            self.property_parser.ParserPlugin(
                self.context, self, self.network_object, resource).execute()]

    @classmethod
    def discover_resources(cls, context, aws_access_key):
        connection = aws_connection.ConnectionPlugin(
            context,
            cls.service_name,
            region_name=aws_access_key.region_name,
            aws_access_key_id=aws_access_key.access_key,
            aws_secret_access_key=aws_access_key.secret_key)
        resources = cls.get_resources(connection)
        for resource in resources:
            resource_id = resource.id
            try:
                # pylint: disable=no-member
                settings = nom.NetworkObjectSettings.objects.get(pk=resource_id)
                settings.update(set__credentials__aws_access_key={'ref': aws_access_key._id})
            except DoesNotExist:
                settings = nom.NetworkObjectSettings(_id=resource_id)
                settings.credentials = {'aws_access_key': {'ref': aws_access_key._id}}
                settings.save()
            driver_ins = cls(context, resource_id)
            discovered = driver_ins.discover(resource=resource)
            for no in discovered:
                no.last_discovered_at = utc_now()
                no.save()

    @classmethod
    @abstractmethod
    def get_resources(cls, connection):
        pass
