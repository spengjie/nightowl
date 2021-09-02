import re

from nightowl.models.nom import DataTableColumnCompareType, DataTableHeader
from nightowl.plugins.parser.base import TableParser


''' Sample 1
ip-10-10-1-12#show ip route
Codes: L - local, C - connected, S - static, R - RIP, M - mobile, B - BGP
       D - EIGRP, EX - EIGRP external, O - OSPF, IA - OSPF inter area
       N1 - OSPF NSSA external type 1, N2 - OSPF NSSA external type 2
       E1 - OSPF external type 1, E2 - OSPF external type 2, m - OMP
       n - NAT, Ni - NAT inside, No - NAT outside, Nd - NAT DIA
       i - IS-IS, su - IS-IS summary, L1 - IS-IS level-1, L2 - IS-IS level-2
       ia - IS-IS inter area, * - candidate default, U - per-user static route
       H - NHRP, G - NHRP registered, g - NHRP registration summary
       o - ODR, P - periodic downloaded static route, l - LISP
       a - application route
       + - replicated route, % - next hop override, p - overrides from PfR

Gateway of last resort is 10.10.1.1 to network 0.0.0.0

S*    0.0.0.0/0 [1/0] via 10.10.1.1, GigabitEthernet1
      10.0.0.0/8 is variably subnetted, 2 subnets, 2 masks
C        10.10.1.0/24 is directly connected, GigabitEthernet1
L        10.10.1.12/32 is directly connected, GigabitEthernet1
'''


class ParserPlugin(TableParser):
    name = 'Route Table'

    def _parse(self, outputs):
        routes_block_search = re.search(
            r'Gateway of last resort is .+?[\r\n]+(\S+.+)', outputs, re.S)
        if not routes_block_search:
            return []
        routes_block = routes_block_search.group(1)
        routes = re.findall(
            r'^(\S+)\s+(\S+) .+?(?:via (\S+))?, (\S+)', routes_block, re.S | re.M)
        return routes

    def execute(self):
        outputs = self.driver.cli.execute_command('show ip route')
        if not outputs:
            return None
        headers = [
            DataTableHeader(
                name='code',
                display_name='Code',
            ),
            DataTableHeader(
                name='destination',
                display_name='Destination',
                compare_type=DataTableColumnCompareType.KEY,
            ),
            DataTableHeader(
                name='next_hop_ip',
                display_name='Next Hop IP',
            ),
            DataTableHeader(
                name='interface',
                display_name='Interface',
            ),
        ]

        self.table.headers = headers
        self.table.rows = self._parse(outputs)
        return self.table
