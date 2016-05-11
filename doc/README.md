
Py3status
=========

[Using modules](#modules)

* [Available modules](#available_modules)
* [Ordering modules](#ordering_modules)
* [Configuring modules](#configuring_modules)
* [Grouping modules](#group_modules)

[Custom click events](#on_click)

* [Special on_click commands](#on_click_commands)
* [Example config](#on_click_example)

[Writing custom modules](#writing_custom_modules)

* [Example 1: Hello world](#example_1)
* [Example 2: Configuration parameters](#example_2)
* [Example 3: Events](#example_3)
* [Example 4: Status string placeholders](#example_4)


<a name="modules"></a>Using modules
===================================

Modules in Py3status are configured using your `i3status.conf`.

Py3status tries to find the config in the following locations.
`~/.i3/i3status.conf`,
`~/.i3status.conf`,
`/etc/i3status.conf`,
`XDG_CONFIG_HOME/.config/i3status/config`,
`~/.config/i3status/config`,
`XDG_CONFIG_DIRS/i3status/config`,
`/etc/xdg/i3status/config`,

You can also specify the config location using `py3status -c <path to config
file>` in your i3 configuration file.

#### <a name="available_modules"></a>Available modules
Py3status comes with a large range of modules.

[List of available modules and their configuration details.](
https://github.com/ultrabug/py3status/blob/master/py3status/modules/README.md)

#### <a name="ordering_modules"></a>Loading a py3status module and ordering modules output


To load a py3status module you just have to list it like any other i3status
module using the `order += parameter`.

Ordering your py3status modules in your i3bar is just the same as i3status
modules, just list the order parameter where you want your module to be
displayed.

For example you could insert and load the imap module like this:
```
order += "disk /home"
order += "disk /"
order += "imap"
order += "time"
```

#### <a name="configuring_modules"></a>Configuring a py3status module

Your py3status modules are configured the exact same way as i3status modules, directly from your `i3status.conf`, like this :
```
# configure the py3status imap module
# and run thunderbird when I left click on it
imap {
    cache_timeout = 60
    imap_server = 'imap.myprovider.com'
    mailbox = 'INBOX'
    name = 'Mail'
    password = 'coconut'
    port = '993'
    user = 'mylogin'
    on_click 1 = "exec thunderbird"
}
```

#### <a name="group_modules"></a>Grouping Modules

The [group](
https://github.com/ultrabug/py3status/blob/master/py3status/modules/README.md#group
)
module allows you to group several modules togeather.  Only one of the
modules are displayed at a time.  The displayed module can either be cycled
through automatically or by user action.


## <a name="on_click"></a>Custom click events

Py3status allows you to easily add click events to modules in your i3bar.
These modules can be both i3status or py3status modules.  This is done in
your `i3status.config` using the `on_click` parameter.

Just add a new configuration parameter named `on_click [button number]` to
your module config and py3status will then execute the given i3 command
(using i3-msg).

This means you can run simple tasks like executing a program or execute any
other i3 specific command.

As an added feature and in order to get your i3bar more responsive, every
`on_click` command will also trigger a module refresh. This works for both
py3status modules and i3status modules as described in the refresh command
below.

#### <a name="on_click_commands"></a>Special on_click commands

There are two commands you can pass to the `on_click` parameter that have a
special meaning to py3status :

*  `refresh` : This will refresh (expire the cache) of the clicked module.
   This also works for i3status modules (it will send a SIGUSR1 to i3status
   for you).

*  `refresh_all` : This will refresh all the modules from your i3bar
   (i3status included). This has the same effect has sending a SIGUSR1 to
   py3status.

#### <a name="on_click_example"></a>Example i3status.conf:

```
# reload the i3 config when I left click on the i3status time module
# and restart i3 when I middle click on it
time {
    on_click 1 = "reload"
    on_click 2 = "restart"
}

# control the volume with your mouse (need >i3-4.8)
# launch alsamixer when I left click
# kill it when I right click
# toggle mute/unmute when I middle click
# increase the volume when I scroll the mouse wheel up
# decrease the volume when I scroll the mouse wheel down
volume master {
    format = "♪: %volume"
    device = "default"
    mixer = "Master"
    mixer_idx = 0
    on_click 1 = "exec i3-sensible-terminal -e alsamixer"
    on_click 2 = "exec amixer set Master toggle"
    on_click 3 = "exec killall alsamixer"
    on_click 4 = "exec amixer set Master 1+"
    on_click 5 = "exec amixer set Master 1-"
}

# run wicd-gtk GUI when I left click on the i3status ethernet module
# and kill it when I right click on it
ethernet eth0 {
    # if you use %speed, i3status requires root privileges
    format_up = "E: %ip"
    format_down = ""
    on_click 1 = "exec wicd-gtk"
    on_click 3 = "exec killall wicd-gtk"
}

# run thunar when I left click on the / disk info module
disk / {
    format = "/ %free"
    on_click 1 = "exec thunar /"
}

# this is a py3status module configuration
# open an URL on opera when I left click on the weather_yahoo module
weather_yahoo paris {
    cache_timeout = 1800
    woeid = 615702
    forecast_days = 2
    on_click 1 = "exec opera http://www.meteo.fr"
    request_timeout = 10
}
```


<a name="writing_custom_modules"></a>Writing custom py3status modules
=====================================================================

__This guide covers the new style of py3status modules.  These are only
available in version 3.0 and above__

Writing custom modules for py3status is easy.  This guide will teach you how.

Let's start by looking at a simple example.

## <a name="example_1"></a>Example 1:  The basics - Hello World!

Here we start with the most basic module that just outputs a static string to
the status bar.

```
# -*- coding: utf-8 -*-
"""
Example module that says 'Hello World!'

This demonstrates how to produce a simple custom module.
"""


class Py3status:

    def hello_world(self):
        return {
            'full_text': 'Hello World!',
            'cache_until': self.py3.CACHE_FOREVER
        }
```

####Running the example


Save the file as `hello_world.py` in a directory that
py3status will check for modules. By default it will look in
`$HOME/.i3/py3status/` or you can specify additional directories using
`--include` when you run py3status.

You need to tell py3status about your new module so in your `i3status.conf` add
```
order += "hello_world"
```

Then restart i3 by pressing `Mod` + `Shift` + `R`.  Your new module should now
show up in the status bar.

####How does it work?

The `Py3status` class tell py3status that this is a module.  The module gets
loaded.  py3status then calls any public methods that the class contains to get
a response.  In our example there is a single method `hello_world()`.

####The response

The response that a method returns must be a python `dict`.
It should contain at least two key / values.

######full_text

This is the text that will be displayed in the status bar.

######cache_until

This tells py3status how long it should consider your
response valid before it should re-run the method to get a fresh response.  In
our example our response will not need to be updated so we can use the special
`self.py3.CACHE_FOREVER` constant.  This tells py3status to consider our
response always valid.

####self.py3

This is a special object that gets injected into Py3status
modules.  It helps provide functionality for the module, such as the
`CACHE_FOREVER` constant.


## <a name="example_2"></a>Example 2: Configuration parameters

Allow users to supply configuration to a module.

```
# -*- coding: utf-8 -*-
"""
Example module that says 'Hello World!' that can be customised.

This demonstrates how to use configuration parameters.

Configuration parameters:
    format: Display format (default 'Hello World!')
"""


class Py3status:

    format = 'Hello World!'

    def hello_world(self):
        return {
            'full_text': self.format,
            'cache_until': self.py3.CACHE_FOREVER
        }
```
This module still outputs 'Hello World' as before but now you can customise the
output using your `i3status.config` for example to show the text in French.
```
hello_world {
    format = 'Bonjour le monde'
}
```
In your module `self.format` will have been set to the value supplied in the
config.


## <a name="example_3"></a>Example 3: Events

Catch click events and perform an action.

```
# -*- coding: utf-8 -*-
"""
Example module that handles events

This demonstrates how to use events.
"""


class Py3status:

    def __init__(self):
        self.full_text = 'Click me'

    def click_info(self):
        return {
            'full_text': self.full_text,
            'cache_until': self.py3.CACHE_FOREVER
        }

    def on_click(self, event):
        """
        event will be a dict like
        {'y': 13, 'x': 1737, 'button': 1, 'name': 'example', 'instance': 'first'}
        """
        button = event['button']
        self.full_text = 'You pressed button {}'.format(button)
        # Our modules update methods will get called automatically.
```

The `on_click` method of a module is special and will get
called when the module is clicked on.  The event parameter
will be a dict that gives information about the event. A
typical event dict will look like `{'y': 13, 'x': 1737,
'button': 1, 'name': 'example', 'instance': 'first'}` you
should only receive events for the module clicked on, so
generally we only care about the button.

The `__init__()` method is called when our class is instantiated.  __Note: this
is called before any config parameters have been set__

## <a name="example_4"></a>Example 4: Status string placeholders

Status string placeholders allow us to add information to formats.


```
# -*- coding: utf-8 -*-
"""
Example module that demonstrates status string placeholders

Configuration parameters:
    format: Initial format to use
        (default 'Click me')
    format_clicked: Display format to use when we are clicked
        (default 'You pressed button {button}')

Format status string parameters:
    {button} The button that was pressed
"""


class Py3status:
    format = 'Click me'
    format_clicked = 'You pressed button {button}'

    def __init__(self):
        self.button = None

    def click_info(self):
        if self.button:
            full_text = self.format_clicked.format(button=self.button)
        else:
            full_text = self.format

        return {
            'full_text': full_text,
            'cache_until': self.py3.CACHE_FOREVER
        }

    def on_click(self, event):
        """
        event will be a dict like
        {'y': 13, 'x': 1737, 'button': 1, 'name': 'example', 'instance': 'first'}
        """
        self.button = event['button']
        # Our modules update methods will get called automatically.
```

This works just like the previous example but we can now be customised.  The
following example assumes that our module has been saved as `click_info.py`.

```
click_info {
    format = "Cliquez ici"
    format_clicked = "Vous bouton {button} enfoncé"
}
```
