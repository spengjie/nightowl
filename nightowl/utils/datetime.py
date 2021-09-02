from datetime import date, datetime, timedelta, timezone


# Helpers for parsing the result of isoformat()
def _parse_isoformat_date(dtstr):
    # It is assumed that this function will only be called with a
    # string of length exactly 10, and (though this is not used) ASCII-only
    year = int(dtstr[0:4])
    if dtstr[4] != '-':
        raise ValueError('Invalid date separator: %s' % dtstr[4])

    month = int(dtstr[5:7])

    if dtstr[7] != '-':
        raise ValueError('Invalid date separator')

    day = int(dtstr[8:10])

    return [year, month, day]


def _parse_hh_mm_ss_ff(tstr):
    # Parses things of the form HH[:MM[:SS[.fff[fff]]]]
    len_str = len(tstr)

    time_comps = [0, 0, 0, 0]
    pos = 0
    for comp in range(0, 3):
        if (len_str - pos) < 2:
            raise ValueError('Incomplete time component')

        time_comps[comp] = int(tstr[pos:pos+2])

        pos += 2
        next_char = tstr[pos:pos+1]

        if not next_char or comp >= 2:
            break

        if next_char != ':':
            raise ValueError('Invalid time separator: %c' % next_char)

        pos += 1

    if pos < len_str:
        if tstr[pos] != '.':
            raise ValueError('Invalid microsecond component')
        else:
            pos += 1

            len_remainder = len_str - pos
            if len_remainder not in (3, 6):
                raise ValueError('Invalid microsecond component')

            time_comps[3] = int(tstr[pos:])
            if len_remainder == 3:
                time_comps[3] *= 1000

    return time_comps


def _parse_isoformat_time(tstr):
    # Format supported is HH[:MM[:SS[.fff[fff]]]][+HH:MM[:SS[.ffffff]]]
    len_str = len(tstr)
    if len_str < 2:
        raise ValueError('Isoformat time too short')

    # Replace 'Z' in timezone with '+00:00'
    if tstr[-1] in ('z', 'Z'):
        tstr = tstr[:-1] + '+00:00'

    # This is equivalent to re.search('[+-]', tstr), but faster
    tz_pos = (tstr.find('-') + 1 or tstr.find('+') + 1)
    timestr = tstr[:tz_pos-1] if tz_pos > 0 else tstr

    time_comps = _parse_hh_mm_ss_ff(timestr)

    tzi = None
    if tz_pos > 0:
        tzstr = tstr[tz_pos:]

        # Valid time zone strings are:
        # HH:MM               len: 5
        # HH:MM:SS            len: 8
        # HH:MM:SS.ffffff     len: 15

        if len(tzstr) not in (5, 8, 15):
            raise ValueError('Malformed time zone string')

        tz_comps = _parse_hh_mm_ss_ff(tzstr)
        if all(x == 0 for x in tz_comps):
            tzi = timezone.utc
        else:
            tzsign = -1 if tstr[tz_pos - 1] == '-' else 1

            td = timedelta(hours=tz_comps[0], minutes=tz_comps[1],
                           seconds=tz_comps[2], microseconds=tz_comps[3])

            tzi = timezone(tzsign * td)

    time_comps.append(tzi)

    return time_comps


def str_to_datetime(date_string):
    """Construct a datetime from the output of datetime.isoformat()."""
    if isinstance(date_string, (datetime, date)):
        return date_string
    if not isinstance(date_string, str):
        raise TypeError('date_string: argument must be str')

    if 'GMT' in date_string:
        try:
            return add_tzinfo(datetime.strptime(date_string, '%a, %d %b %Y %H:%M:%S GMT'))
        except ValueError as ex:
            raise ValueError(f'Invalid GMT format string: {date_string!r}') from ex

    # Split this at the separator
    dstr = date_string[0:10]
    tstr = date_string[11:]

    try:
        date_components = _parse_isoformat_date(dstr)
    except ValueError as ex:
        raise ValueError(f'Invalid isoformat string: {date_string!r}') from ex

    if tstr:
        try:
            time_components = _parse_isoformat_time(tstr)
        except ValueError as ex:
            raise ValueError(f'Invalid isoformat string: {date_string!r}') from ex
    else:
        time_components = [0, 0, 0, 0, None]

    return datetime(*(date_components + time_components))


def datetime_to_str(dt, format=None):
    if not isinstance(dt, datetime):
        raise TypeError('dt: argument must be datetime')
    if format is None:
        return dt.isoformat()
    return dt.strftime(format)


def utc_now():
    return datetime.now(timezone.utc)


def to_timestamp(dt, ms=True):
    if not isinstance(dt, datetime):
        raise TypeError(f"'{dt}' is not an instance of 'datetime'")
    dt = add_tzinfo(dt)
    timestamp = dt.timestamp()
    if ms:
        timestamp = int(timestamp * 1000)
    return timestamp


def add_tzinfo(no_tz_dt, tzoffset=0):
    if not isinstance(no_tz_dt, datetime):
        raise TypeError(f"'{no_tz_dt}' is not an instance of 'datetime'")
    if no_tz_dt.tzinfo:
        return no_tz_dt
    if no_tz_dt == datetime(1970, 1, 1):
        no_tz_dt.replace(tzinfo=timezone.utc)
    return no_tz_dt.replace(tzinfo=timezone(timedelta(hours=tzoffset)))


def astimezone(dt, tzoffset):
    if not isinstance(dt, datetime):
        raise TypeError(f"'{dt}' is not an instance of 'datetime'")
    return dt.astimezone(timezone(timedelta(hours=tzoffset)))
