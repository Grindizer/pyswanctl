from cliff.command import Command
from boto3 import client
from botocore.exceptions import ClientError
import time
import threading
import json


class CWLogger(object):
    def __init__(self, group, stream, region, create):
        self.group = group
        self.stream = stream
        self.region = region
        self.client, self.seq_token = self.init_logger(create)

    def init_logger(self, create):
        cwlogs = client('logs', region_name=self.region)
        if create:
            try:
                cwlogs.create_log_stream(logGroupName=self.group, logStreamName=self.stream)
            except ClientError as error:
                if error.response['Error']['Code'] != 'ResourceAlreadyExistsException':
                    raise

        logstream = cwlogs.describe_log_streams(logGroupName=self.group,
                                                logStreamNamePrefix=self.stream,
                                                limit=1)
        streams = logstream.get('logStreams', None)
        sequence_token = streams[0].get('uploadSequenceToken', None)
        return cwlogs, sequence_token

    def publish(self, logs):
        st = {}
        if self.seq_token is not None:
            st = {'sequenceToken': self.seq_token}
        response = self.client.put_log_events(logGroupName=self.group, logStreamName=self.stream,
                                              logEvents=
                                              [
                                                  {
                                                      "timestamp": int(time.time() * 1000),
                                                      "message": json.dumps(logs)
                                                  }
                                              ],
                                              **st)

        self.seq_token = response['nextSequenceToken']
        return response.get('rejectedLogEventsInfo', True)


class CWlogs(Command):
    """ stream event and stats data to cw logs. """

    def get_parser(self, prog_name):
        parser = super(CWlogs, self).get_parser(prog_name)
        parser.add_argument('--log-group', '-g',
                            required=True, dest='group',
                            help='Name of the log group to stream to.')

        parser.add_argument('--log-stream', '-s', dest='stream', required=True,
                            help='cloudwatcg log stream to send data to.')

        parser.add_argument('--log-region', '-r', dest='region', required=True,
                            help='cloudwatcg log stream to send data to.')

        parser.add_argument('--create-stream', '-c', dest='create', action='store_true', default=False,
                            help='Weither or not create the logstream if it does not exists.')

        parser.add_argument('--delay', '-t', dest='delay', default=10, type=int,
                            help='Delay in second between two status request.')
        return parser

    def take_action(self, parsed_args):
        cwlog = CWLogger(parsed_args.group, parsed_args.stream, parsed_args.region, parsed_args.create)
        lock = threading.Lock()
        event_thread = threading.Thread(target=send_swan_event, args=(self.app.ctl, cwlog, lock))
        event_thread.daemon = True
        event_thread.start()
        stats_thread = threading.Thread(target=send_stats_event, args=(self.app.ctl, cwlog, parsed_args.delay, lock))
        stats_thread.daemon = True
        stats_thread.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        return True


def send_swan_event(swanctl, cwlog, lock):
    for event in swanctl.watch('child-updown', ['awslog']):
        with lock:
            cwlog.publish(dict(child_updown=event))


def send_stats_event(swanctl, cwlog, delay, lock):
    while True:
        logs = []
        ctx = swanctl.iter_call('list_sas')
        for cx in ctx:
            for c_name, c_pts in cx.items():
                for sa_name, sa_pts in c_pts['child-sas'].items():
                    account, region, vpc, tunnel = sa_name.split('_')
                    stats = dict(type='stats', account=account, region=region, vpc_id=vpc, ctx=tunnel)
                    stats.update(sa_pts)
                    logs.append(stats)
        if logs:
            with lock:
                cwlog.publish(dict(stats=logs))
        time.sleep(delay)
