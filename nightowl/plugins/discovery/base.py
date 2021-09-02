import re
from abc import abstractmethod, ABC
from fnmatch import fnmatch

from netaddr import IPNetwork, IPRange

from nightowl.plugins import NightOwlPlugin
from nightowl.utils.ip import IPList


class DriverSelectionRuleBase(ABC):

    def __init__(self, driver, *, condition=None, default=None):
        self.driver = driver
        self.condition = condition
        self.default = default

    def match(self, value, **kwargs):
        if self.match_rule(value, **kwargs):
            return self.driver
        return self.default

    @classmethod
    def load_from_dict(cls, rule_data):
        rule_type = rule_data.get('type')
        if not rule_type:
            raise ValueError('Invalid rule type')
        rule_cls = __import__(rule_type, fromlist=[''])  # To do
        return rule_cls

    @abstractmethod
    def match_rule(self, value, **kwargs):
        pass


class DriverSelector:

    def __init__(self, *rules, default=None, autodetect=None):
        self.rules = rules
        self.default = default
        self.autodetect = autodetect

    def match(self, value, **kwargs):
        for rule in self.rules:
            matched_driver = rule.match(value, **kwargs)
            if matched_driver:
                return matched_driver
        if self.autodetect:
            matched_driver = self.autodetect(value, **kwargs)
            if matched_driver:
                return matched_driver
        return self.default


class WildcardDriverSelectionRule(DriverSelectionRuleBase):

    def match_rule(self, value, **kwargs):
        return fnmatch(value, self.condition)


class RegexDriverSelectionRule(DriverSelectionRuleBase):

    def match_rule(self, value, **kwargs):
        return bool(re.match(self.condition, value, re.I))


class IPDriverSelectionRule(DriverSelectionRuleBase):

    def match_rule(self, value, **kwargs):
        if '-' in self.condition:
            if value in IPRange(*self.condition.split('-')):
                return True
        elif '/' in self.condition:
            if value in IPNetwork(self.condition):
                return True
        else:
            if value == self.condition:
                return True
        return False


class DiscoveryBase(NightOwlPlugin):
    ui_profile = {
        'data': {},
        'validation': {},
    }
    _var_mapping = {
        'str': str,
        'int': int,
        'float': float,
        'list': list,
        'dict': dict,
    }
    _cus_var_mapping = {
        'ip_list': IPList,
    }

    @abstractmethod
    def run(self):
        pass

    @classmethod
    def validate(cls, discovery_method):
        for data_key, data_def in cls.ui_profile['data'].items():
            if isinstance(data_def, str):
                data_type = data_def
                required = False
            elif isinstance(data_def, dict):
                data_type = data_def.get('type', 'str')
                required = data_def.get('required', False)
            else:
                raise ValueError(f'Invalid data definition: {data_key}')

            data_value = discovery_method.data.get(data_key)
            if required and (data_value is None or data_value == ''):
                raise ValueError(f'Value is required: {data_key}')

            var_type = cls._cus_var_mapping.get(data_type)
            if var_type:
                try:
                    var_type(data_value)
                except Exception:
                    raise ValueError(f'Invalid data value: {data_key}')
            else:
                var_type = cls._var_mapping.get(data_type)
                if data_type is None:
                    raise ValueError(f'Invalid data type: {data_key}')
                if not isinstance(data_value, var_type):
                    raise ValueError(f'Invalid data type: {data_key}')

            validation_rules = cls.ui_profile['validation'].get(data_key)
            if not validation_rules:
                continue

    @classmethod
    def build_data(cls):
        data = {}
        for data_key, data_def in cls.ui_profile['data'].items():
            if isinstance(data_def, str):
                data_type = data_def
            elif isinstance(data_def, dict):
                data_type = data_def.get('type', 'str')
            else:
                raise ValueError(f'Invalid data definition: {data_key}')

            if data_type == 'list':
                data[data_key] = []
            elif data_type == 'dict':
                data[data_key] = {}
            else:
                data[data_key] = None
        return data
