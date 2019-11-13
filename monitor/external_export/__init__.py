import datetime
epoch = datetime.datetime.utcfromtimestamp(0)


def time_ms_after_epoch(time_requested):
    return int((time_requested - epoch).total_seconds()*1000)
