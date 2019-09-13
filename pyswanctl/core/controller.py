import socket
from pkg_resources import iter_entry_points
import vici
from vici.protocol import Packet, Message
import logging
from collections import defaultdict
import inspect
import signal


class PySwanCtl(object):
    log = logging.getLogger(__name__)
    specs = defaultdict(set)

    def __init__(self, sock='/opt/swan/proc/charon.vici'):
        vici_sock = socket.socket(socket.AF_UNIX)
        vici_sock.connect(sock)
        self.ipsec_s = vici.Session(vici_sock)
        self.sock = sock
        self.watchers = []

    def make_call(self, api, **args):
        api_func = getattr(self.ipsec_s, api)
        if not args:
            return api_func()
        return api_func(args)

    def iter_call(self, api, **args):
        response = self.make_call(api, **args)
        if response:
            if type(response).__name__ == 'generator':
                response = list(response)

        return response

    def watch(self, event_name, entry_point_names=None, group_name='pyswanctl.event_handler', detach=False):
        entry_point_names = entry_point_names or [None]
        watcher = Watcher(self.sock, event_name, entry_point_names, group_name)
        return watcher.run()


class Watcher(object):
    log = logging.getLogger(__name__)

    def __init__(self, sock, event_name, entry_point_names, group_name):
        super(Watcher, self).__init__()
        self.sock = sock
        self.event_name = event_name
        self.entry_points = entry_point_names
        self.group_name = group_name
        self.handlers = []

    def get_session(self):
        vici_sock = socket.socket(socket.AF_UNIX)
        vici_sock.connect(self.sock)
        return vici.Session(vici_sock)

    def get_handlers(self):
        handlers = []
        for name in self.entry_points:
            handlers += list(iter_entry_points(self.group_name, name))
        return handlers

    def on_event_received(self, event_type, events):
        handlers = self.handlers
        for handler in handlers:
            try:
                pyhandler = handler.load()
                kwargs = dict(events=events, event_type=event_type)
                if 'log' in inspect.getargspec(pyhandler).args:
                    kwargs['log'] = self.log
                return pyhandler(**kwargs)
            except ImportError as error:
                self.log.error("Was not able to load the hook '{0}' -> skipping".format(str(handler)))
                self.log.exception(error)
            except Exception as something:
                self.log.error("Something went wrong when running the hook '{0}' -> skipping".format(str(handler)))
                self.log.exception(something)

    def run(self):
        vici = self.get_session().handler
        self.handlers = self.get_handlers()
        vici._register_unregister(self.event_name, True)
        return self.watch(vici)

    def watch(self, vici):
        while True:
            response = Packet.parse(vici.transport.receive())
            if response.response_type == Packet.EVENT:
                event_type = response.event_type
                events = Message.deserialize(response.payload)
                yield self.on_event_received(event_type, events)
