from threading import Thread
from subprocess import call

try:
    from pydbus import SessionBus
    from gi.repository import GObject
    dbus_available = True
except ImportError:
    dbus_available = False


class DbusInterface(object):
    """
    <node>
      <interface name='py3status.control'>
        <method name='Command'>
          <arg type='s' name='a' direction='in'/>
          <arg type='b' name='response' direction='out'/>
        </method>
      </interface>
    </node>
    """

    def __init__(self, controller):
        self.controller = controller
        self.py3_wrapper = controller.py3_wrapper

    def Command(self, cmd):
        """Run command sent via dbus"""
        self.py3_wrapper.log('py3status-cli {}'.format(cmd))
        if cmd:
            if ' ' in cmd:
                command, args = cmd.split(' ', 1)
            else:
                command, args = cmd, None
            if hasattr(self, command):
                getattr(self, command)(args)
                self.controller.force_update = True
                return True
        return False

    def activate(self, args):
        self.controller.active = True

    def deactivate(self, args):
        self.controller.active = False

    def next(self, args):
        self.controller.selected += 1
        outputs = len(self.controller.current_output)
        if self.controller.selected >= outputs:
            self.controller.selected = outputs - 1

    def previous(self, args):
        self.controller.selected -= 1
        if self.controller.selected < 0:
            self.controller.selected = 0

    def first(self, args):
        self.controller.selected = 0

    def last(self, args):
        outputs = len(self.controller.current_output)
        self.controller.selected = outputs - 1

    def button(self, args):
        button = int(args)
        self.controller.event(button)

    def refresh(self, args):
        # Refresh all modules.
        # FIXME move logic from sig_handler() to better named function()
        self.py3_wrapper.sig_handler(None, None)

    def update(self, args):
        # update any modules starting with the given string
        # FIXME this should move to a function in core.py
        update_i3status = False
        for name, module in self.py3_wrapper.output_modules.items():
            if name.startswith(args):
                if module['type'] == 'py3status':
                    module['module'].force_update()
                else:
                    update_i3status = True
        if update_i3status:
            call(['killall', '-s', 'USR1', 'i3status'])


class DbusControls:

    def __init__(self, py3_wrapper):
        self.py3_wrapper = py3_wrapper
        self.active = False
        self.force_update = False
        self.selected = 0
        self.current_output = []
        if dbus_available:
            self._start_handler_thread()

    def event(self, button):
        # Create and dispatch a fake event
        item = self.current_output[self.selected]
        # usage variables
        instance = item.get('instance', '')
        event = {'x': 0, 'y': 0}
        # FIXME this is repeated from events.py which should be refactored to
        # reduce this code retition.
        name = item.get('name', '')
        event['name'] = name
        event['button'] = button

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
        else:
            event['instance'] = instance

        # guess the module config name
        module_name = '{} {}'.format(name, instance).strip()
        # do the work
        self.py3_wrapper.events_thread.process_event(module_name, event)

    def _start_handler_thread(self):
        """Called once to start the event handler thread."""
        t = Thread(target=self._start_loop)
        t.daemon = True
        t.start()

    def _start_loop(self):
        """Starts main event handler loop, run in handler thread t."""
        bus = SessionBus()
        bus.publish("py3status.control", DbusInterface(self))
        loop = GObject.MainLoop()
        loop.run()
