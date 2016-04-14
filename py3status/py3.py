from time import sleep
import inspect


PY3_CACHE_FOREVER = -1


class Py3:
    """
    Helper object that gets injected as self.py3 into Py3status
    modules that have not got that attribute set already.

    This allows functionality like:
        User notifications
        Forcing module to update (even other modules)
        Triggering events for modules
    """

    CACHE_FOREVER = PY3_CACHE_FOREVER

    def __init__(self, module):
        self._module = module

    def update(self, module_name=None):
        """
        Update a module.  If module_name is supplied the module of that
        name is updated.  Otherwise the module calling is updated.
        """
        if not module_name:
            return self._module.force_update()
        else:
            module = self.get_module_info(self, module_name).get(module_name)
            if module:
                module.force_update()

    def get_module_info(self, module_name):
        """
        Helper function to get info for named module.
        Info comes back as a dict containing.

        'module': the instance of the module,
        'position': list of places in i3bar, usually only one item
        'type': module type py3status/i3status
        """
        return self._module._py3_wrapper.output_modules.get(module_name)

    def trigger_event(self, module_name, event):
        """
        Trigger the event on named module
        """
        if module_name:
            self._module._py3_wrapper.events_thread.process_event(
                module_name, event)

    def notify_user(self, msg, level='info'):
        """
        Send notification to user.
        level can be 'info', 'error' or 'warning'
        """
        self._module._py3_wrapper.notify_user(msg, level=level)


class MockPy3:
    """
    Mock Helper object.
    """

    CACHE_FOREVER = PY3_CACHE_FOREVER

    def update(self, module_name=None):
        pass

    def get_module_info(self, module_name):
        pass

    def trigger_event(self, module_name, event):
        pass

    def notify_user(self, msg, level='info'):
        pass


def test_module(module_class):
    config = {
        'color_bad': '#FF0000',
        'color_degraded': '#FFFF00',
        'color_good': '#00FF00'
    }
    module = module_class()
    setattr(module, 'py3', MockPy3())
    methods = []
    for method_name in sorted(dir(module)):
        if method_name.startswith('_'):
            continue
        if method_name in ['on_click', 'kill', 'py3']:
            continue
        if not hasattr(getattr(module_class, method_name, ''), '__call__'):
            continue

        method = getattr(module, method_name, None)
        args, vargs, kw, defaults = inspect.getargspec(method)
        if len(args) == 1:
            methods.append((method_name, []))
        else:
            methods.append((method_name, [[], config]))
    while True:
        try:
            for method, method_args in methods:
                print(getattr(module, method)(*method_args))
            sleep(1)
        except KeyboardInterrupt:
            break
