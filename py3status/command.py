import argparse
import glob
import json
import os
import socket
import threading

SERVER_ADDRESS = '/tmp/py3status_uds'
MAX_SIZE = 1024

REFRESH_EPILOG = """
examples:
    refresh:
        # refresh all instances of the wifi module
        py3-cmd refresh wifi

        # refresh multiple modules
        py3-cmd refresh coin_market github weather_yahoo

        # refresh a module with instance name
        py3-cmd refresh "weather_yahoo chicago"

        # refresh all modules
        py3-cmd refresh --all
"""
CLICK_EPILOG = """
examples:
    button:
        # send a left/middle/right click
        py3-cmd click --button 1 dpms      # left
        py3-cmd click --button 2 sysdata   # middle
        py3-cmd click --button 3 pomodoro  # right

        # send a up/down click
        py3-cmd click --button 4 volume_status  # up
        py3-cmd click --button 5 volume_status  # down

    index:
        # toggle button in frame module
        py3-cmd click --button 1 --index button frame  # left

        # change modules in group module
        py3-cmd click --button 5 --index button group  # down

        # change time units in timer module
        py3-cmd click --button 4 --index hours timer    # up
        py3-cmd click --button 4 --index minutes timer  # up
        py3-cmd click --button 4 --index seconds timer  # up

    width, height, relative_x, relative_y, x, y:
        # py3-cmd allows users to specify click events with
        # more options. however, there are no modules that
        # uses the aforementioned options.
"""
# EXEC_EPILOG = ''
INFORMATION = [
    ('V', 'version', 'show version number and exit'),
    ('v', 'verbose', 'enable verbose mode'),
]
SUBPARSERS = [
    ('click', 'click modules', '+'),
    ('refresh', 'refresh modules', '*'),
    # ('exec', 'execute methods', '+'),
]
CLICK_OPTIONS = [
    ('button', 'specify a button number (default %(default)s)'),
    ('height', 'specify a height of the block, in pixel'),
    ('index', 'specify an index value often found in modules'),
    ('relative_x', 'specify relative X on the block, from the top left'),
    ('relative_y', 'specify relative Y on the block, from the top left'),
    ('width', 'specify a width of the block, in pixel'),
    ('x', 'specify absolute X on the bar, from the top left'),
    ('y', 'specify absolute Y on the bar, from the top left'),
]
REFRESH_OPTIONS = [
    ('all', 'refresh all modules')
]


class CommandRunner:
    """
    Encapsulates the remote commands that are available to run.
    """

    def __init__(self, py3_wrapper):
        self.debug = py3_wrapper.config['debug']
        self.py3_wrapper = py3_wrapper

    def find_modules(self, requested_names):
        """
        find the module(s) given the name(s)
        """
        found_modules = set()
        for requested_name in requested_names:
            is_instance = ' ' in requested_name

            for module_name, module in self.py3_wrapper.output_modules.items():
                if module['type'] == 'py3status':
                    name = module['module'].module_nice_name
                else:
                    name = module['module'].module_name
                if is_instance:
                    if requested_name == name:
                        found_modules.add(module_name)
                else:
                    if requested_name == name.split(' ')[0]:
                        found_modules.add(module_name)

        if self.debug:
            self.py3_wrapper.log('found %s' % found_modules)
        return found_modules

    def refresh(self, data):
        """
        refresh the module(s)
        """
        modules = data.get('module')
        # for i3status modules we have to refresh the whole i3status output.
        update_i3status = False
        for module_name in self.find_modules(modules):
            module = self.py3_wrapper.output_modules[module_name]
            if self.debug:
                self.py3_wrapper.log('refresh %s' % module)
            if module['type'] == 'py3status':
                module['module'].force_update()
            else:
                update_i3status = True
        if update_i3status:
            self.py3_wrapper.i3status_thread.refresh_i3status()

    def click(self, data):
        """
        send a click event to the module(s)
        """
        modules = data.get('module')
        for module_name in self.find_modules(modules):
            module = self.py3_wrapper.output_modules[module_name]
            if module['type'] == 'py3status':
                name = module['module'].module_name
                instance = module['module'].module_inst
            else:
                name = module['module'].name
                instance = module['module'].instance
            # make an event
            event = {'name': name, 'instance': instance}
            for name, message in CLICK_OPTIONS:
                event[name] = data.get(name)

            if self.debug:
                self.py3_wrapper.log(event)
            # trigger the event
            self.py3_wrapper.events_thread.dispatch_event(event)

    def run_command(self, data):
        """
        check the given command and send to the correct dispatcher
        """
        command = data.get('command')
        if self.debug:
            self.py3_wrapper.log('Running remote command %s' % command)
        if command == 'refresh':
            self.refresh(data)
        elif command == 'refresh_all':
            self.py3_wrapper.refresh_modules()
        elif command == 'click':
            self.click(data)


