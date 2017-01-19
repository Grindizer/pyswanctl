from cliff.lister import Lister
from cliff.show import ShowOne
from cliff.command import Command
import inspect
from . import utils


class SwanCtlBase(object):
    swancmd = ''
    keys = []
    formats = {}

    def get_parser(self, prog_name):
        parser = super(SwanCtlBase, self).get_parser(prog_name)
        for key in self.keys:
            parser.add_argument('--{0}'.format(key), **utils.args_def[key])

        parser.add_argument('--output', '-o', required=False, default='default',
                            help='name of the filter to apply on the results.')
        return parser

    def _clean_args(self, parsed_args):
        parsed_args = vars(parsed_args)
        args = {}
        for key in self.keys:
            safe_key = key.replace('-', '_')
            arg = parsed_args.get(safe_key, None)
            if arg is not None:
                args[key] = arg
        return args

    def take_action(self, parsed_args):
        args = self._clean_args(parsed_args)
        # add a try catch for generic errors here.
        response = self.app.ctl.iter_call(self.swancmd, **args)
        if isinstance(response, (list, tuple)):
            default_formatter = utils.raw
        else:
            default_formatter = utils.extended

        formatter = self.formats.get(parsed_args.output, default_formatter)
        response = formatter(response)
        return response


class ListSas(SwanCtlBase, Lister):
    """List currently active security association (the tunnels!)"""

    swancmd = 'list_sas'
    keys = ['noblock', 'ike', 'ike-id']
    formats = {
        'default': utils.list_sa_default
    }


class ListConnections(SwanCtlBase, Lister):
    """ List loaded connections """

    swancmd = 'list_conns'
    keys = ['ike']
    formats = {
        'default': utils.list_ctx_default
    }


class GetStats(SwanCtlBase, ShowOne):
    """ Get daemon statictics """

    swancmd = 'stats'
    formats = {
        'default': utils.get_stats_default
    }


class GetVersion(SwanCtlBase, ShowOne):
    """ Get daemon statictics """

    swancmd = 'version'


class WatchExec(Command):
    """ Run a specific callback when an event is triggered """

    swancmd = 'listen'

    def get_parser(self, prog_name):
        parser = super(Command, self).get_parser(prog_name)
        parser.add_argument('--watch', '-w',
                            chices=['ike-updown', 'ike-rekey', 'child-updown', 'child-rekey'],
                            required=True, dest='event_name',
                            help='Name of the event to register to')

        parser.add_argument('--exec', '--cb', '-e', nargs='+', type=list, dest='handlers',
                            help='name of the callback to run when the event is triggered. '
                                 '(name of a python entry point under "pyswanctl.event_handler")')
        return parser

    def take_action(self, parsed_args):
        # add a try catch for generic errors here.
        response = self.app.ctl.watch(parsed_args.event_name, parsed_args.handlers)
        return response.ident


__all__ = [
    'ListSas',
    'ListConnections',
    'GetStats',
    'GetVersion',
    'WatchExec',
]
