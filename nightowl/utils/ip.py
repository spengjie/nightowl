from netaddr import IPAddress, IPNetwork, IPRange


class IPList:

    def __init__(self, ip_list_str):
        if not isinstance(ip_list_str, str):
            raise TypeError('invalid ip_list type')
        self.original = ip_list_str
        self.ip_list = []
        try:
            for ip_str in ip_list_str.split(';'):
                if '-' in ip_str:
                    ip_range = IPRange(*ip_str.split('-'))
                    self.ip_list.append(ip_range)
                elif '/' in ip_str:
                    ip_network = IPNetwork(ip_str)
                    self.ip_list.append(ip_network)
                else:
                    ip_address = IPAddress(ip_str)
                    self.ip_list.append(ip_address)
        except Exception:
            raise ValueError(f'Invalid IP list: {ip_list_str}')

    def __len__(self):
        length = 0
        for ip_item in self.ip_list:
            if isinstance(ip_item, (IPRange, IPNetwork)):
                length += len(ip_item)
            else:
                length += 1
        return length

    def __iter__(self):
        for ip_item in self.ip_list:
            if isinstance(ip_item, (IPRange, IPNetwork)):
                for ip_addr in ip_item:
                    yield ip_addr
            else:
                yield ip_item
