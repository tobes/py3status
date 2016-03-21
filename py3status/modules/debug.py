# -*- coding: utf-8 -*-
"""
Debugging info for loaded modules.

Provides quick and dirty information on loaded modules.

Configuration parameters:
    button_next: Button that when clicked will switch to display next module.
        Setting to `0` will disable this action. (default 4)
    button_prev: Button that when clicked will switch to display previous
        module.  Setting to `0` will disable this action. (default 5)
    format: Format for module output. (default "DEBUG: {name} {count} {time} {alive} {cached_until}")


Format of status string placeholders:
    {alive} State of thread `Alive` or `Dead`
    {cached_until} Time till next update of the module
    {count} Number of updates of module since being monitored
    {name} Module name
    {time} Time that module has taken running since monitored

@author tobes
@license BSD
"""

from time import time
import types


class Py3status:
    # available configuration parameters
    button_next = 4
    button_prev = 5
    format = 'DEBUG: {name} {count} {time} {alive} {cached_until}'

    class Meta:
        include_py3_module = True

    def __init__(self):
        self.initialized = False

    def _init(self):
        try:
            self.py3_wrapper = self.py3_module.py3_wrapper
        except AttributeError:
            self.py3_wrapper = None
            good = False
        if self.py3_wrapper:
            good = self._patch()
        self.active = 0
        self.initialized = good

    def _patch(self):

        good = len(self.py3_wrapper.modules) == len(self.py3_wrapper.py3_modules)
        if not good:
            return False
        for module in self.py3_wrapper.modules.values():
            module.debug = {'count': 0, 'time': 0}
            module._run = module.run

            def run(self):
                now = time()
                self.debug['count'] += 1
                self._run()
                self.debug['time'] += time() - now

            module.run = types.MethodType(run, module)
        return True

    def _next(self):
        self.active = (self.active + 1) % len(self.py3_wrapper.py3_modules)

    def _prev(self):
        self.active = (self.active - 1) % len(self.py3_wrapper.py3_modules)

    def debug(self, i3s_output_list, i3s_config):
        """
        Display a output of current module
        """
        if not self.initialized:
            self._init()

        if not self.initialized:
            return {
                'cached_until': time() + 0.1,
                'full_text': ''
            }

        name = self.py3_wrapper.py3_modules[self.active]
        module = self.py3_wrapper.modules[name]
        count = module.debug['count']
        _time = module.debug['time']
        _time = round(_time, 3)
        alive = 'Alive' if module.timer.is_alive() else 'Dead'
        cached_until = '{0:.2f}'.format(module.cache_time - time())

        response = {
            'cached_until': time() + 0.1,
            'full_text': self.format.format(name=name,
                                            count=count,
                                            time=_time,
                                            alive=alive,
                                            cached_until=cached_until)
        }
        return response

    def on_click(self, i3s_output_list, i3s_config, event):
        """
        Switch the displayed module or pass the event on to the active module
        """
        if self.button_next and event['button'] == self.button_next:
            self._next()
        elif self.button_prev and event['button'] == self.button_prev:
            self._prev()


if __name__ == "__main__":
    """
    Test this module by calling it directly.
    """
    from time import sleep
    x = Py3status()
    config = {}

    while True:
        print(x.debug([], config))
        sleep(1)
