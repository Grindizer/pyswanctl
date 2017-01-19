args_def = {
    'noblock': dict(action='store_true',
                    help='Do not wait for the result to be returned.'
                         'Useful when in asynchronous mode.'),
    'ike': dict(type=str, required=False,
                help='List only SA of the specified ike (by name)'),
    'ike-id': dict(type=str, required=False,
                   help='List only SA of the specified ike (by ID)')
}


def raw(results):
    headers = ['_raw']
    yield headers

    def _iter_results():
        for entry in results:
            yield [entry]

    yield _iter_results()


def extended(results):
    return results.keys(), results.values()


def list_sa_default(results):
    headers = ['SA', 'State', 'Network', 'In (b/p)',
               'Out (b/p)', 'Id (u/req)', 'Link State', 'Local', 'Remote']
    yield headers

    def _iter_result():
        for entry in results:
            for c_name, c_pts in entry.items():
                for sa_name, sa_pts in c_pts['child-sas'].items():
                    yield [
                        sa_name,
                        sa_pts['state'],
                        ','.join(sa_pts['remote-ts']),
                        '{0}/{1}'.format(sa_pts['bytes-in'], sa_pts['packets-in']),
                        '{0}/{1}'.format(sa_pts['bytes-out'], sa_pts['packets-out']),
                        '{0}/{1}'.format(sa_pts['uniqueid'], sa_pts['reqid']),
                        c_pts['state'],
                        c_pts['local-host'],
                        c_pts['remote-host'],
                    ]

    yield _iter_result()


def list_ctx_default(results):
    headers = ['Child', 'Local Networks', 'Remote Networks', 'Mode',
               'Connection', 'Local', 'Remote']
    yield headers

    def _iter_results():
        for entry in results:
            for c_name, c_pts in entry.items():
                for child_name, child_pts in c_pts['children'].items():
                    yield [
                        child_name,
                        ','.join(child_pts['local-ts']),
                        ','.join(child_pts['remote-ts']),
                        child_pts['mode'],
                        c_name,
                        ','.join(child_pts['local_addrs']),
                        ','.join(child_pts['remote_addrs']),
                    ]

    yield _iter_results()


def get_stats_default(results):
    headers = ['Started At', 'Running For', 'Used Memory', 'Free Memory', 'Active Tunnels',
               'Half Open Tunnels', 'Awaiting Critical Jobs', 'Awaiting Priority Jobs',
               'Workers', 'Available Workers']
    yield headers
    yield [
        results['uptime']['since'],
        results['uptime']['running'],
        results['mallinfo']['used'],
        results['mallinfo']['free'],
        results['ikesas']['total'],
        results['ikesas']['half-open'],
        results['queues']['critical'],
        results['queues']['high'],
        results['workers']['total'],
        results['workers']['idle']
    ]
