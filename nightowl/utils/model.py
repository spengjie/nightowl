import importlib
import pathlib
import re
from datetime import timedelta
from functools import partial
from inspect import ismethod
from uuid import NAMESPACE_DNS, uuid5

from nightowl.utils.datetime import str_to_datetime


class NotFound:

    def __bool__(self):
        return False


NOT_FOUND = NotFound()


class classproperty:

    def __init__(self, fget):
        self.fget = fget

    def __get__(self, owner_self, owner_cls):
        return self.fget(owner_cls)


def as_model(obj):
    if isinstance(obj, partial):
        raise ValueError('Cannot create a reference to a partial()')

    name = obj.__qualname__
    if '<lambda>' in name:
        raise ValueError('Cannot create a reference to a lambda')
    if '<locals>' in name:
        raise ValueError('Cannot create a reference to a nested function')

    if ismethod(obj):
        if hasattr(obj, 'im_self') and obj.im_self:
            # bound method
            module = obj.im_self.__module__
        elif hasattr(obj, 'im_class') and obj.im_class:
            # unbound method
            module = obj.im_class.__module__
        else:
            module = obj.__module__
    else:
        module = obj.__module__
    return '%s:%s' % (module, name)


def import_model(module_name, model_name=None):
    module_defs = module_name.split(':', 1)
    module_name = module_defs[0]
    if len(module_defs) > 1 and model_name is None:
        model_name = module_defs[1]
    if model_name is None:
        raise LookupError('Invalid reference')
    try:
        model = __import__(module_name, fromlist=[model_name])
    except ImportError as ex:
        raise LookupError(
            f'Error resolving reference {module_name}:{model_name}: '
            'could not import module') from ex
    try:
        for name in model_name.split('.'):
            model = getattr(model, name)
        return model
    except Exception as ex:
        raise LookupError(
            f'Error resolving reference {module_name}:{model_name}: '
            'error looking up object') from ex


def import_submodules(file, all_modules, package):
    module_path = pathlib.Path(file).parent
    for module_file in module_path.iterdir():
        if module_file.is_dir():
            module_name = module_file.name
            if module_name in ('__pycache__'):
                continue
        elif module_file.is_file():
            if module_file.suffix != '.py':
                continue
            module_name = module_file.name[:-3]
            if module_name in ('__init__', 'base'):
                continue
        else:
            continue
        importlib.import_module(f'.{module_name}', package=package)
        all_modules.append(module_name)


def to_bool(value):
    if value == 'true':
        return True
    elif value == 'false':
        return False
    raise ValueError()


def to_bytes(obj):
    if isinstance(obj, bytes):
        return obj

    if isinstance(obj, str):
        return obj.encode()

    if isinstance(obj, re.Pattern):
        if isinstance(obj.pattern, str):
            return re.compile(obj.encode(), obj.flags)
        return obj

    return str(obj).encode()


def to_uuid(input):
    return uuid5(NAMESPACE_DNS, input)


def to_lower(input):
    return input.lower() if isinstance(input, str) else input


def find_item(iterable, find, default=None):
    for item in iterable:
        if find(item):
            return item
    return default


def get_query_pipeline(key, q, id_key=None, unwind_key=None, extra_query=None):
    if id_key and key == id_key:
        key = '_id'
    if unwind_key is None:
        unwind_key = key
    if extra_query is None:
        extra_query = {}
    pipeline = [
        {
            '$unwind': f'${unwind_key}'
        }
    ]
    match = {}
    if q:
        q = re.escape(q)
        match[key] = {
            '$regex': q,
            '$options': 'i',
        }
    if extra_query:
        match.update(extra_query)
    if match:
        pipeline.append({'$match': match})
    pipeline.extend([
        {
            '$group': {
                '_id': f'${key}'
            }
        },
        {
            '$sort': {
                '_id': 1,
            }
        }
    ])
    return pipeline


def translate_query(query):
    query_type = query.get('type', 'str')
    value = query.get('value')
    operator = query.get('operator')
    if value is None:
        query_value = value
    elif operator == '<empty>':
        query_value = {'$in': ['', None, []]}
    elif operator == '<non-empty>':
        query_value = {'$nin': ['', None, []]}
    elif query_type == 'str':
        if not operator or operator == ':':
            query_value = {'$regex': re.escape(value), '$options': 'i'}
        elif operator == '=':
            query_value = value
        else:
            raise ValueError(f"invalid operator '{operator}' for '{query_type}'")
    elif query_type == 'bool':
        if not operator or operator == '=':
            query_value = value
        else:
            raise ValueError(f"invalid operator '{operator}' for '{query_type}'")
    elif query_type in ('int', 'float'):
        if not operator or operator == '=':
            query_value = value
        elif operator == '!=':
            query_value = {'$ne': value}
        elif operator == '>':
            query_value = {'$gt': value}
        elif operator == '>=':
            query_value = {'$ge': value}
        elif operator == '<':
            query_value = {'$lt': value}
        elif operator == '<=':
            query_value = {'$le': value}
        else:
            raise ValueError(f"invalid operator '{operator}' for '{query_type}'")
    elif query_type in ('date', 'datetime'):
        if not operator or operator == ':':
            start, end = value
            start_date, end_date = str_to_datetime(start), str_to_datetime(end)
            query_value = {'$gte': start_date, '$lt': end_date}
        elif operator == '=':
            date = str_to_datetime(value)
            delta = timedelta(days=1) if query_type == 'date' else timedelta(seconds=1)
            query_value = {'$gte': date, '$lt': date + delta}
        elif operator == '>':
            date = str_to_datetime(value)
            query_value = {'$gt': date}
        elif operator == '<':
            date = str_to_datetime(value)
            query_value = {'$lt': date}
        else:
            raise ValueError(f"invalid operator '{operator}' for '{query_type}'")
    else:
        query_value = value

    return {query['key']: query_value}


def translate_keyword_query(query, keyword_filter_keys):
    if query['key']:
        raise ValueError('filter key must be empty')
    if not keyword_filter_keys:
        raise ValueError("'keyword_filter_keys' must not be empty")
    query_list = []
    for keyword_key in keyword_filter_keys:
        search_filter = dict(query, key=keyword_key)
        query_list.append(translate_query(search_filter))
    return {'$or': query_list}


def get_search_query(filters=None, keyword_filter_keys=None, id_key=None):
    if filters is None:
        filters = []
    if keyword_filter_keys is None:
        keyword_filter_keys = []
    query_list = []
    handled_keys = {}
    index = 0
    for search_filter in filters:
        if id_key:
            if search_filter['key'] == id_key:
                search_filter['key'] = '_id'
            keyword_filter_keys = ['_id' if i == id_key else i for i in keyword_filter_keys]

        first_index = handled_keys.get(search_filter['key'])
        if first_index is None:
            handled_keys[search_filter['key']] = index
            index += 1
            if not search_filter['key']:
                translated = translate_keyword_query(search_filter, keyword_filter_keys)
            else:
                translated = translate_query(search_filter)
            query_list.append(translated)
        else:
            if not search_filter['key']:
                translated = translate_keyword_query(search_filter, keyword_filter_keys)
            else:
                translated = translate_query(search_filter)
            if '$or' not in query_list[first_index]:
                query_list[first_index] = {'$or': [query_list[first_index]]}
            query_list[first_index]['$or'].append(translated)

    db_query = {'$and': query_list} if query_list else {}
    return db_query
