from flask import current_app, jsonify, request
from flask.views import MethodView
from mongoengine.errors import DoesNotExist
from mongoengine.queryset.visitor import Q

from nightowl.auth import require_auth
from nightowl.models.nom import NetworkInterface, NetworkLink, NetworkNode
from nightowl.models.nom.network_device import NetworkDeviceConfig
from nightowl.plugins.adapter.zabbix import AdapterPlugin as ZabbixAdapter
from nightowl.plugins.adapter.cloudwatch import AdapterPlugin as CloudWatchAdapter
from nightowl.utils.datetime import str_to_datetime
from nightowl.utils.flask import Blueprint


def get_upstream(network_object):
    group_ref = network_object.group
    if group_ref:
        try:
            # pylint: disable=no-member
            group = NetworkNode.objects.get(pk=group_ref._id)
            group_infos = get_upstream(group)
            parent, parent_groups = group_infos[-1]
            return [*group_infos, (network_object, [
                {'_id': parent._id, 'type': parent.type}, *parent_groups])]
        except DoesNotExist:
            pass
    return [(network_object, [])]


def get_downstream(network_object, groups):
    groups = groups[:]
    if network_object.is_group:
        groups.insert(0, {'_id': network_object._id, 'type': network_object.type})
        group_members = NetworkNode.objects(  # pylint: disable=no-member
            __raw__={'group._id': network_object._id})
        members = []
        for group_member in group_members:
            members.append((group_member, [*groups]))
            x = get_downstream(group_member, [*groups])
            members.extend(x)
        return members
    return []


def get_map_data(network_object):

    def _iter_items(items):
        for net_obj, groups in items:
            nn_list.append({
                '_id': net_obj._id,
                'name': net_obj.name,
                'type': net_obj.type,
                'is_group': net_obj.is_group,
                'icon': net_obj.icon,
                'color': net_obj.color,
                'groups': groups,
                # pylint: disable=no-member
                'boundary_interfaces': [{
                    '_id': net_intf._id,
                    'name': net_intf.name,
                    'type': net_intf.type,
                    'icon': net_intf.icon,
                    'color': net_intf.color,
                } for net_intf in NetworkInterface.objects(
                    noid=net_obj._id, is_boundary=True)],
            })

    nn_list = []
    nl_list = []
    upstream = get_upstream(network_object)
    groups = upstream[-1][1]
    downstream = get_downstream(network_object, groups)
    _iter_items(upstream)
    _iter_items(downstream)
    nnids = [nn['_id'] for nn in nn_list]
    # pylint: disable=no-member
    network_links = NetworkLink.objects(Q(noid1__in=nnids) | Q(noid2__in=nnids))
    for network_link in network_links:
        nl_list.append({
            '_id': network_link._id,
            'name': network_link.name,
            'type': network_link.type,
            'link_type': network_link.link_type.value,
            'no1': network_link.noid1,
            'no2': network_link.noid2,
            'noi1': network_link.noiid1,
            'noi2': network_link.noiid2,
            'icon': network_link.icon,
            'color': network_link.color,
        })
    return {
        'network_nodes': nn_list,
        'network_links': nl_list,
    }


bp = Blueprint('networ_objects', __name__)


@bp.route('/network_objects/<_id>/map_data')
class NetwortObjectMapData(MethodView):

    @require_auth()
    def get(self, _id):
        try:
            # pylint: disable=no-member
            network_node = NetworkNode.objects.get(pk=_id)
        except DoesNotExist:
            current_app.logger.info(
                f'Failed to Fetch Network Object map data (_id={_id}, error=Not found)')
            return '', 404
        data = get_map_data(network_node)
        current_app.logger.info(f'Fetched Network Object map data (_id={_id})')
        return jsonify(data), 200


@bp.route('/network_objects/<_id>/properties')
class NetwortObjectProperties(MethodView):

    @require_auth()
    def get(self, _id):
        try:
            # pylint: disable=no-member
            network_node = NetworkNode.objects.get(pk=_id)
        except DoesNotExist:
            current_app.logger.info(
                f'Failed to Fetch Network Object properties (_id={_id}, error=Not found)')
            return '', 404
        data = network_node.to_mongo()
        current_app.logger.info(f'Fetched Network Object properties (_id={_id})')
        return jsonify(data), 200


@bp.route('/network_objects/<_id>/settings')
class NetwortObjectSettings(MethodView):

    @require_auth()
    def get(self, _id):
        try:
            # pylint: disable=no-member
            network_node = NetworkNode.objects.get(pk=_id)
        except DoesNotExist:
            current_app.logger.info(
                f'Failed to Fetch Network Object map data (_id={_id}, error=Not found)')
            return '', 404
        data = network_node.settings.to_dict()
        current_app.logger.info(f'Fetched Network Object map data (_id={_id})')
        return jsonify(data), 200


@bp.route('/network_objects/<_id>/configuration')
class NetwortDeviceConfiguration(MethodView):

    @require_auth()
    def get(self, _id):
        data = {
            'config': '',
        }
        try:
            # pylint: disable=no-member
            config = NetworkDeviceConfig.objects.get(noid=_id)
            data['config'] = config.config
        except DoesNotExist:
            pass
        current_app.logger.info(f'Fetched Network Device configuration (_id={_id})')
        return jsonify(data), 200


@bp.route('/network_objects/<_id>/monitoring/<plugin_id>')
class MonitoringData(MethodView):

    @require_auth()
    def post(self, _id, plugin_id):
        request_data = request.get_json() or {}
        request_args = request.args
        try:
            context = {}
            adapter = CloudWatchAdapter(context, _id)
        except DoesNotExist:
            current_app.logger.info(
                f'Failed to fetch monitoring data (_id={_id}, plugin={plugin_id}, '
                f'request_data={request_data}, error=Not found)')
            return '', 404
        metric_id = request_args.get('metric_id')
        data = []
        if not metric_id:
            for metric in adapter.get_metrics():
                data.append(adapter.run(metric, **request_data))
        else:
            metric = adapter.get_metric(metric_id)
            if metric:
                data.append(adapter.run(metric, **request_data))
        data.sort(key=lambda x: x['name'])
        current_app.logger.info(
            f'Fetched monitoring data (_id={_id}, plugin={plugin_id}, '
            f'request_data={request_data})')
        return jsonify(data), 200
