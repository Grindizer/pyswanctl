

def debugging(events, name, log):
    import epdb; epdb.set_trace()
    log.info(name)
    return True
