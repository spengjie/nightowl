from datetime import date, datetime
from inspect import isclass

from flask import Blueprint as _Blueprint, Flask as _Flask, json as _json
from furl import furl as _furl


class JSONEncoder(_json.JSONEncoder):

    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()
        if isinstance(o, date):
            return o.isoformat()
        return _json.JSONEncoder.default(self, o)


class Flask(_Flask):
    json_encoder = JSONEncoder


class Blueprint(_Blueprint):

    def route(self, rule, **options):
        """Like :meth:`Flask.route` but for a blueprint.  The endpoint for the
        :func:`url_for` function is prefixed with the name of the blueprint.
        """

        def decorator(f):
            if isclass(f):
                endpoint = f.__name__
                view_func = f.as_view(endpoint)
                options.pop('methods', None)
                for method in f.methods or []:
                    self.add_url_rule(rule, endpoint, view_func, methods=(method, ), **options)
            else:
                endpoint = options.pop('endpoint', f.__name__)
                self.add_url_rule(rule, endpoint, f, **options)
            return f

        return decorator


class furl(_furl):

    def add_args(self, args):
        if '/#/' in self.url:
            self.add(fragment_args=args)
        else:
            self.add(args=args)