class CommandServer(threading.Thread):
    """
    Set up a Unix domain socket to allow commands to be sent to py3status
    instance.
    """

    def __init__(self, py3_wrapper):
        threading.Thread.__init__(self)

        self.debug = py3_wrapper.config['debug']
        self.py3_wrapper = py3_wrapper

        self.command_runner = CommandRunner(py3_wrapper)
        server_address = '{}.{}'.format(SERVER_ADDRESS, os.getpid())
        self.server_address = server_address

        # Make sure the socket does not already exist
        try:
            os.unlink(server_address)
        except OSError:
            if os.path.exists(server_address):
                raise

        # Create a UDS socket
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.bind(server_address)

        if self.debug:
            self.py3_wrapper.log('Unix domain socket at %s' % server_address)

        # Listen for incoming connections
        sock.listen(1)
        self.sock = sock

    def kill(self):
        """
        Remove the socket as it is no longer needed.
        """
        try:
            os.unlink(self.server_address)
        except OSError:
            if os.path.exists(self.server_address):
                raise

    def run(self):
        """
        Main thread listen to socket and send any commands to the
        CommandRunner.
        """
        while True:
            try:
                data = None
                # Wait for a connection
                if self.debug:
                    self.py3_wrapper.log('waiting for a connection')

                connection, client_address = self.sock.accept()
                try:
                    if self.debug:
                        self.py3_wrapper.log('connection from')

                    data = connection.recv(MAX_SIZE)
                    if data:
                        data = json.loads(data.decode('utf-8'))
                        if self.debug:
                            self.py3_wrapper.log(u'received %s' % data)
                        self.command_runner.run_command(data)
                finally:
                    # Clean up the connection
                    connection.close()
            except Exception:
                if data:
                    self.py3_wrapper.log('Command error')
                    self.py3_wrapper.log(data)
                self.py3_wrapper.report_exception('command failed')


