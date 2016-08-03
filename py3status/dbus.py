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
        self.py3_wrapper.refresh_modules()

    def update(self, args):
        # update any modules starting with the given string
        self.py3_wrapper.refresh_modules(args)


class DbusControls:

    def __init__(self, py3_wrapper):
        self.py3_wrapper = py3_wrapper
        self.active = False
        self.force_update = False
        self.selected = 0
        self.current_output = []
        self.loop = None
        if dbus_available:
            self.start_handler_thread()

    def kill(self):
      #  if self.loop:
      #      self.loop.quit()
        self.service.unpublish()

    def event(self, button):
        # Create and dispatch a fake event
        item = self.current_output[self.selected]
        event = {
            'x': 0,
            'y': 0,
            'instance': item.get('instance', ''),
            'name': item.get('name', ''),
            'button': button,
        }
        self.py3_wrapper.events_thread.dispatch_event(event)

    def start_handler_thread(self):
        """Called once to start the event handler thread."""
        t = Thread(target=self.start_loop)
        t.daemon = True
        t.start()

    def start_loop(self):
        """Starts main event handler loop, run in handler thread t."""
        bus = SessionBus()
        self.service = bus.publish("py3status.control", DbusInterface(self))
        self.loop = GObject.MainLoop()
        self.loop.run()
