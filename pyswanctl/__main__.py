#!/usr/bin/env python
# -*- encoding: utf-8 -*-
import json

import click
import signal
import pprint
import sys
import vici
import socket
from pkg_resources import iter_entry_points

mapp_g = {
    'v': 'version',
    'S': 'stats',
    'L': 'get_conns',
    'A': 'get_pools',
    'r': 'reload_settings',
    'f': 'clear_creds',
}

mapp_l = {
    'i': {'c': 'initiate', 'd': '{ child = <CHILD_SA configuration name to initiate> '
                                '  ike = <optional IKE_SA configuraiton name to find child under>'
                                '  timeout = <timeout in ms before returning>'
                                '  init-limits = <whether limits may prevent initiating the CHILD_SA>'
                                '  loglevel = <loglevel to issue "control-log" events for>'
                                '}',
          },
    't': {'c': 'terminate', 'd': '{'
                                 '  child = <terminate a CHILD_SA by configuration name>'
                                 '  ike = <terminate an IKE_SA by configuration name>'
                                 '  child-id = <terminate a CHILD_SA by its reqid>'
                                 '  ike-id = <terminate an IKE_SA by its unique id>'
                                 '  timeout = <timeout in ms before returning>'
                                 '  loglevel = <loglevel to issue "control-log" events for>'
                                 '}'
          },
    'p': {'c': 'install', 'd': '{'
                               '    child = <CHILD_SA configuration name to install>'
                               '    ike = <optional IKE_SA configuraiton name to find child under>'
                               '}'
          },
    'u': {'c': 'uninstall', 'd': '{'
                                 '  child = <CHILD_SA configuration name to install>'
                                 '}'
          },
    'l': {'c': 'list_sas', 'd': '{'
                                '  noblock = <use non-blocking mode if key is set>'
                                '  ike = <filter listed IKE_SAs by its name>'
                                '  ike-id = <filter listed IKE_SA by its unique id>'
                                '}'
          },
    'L': {'c': 'list_conns', 'd': '{'
                                  'ike = <list connections matching a given configuration name only>'
                                  '}'
          },
    'd': {'c': 'unload_conn', 'd': '{'
                                   'name = <IKE_SA config name>'
                                   '}'
          },
    'P': {'c': 'list_policies', 'd': '{'
                                     '  drop = <set to yes to list drop policies>'
                                     '  pass = <set to yes to list bypass policies>'
                                     '  trap = <set to yes to list trap policies>'
                                     '  child = <filter by CHILD_SA configuration name>'
                                     '}'
          },
}

events = ['log', 'control-log', 'ike-updown', 'ike-rekey', 'child-updown', 'child-rekey']


@click.group(invoke_without_command=True)
@click.option('--sock', default='/opt/swan/proc/charon.vici')
@click.option('--get-help', required=False, is_flag=True)
@click.pass_context
def cli(ctx, sock, get_help=False):
    if get_help:
        click.echo(pprint.pformat(mapp_g), nl=True)
        click.echo(pprint.pformat(mapp_l))
        return

    sk = socket.socket(socket.AF_UNIX)
    sk.connect(sock)
    ipsec_s = vici.Session(sk)
    ctx.obj['ipsec_s'] = ipsec_s


@cli.command()
@click.argument('cmd', type=click.Choice(mapp_g.keys()))
@click.pass_context
def get(ctx, cmd):
    ipsec_s = ctx.obj['ipsec_s']
    ret = getattr(ipsec_s, mapp_g[cmd])()
    if ret:
        if type(ret).__name__ == 'generator':
            ret = list(ret)
        click.echo(json.dumps(ret))
    else:
        click.echo(ret)


@cli.command()
@click.argument('cmd', type=click.Choice(mapp_l.keys()))
@click.option('--option', '-o', type=click.Tuple([unicode, unicode]), multiple=True)
@click.pass_context
def do(ctx, cmd, option):
    ipsec_s = ctx.obj['ipsec_s']
    ret = getattr(ipsec_s, mapp_l[cmd]['c'])(dict(option))
    if ret:
        if type(ret).__name__ == 'generator':
            ret = list(ret)
        click.echo(json.dumps(ret))
    else:
        click.echo(ret)


@cli.command('watch-exec')
@click.option('--event', '-e', type=click.Choice(events), multiple=True, help="{0}".format(events))
@click.option('--hook', '-x', type=unicode, multiple=True,
              help="a list of setuptools entrypoints in the group: vici.events.hook")
@click.pass_context
def watch(ctx, event, hook):
    ipsec_s = ctx.obj['ipsec_s']
    handlers = []
    for name in hook:
        handlers += list(iter_entry_points('vici.events.hook', name))

    signal.signal(signal.SIGINT, terminating)
    while True:
        fire = ipsec_s.listen(event)
        for handler in handlers:
            try:
                pyhandler = handler.load()
                pyhandler(ipsec_s, event, fire)
            except ImportError as error:
                click.echo("Was not able to load the hook '{0}' -> skipping".format(str(handler)))
                click.echo("Error was: '{0}'".format(error))
            except Exception as something:
                click.echo("Something went wrong when running the hook '{0}' -> skipping".format(str(handler)))
                click.echo("Error was: '{0}'".format(something))


@cli.command('update')
@click.pass_context
def update(ctx):
    ipsec_s = ctx.obj['ipsec_s']
    loaded = set(sum([lc.values()[0]['children'].keys() for lc in ipsec_s.list_conns()], []))
    initiated = set(sum([ic.values()[0]['child-sas'].keys() for ic in ipsec_s.list_sas()], []))
    to_update = list(loaded - initiated)
    to_terminate = list(initiated - loaded)
    for missing_connection in to_update:
        do_init = list(ipsec_s.initiate(dict(child=missing_connection, timeout=-1)))
    for deleted_connection in to_terminate:
        do_del = list(ipsec_s.terminate(dict(child=deleted_connection, timeout=-1)))
    click.echo(json.dumps(dict(updated=to_update, terminated=to_terminate)))


def terminating(signal, frame):
    click.echo("Stopping event watch ")
    sys.exit(0)


def entry():
    return cli(obj={})


if __name__ == '__main__':
    entry()
