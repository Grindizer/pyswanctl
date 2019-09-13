import sys

from cliff.app import App
from cliff.commandmanager import CommandManager
from pyswanctl.core.controller import PySwanCtl
from os.path import exists


class PySwanCLI(App):
    def __init__(self):
        super(PySwanCLI, self).__init__(
            description='Manage StrongSwan and IPSec configuration.',
            version='0.3',
            command_manager=CommandManager('pyswanctl.cli.commands'),
            deferred_help=True
        )

    def build_option_parser(self, description, version, argparse_kwargs=None):
        parser = super(PySwanCLI, self).build_option_parser(description, version, argparse_kwargs)
        parser.add_argument('--socket', default='/opt/swan/proc/charon.vici')
        return parser

    def initialize_app(self, argv):
        self.LOG.debug('Initialize Vici connection.')
        self.ctl = PySwanCtl(self.options.socket)

    def prepare_to_run_command(self, cmd):
        self.LOG.debug('prepare_to_run_command %s', cmd.__class__.__name__)

    def clean_up(self, cmd, result, err):
        self.LOG.debug('clean_up %s', cmd.__class__.__name__)
        if err:
            self.LOG.debug('got an error: %s', err)


def main():
    pyswancli = PySwanCLI()
    return pyswancli.run(sys.argv[1:])


if __name__ == '__main__':
    sys.exit(main())
