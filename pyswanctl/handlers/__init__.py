

def debugging(events, event_type, log):
    event = events.items()[0]
    import epdb; epdb.set_trace()
    child, state = event[0], event[1][0]
    log.info(event_type, child, state)
    return True
