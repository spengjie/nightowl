import datetime

from mongoengine import fields
from mongoengine.errors import ValidationError

from nightowl.utils.datetime import add_tzinfo, str_to_datetime


class DateTimeField(fields.DateTimeField):

    def to_mongo(self, value):
        if isinstance(value, datetime.datetime):
            return add_tzinfo(value)
        elif isinstance(value, datetime.date):
            return add_tzinfo(datetime.datetime(
                value.year, value.month, value.day, tzinfo=value.tzinfo))
        elif isinstance(value, str):
            try:
                return add_tzinfo(str_to_datetime(value))
            except Exception as ex:
                raise ValidationError(
                    '%r cannot be converted to a datetime object.' % value
                ) from ex
        elif isinstance(value, (int, float)):
            try:
                return add_tzinfo(datetime.datetime.utcfromtimestamp(value))
            except TypeError as ex:
                raise ValidationError(
                    '%r cannot be converted to a datetime object.' % value
                ) from ex
        raise ValidationError('%r cannot be converted to a datetime object.' % value)

    def to_python(self, value):
        try:
            return self.to_mongo(value)
        except ValidationError:
            return value
