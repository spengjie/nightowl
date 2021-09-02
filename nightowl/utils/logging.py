from datetime import datetime, timezone
from logging import FileHandler, Formatter, StreamHandler
from pathlib import Path


class DatetimeFormatter(Formatter):

    def converter(self, timestamp):
        return datetime.fromtimestamp(timestamp, timezone.utc)

    def formatTime(self, record, datefmt=None):
        dt = self.converter(record.created)
        if datefmt:
            s = dt.strftime(datefmt)
        else:
            s = dt.isoformat()
        return s


def setup_logger(logger, level, file, format, formatter=None, clear_handlers=True):
    if clear_handlers:
        logger.handlers = []
    formatter = formatter or DatetimeFormatter
    log_formatter = formatter(format)
    Path(file).parent.mkdir(parents=True, exist_ok=True)
    file_handler = FileHandler(file, mode='a+', encoding='utf-8')
    std_handler = StreamHandler()
    file_handler.setFormatter(log_formatter)
    std_handler.setFormatter(log_formatter)
    logger.setLevel(level)
    logger.addHandler(file_handler)
    logger.addHandler(std_handler)