def command_parser():
    """
    build and return our command parser
    """
    class Parser(argparse.ArgumentParser):
        # print usages and exit on errors
        def error(self, message):
            print('\x1b[1;31merror: \x1b[0m{}'.format(message))
            self.print_help()
            self.exit(1)

        # hide aliases on errors
        def _check_value(self, action, value):
            if action.choices is not None and value not in action.choices:
                raise argparse.ArgumentError(
                    action, "invalid choice: '{}'".format(value)
                )

    # make parser
    parser = Parser(formatter_class=argparse.RawTextHelpFormatter)

    # parser: add verbose, version
    for short, name, msg in INFORMATION:
        short = '-%s' % short
        arg = '--%s' % name
        parser.add_argument(short, arg, action='store_true', help=msg)

    # make subparsers // ALIAS_DEPRECATION: remove metavar later
    subparsers = parser.add_subparsers(dest='command', metavar='{click,refresh}')
    sps = {}

    # subparsers: add refresh, click
    for name, msg, nargs in SUBPARSERS:
        sps[name] = subparsers.add_parser(
            name,
            epilog=eval('{}_EPILOG'.format(name.upper())),
            formatter_class=argparse.RawTextHelpFormatter,
            add_help=False,
            help=msg
        )
        sps[name].add_argument(nargs=nargs, dest='module', help='module name')

    # ALIAS_DEPRECATION: subparsers: add click (aliases)
    buttons = {
        'leftclick': 1, 'middleclick': 2, 'rightclick': 3,
        'scrollup': 4, 'scrolldown': 5
    }
    for name in sorted(buttons):
        sps[name] = subparsers.add_parser(name)
        sps[name].add_argument(nargs='+', dest='module', help='module name')

    # click subparser: add button, index, width, height, relative_{x,y}, x, y
    sp = sps['click']
    for name, msg in CLICK_OPTIONS:
        arg = '--{}'.format(name)
        if name == 'button':
            sp.add_argument(arg, metavar='INT', type=int, help=msg, default=1)
        elif name == 'index':
            sp.add_argument(arg, metavar='INDEX', help=msg)
        else:
            sp.add_argument(arg, metavar='INT', type=int, help=msg)

    # refresh subparser: add all
    sp = sps['refresh']
    for name, msg in REFRESH_OPTIONS:
        arg = '--{}'.format(name)
        sp.add_argument(arg, action='store_true', help=msg)

    # parse args, post-processing
    options = parser.parse_args()

    if options.command == 'click':
        # cast string index to int
        if options.index:
            try:
                options.index = int(options.index)
            except ValueError:
                pass
    elif options.command == 'refresh':
        # refresh all
        # ALL_DEPRECATION
        if options.module is None:
            options.module = []
        # end
        valid = False
        if options.all:  # keep this
            options.command = 'refresh_all'
            options.module = []
            valid = True
        if 'all' in options.module:  # remove this later
            options.command = 'refresh_all'
            options.module = []
            valid = True
        if not options.module and not valid:
            sps['refresh'].error('missing positional or optional arguments')
    elif options.version:
        # print version
        from platform import python_version
        from py3status.version import version
        print('py3status {} (python {})'.format(version, python_version()))
        parser.exit()
    elif not options.command:
        parser.error('too few arguments')

    # ALIAS_DEPRECATION
    alias = options.command in buttons

    # py3-cmd click 3 dpms ==> py3-cmd click --button 3 dpms
    new_modules = []
    for index, name in enumerate(options.module):
        if name.isdigit():
            if alias:
                continue
            if not index:  # zero index
                options.button = int(name)
        else:
            new_modules.append(name)

    # ALIAS_DEPRECATION: Convert (click) aliases to buttons
    if alias:
        options.button = buttons[options.command]
        options.command = 'click'

    if options.command == 'click' and not new_modules:
        sps[options.command].error('too few arguments')
    options.module = new_modules

    return options


def send_command():
    """
    Run a remote command. This is called via py3-cmd utility.

    We look for any uds sockets with the correct name prefix and send our
    command to all that we find.  This allows us to communicate with multiple
    py3status instances.
    """

    def verbose(msg):
        """
        print output if verbose is set.
        """
        if options.verbose:
            print(msg)

    options = command_parser()
    msg = json.dumps(vars(options)).encode('utf-8')
    if len(msg) > MAX_SIZE:
        verbose('Message length too long, max length (%s)' % MAX_SIZE)

    # find all likely socket addresses
    uds_list = glob.glob('{}.[0-9]*'.format(SERVER_ADDRESS))

    verbose('message "%s"' % msg)
    for uds in uds_list:
        # Create a UDS socket
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

        # Connect the socket to the port where the server is listening
        verbose('connecting to %s' % uds)
        try:
            sock.connect(uds)
        except socket.error:
            # this is a stale socket so delete it
            verbose('stale socket deleting')
            try:
                os.unlink(uds)
            except OSError:
                pass
            continue
        try:
            # Send data
            verbose('sending')
            sock.sendall(msg)
        finally:
            verbose('closing socket')
            sock.close()
