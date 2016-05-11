import select
import sys

from threading import Thread
from time import time
from subprocess import Popen, call, PIPE
from syslog import syslog, LOG_INFO, LOG_WARNING
from json import loads

from py3status.profiling import profile


class IOPoller:
    """
    This class implements a predictive and timing-out I/O reader
    using select and the poll() mechanism for greater compatibility.
    """

    def __init__(self, io, eventmask=select.POLLIN):
        """
        Our default is to read (POLLIN) the specified 'io' file descriptor.
        """
        self.io = io
        self.poller = select.poll()
        self.poller.register(io, eventmask)

    def readline(self, timeout=500):
        """
        Try to read our I/O for 'timeout' milliseconds, return None otherwise.
        This makes calling and reading I/O non blocking !
        """
        poll_result = self.poller.poll(timeout)
        if poll_result:
            line = self.io.readline().strip()
            if self.io == sys.stdin and line == '[':
                # skip first event line wrt issue #19
                line = self.io.readline().strip()
            try:
                # python3 compatibility code
                line = line.decode()
            except (AttributeError, UnicodeDecodeError):
                pass
            return line
        else:
            return None


class Events(Thread):
    """
    This class is responsible for dispatching event JSONs sent by the i3bar.
    """

    def __init__(self, py3_wrapper):
        """
        We need to poll stdin to receive i3bar messages.
        """
        Thread.__init__(self)
        self.config = py3_wrapper.config
        self.i3s_config = py3_wrapper.i3status_thread.config
        self.last_refresh_ts = time()
        self.lock = py3_wrapper.lock
        self.modules = py3_wrapper.modules
        self.on_click = self.i3s_config['on_click']
        self.poller_inp = IOPoller(sys.stdin)
        self.py3_wrapper = py3_wrapper

    def dispatch(self, module, obj, event):
        """
        Dispatch the event or enforce the default clear cache action.
        """
        module_name = '{} {}'.format(module.module_name,
                                     module.module_inst).strip()
        #
        if module.click_events:
            # module accepts click_events, use it
            module.click_event(event)
            if self.config['debug']:
                syslog(LOG_INFO, 'dispatching event {}'.format(event))
        else:
            # default button 2 action is to clear this method's cache
            if self.config['debug']:
                syslog(LOG_INFO, 'dispatching default event {}'.format(event))

        # to make the bar more responsive to users we ask for a refresh
        # of the module or of i3status if the module is an i3status one
        self.refresh(module_name)

    def i3bar_click_events_module(self):
        """
        Detect the presence of the special i3bar_click_events.py module.

        When py3status detects a module named 'i3bar_click_events.py',
        it will dispatch i3status click events to this module so you can catch
        them and trigger any function call based on the event.
        """
        for module in self.modules.values():
            if not module.click_events:
                continue
            if module.module_name == 'i3bar_click_events.py':
                return module
        else:
            return False

    def refresh(self, module_name):
        """
        Force a cache expiration for all the methods of the given module.

        We rate limit the i3status refresh to 100ms.
        """
        module = self.modules.get(module_name)
        if module is not None:
            if self.config['debug']:
                syslog(LOG_INFO, 'refresh module {}'.format(module_name))
            module.force_update()
        else:
            if time() > (self.last_refresh_ts + 0.1):
                if self.config['debug']:
                    syslog(
                        LOG_INFO,
                        'refresh i3status for module {}'.format(module_name))
                call(['killall', '-s', 'USR1', 'i3status'])
                self.last_refresh_ts = time()

    def refresh_all(self, module_name):
        """
        Force a full refresh of py3status and i3status modules by sending
        a SIGUSR1 signal to py3status.

        We rate limit this command to 100ms for obvious abusive behavior.
        """
        if time() > (self.last_refresh_ts + 0.1):
            call(['killall', '-s', 'USR1', 'py3status'])
            self.last_refresh_ts = time()

    def on_click_dispatcher(self, module_name, command):
        """
        Dispatch on_click config parameters to either:
            - Our own methods for special py3status commands (listed below)
            - The i3-msg program which is part of i3wm
        """
        py3_commands = ['refresh', 'refresh_all']
        if command is None:
            return
        elif command in py3_commands:
            # this is a py3status command handled by this class
            method = getattr(self, command)
            method(module_name)
        else:
            # this is a i3 message
            self.i3_msg(module_name, command)

            # to make the bar more responsive to users we ask for a refresh
            # of the module or of i3status if the module is an i3status one
            self.refresh(module_name)

    @staticmethod
    def i3_msg(module_name, command):
        """
        Execute the given i3 message and log its output.
        """
        i3_msg_pipe = Popen(['i3-msg', command], stdout=PIPE)
        syslog(LOG_INFO, 'i3-msg module="{}" command="{}" stdout={}'.format(
            module_name, command, i3_msg_pipe.stdout.read()))

    def process_event(self, module_name, event, top_level=True):
        """
        Process the event for the named module.
        Events may have been declared in i3status.conf, modules may have
        on_click() functions. There is a default middle click event etc.
        """
        button = event.get('button', 0)
        default_event = False
        dispatched = False
        # execute any configured i3-msg command
        # we do not do this for containers
        if top_level:
            if self.on_click.get(module_name, {}).get(button):
                self.on_click_dispatcher(module_name,
                                         self.on_click[module_name].get(button))
                dispatched = True
            # otherwise setup default action on button 2 press
            elif button == 2:
                default_event = True

        for module in self.modules.values():
            # skip modules not supporting click_events
            # unless we have a default_event set
            if not module.click_events and not default_event:
                continue

            # check for the method name/instance
            if ' ' in module_name:
                name, instance = module_name.split(' ')
            else:
                name, instance = module_name, None
            for obj in module.methods.values():
                if name == obj['name']:
                    if instance:
                        if instance == obj['instance']:
                            self.dispatch(module, obj, event)
                            dispatched = True
                            break
                    else:
                        self.dispatch(module, obj, event)
                        dispatched = True
                        break

        # find container that holds the module and call its onclick
        module_groups = self.i3s_config['.module_groups']
        containers = module_groups.get(module_name)
        for container in containers:
            self.process_event(container, event, top_level=False)

        # fall back to i3bar_click_events.py module if present
        if not dispatched:
            module = self.i3bar_click_events_module()
            if module:
                if self.config['debug']:
                    syslog(LOG_INFO, 'dispatching event to i3bar_click_events')
                self.dispatch(module, obj, event)

    @profile
    def run(self):
        """
        Wait for an i3bar JSON event, then find the right module to dispatch
        the message to based on the 'name' and 'instance' of the event.

        In case the module does NOT support click_events, the default
        implementation is to clear the module's cache
        when the MIDDLE button (2) is pressed on it.

        Example event:
        {'y': 13, 'x': 1737, 'button': 1, 'name': 'empty', 'instance': 'first'}
        """
        while self.lock.is_set():
            event_str = self.poller_inp.readline()
            if not event_str:
                continue
            try:
                # remove leading comma if present
                if event_str[0] == ',':
                    event_str = event_str[1:]
                event = loads(event_str)

                if self.config['debug']:
                    syslog(LOG_INFO, 'received event {}'.format(event))

                # usage variables
                instance = event.get('instance', '')
                name = event.get('name', '')

                # composites have an index which is passed to i3bar with
                # the instance.  We need to separate this out here and
                # clean up the event.  If index
                # is an integer type then cast it as such.
                if ' ' in instance:
                    instance, index = instance.split(' ', 1)
                    try:
                        index = int(index)
                    except ValueError:
                        pass
                    event['index'] = index
                    event['instance'] = instance

                if self.config['debug']:
                    syslog(
                        LOG_INFO,
                        'trying to dispatch event to module "{}"'.format(
                            '{} {}'.format(name, instance).strip()))

                # guess the module config name
                module_name = '{} {}'.format(name, instance).strip()
                # do the work
                self.process_event(module_name, event)

            except Exception:
                err = sys.exc_info()[1]
                syslog(LOG_WARNING, 'event failed ({})'.format(err))
