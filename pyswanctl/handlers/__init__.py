import json
import os


def debugging(events, event_type, log):
    up = events.get('up', False)
    idents = [child for child in events.keys() if child != 'up']
    updown = 'up' if up else 'down'
    for ident in idents:
        state = events[ident]['state']
        log.info(" ".join([ident, updown, state]))
    return True


def log(events, event_type, log):
    events['type'] = event_type
    # event is an ordereddict. ?
    return events


def awslog(events, event_type, log):
    logs = []
    action = 'up' if events.get('up', False) else 'down'
    for c_name, c_pts in events.items():
        if c_name == 'up':
            continue
        for sa_name, sa_pts in c_pts['child-sas'].items():
            account, region, vpc, tunnel = sa_name.split('_')
            ev = dict(type=event_type, action=action, account=account, region=region, vpc_id=vpc, ctx=tunnel, local=c_pts['local-host'], remote=c_pts['remote-host'])
            ev.update(sa_pts)
            logs.append(ev)

    return logs
