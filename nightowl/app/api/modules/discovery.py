from flask.views import MethodView

from nightowl.plugins.discovery import aws
from nightowl.plugins.explorer import network_object
from nightowl.plugins.link import l3_topology, vpc_peering
from nightowl.utils.flask import Blueprint


bp = Blueprint('discovery', __name__)


@bp.route('/_test')
class TestDiscoveryTask(MethodView):

    def get(self):
        aws.DiscoveryPlugin({}).run()
        network_object.ExplorerPlugin({}).build()
        l3_topology.LinkPlugin({}).build()
        vpc_peering.LinkPlugin({}).build()
        return ''
