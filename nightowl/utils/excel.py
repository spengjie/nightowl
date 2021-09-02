from tablib import Dataset


def export_xlsx(*rows, headers=None, title=None):
    return Dataset(*rows, headers=headers, title=title).export('xlsx')


def import_xlsx(stream):
    # If mode is 'r' or 'a', the file should be seekable for ZipFile.
    # But tempfile.SpooledTemporaryFile while is used by Flask has no seekable attribute.
    # So set seekable manually.
    # https://docs.python.org/3/library/zipfile.html#zipfile.ZipFile
    # This issue will be fixed once https://github.com/python/cpython/pull/3249 get merged
    if not hasattr(stream, 'seekable') and hasattr(stream, 'seek'):
        stream.seekable = lambda: True
    return Dataset().load(stream)
