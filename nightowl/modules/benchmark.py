from nightowl.models.nom import NetworkNode
from nightowl.utils.model import import_model


def main(context):
    context = {}
    for network_object in NetworkNode.objects.all():  # pylint: disable=no-member
        driver_module = import_model(network_object.driver, 'DriverPlugin')
        driver = driver_module(
            context,
            noid=network_object._id)
        driver.benchmark()
