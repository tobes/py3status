*********
py3status
*********
|version| |travis|

.. |version| image:: https://img.shields.io/pypi/v/py3status.svg
.. |travis| image:: https://travis-ci.org/ultrabug/py3status.svg?branch=master

**py3status** is an extensible i3status wrapper written in python.

Using py3status, you can take control of your i3bar easily by:

- using one of the availables modules shipped with py3status
- writing your own modules and have their output displayed on your bar
- handling click events on your i3bar and play with them in no time
- seeing your clock tick every second whatever your i3status interval

**No extra configuration file needed**, just install & enjoy !

Documentation
=============
Up to date documentation:

-  `Using modules <https://github.com/ultrabug/py3status/blob/master/doc/README.md#modules>`_

-  `Custom click events <https://github.com/ultrabug/py3status/blob/master/doc/README.md#on_click>`_

-  `Writing custom modules <https://github.com/ultrabug/py3status/blob/master/doc/README.md#writing_custom_modules>`_

Get help or share your ideas on IRC:

- channel **#py3status** on **FreeNode**

Usage
=====
In your i3 config file, simply switch from *i3status* to *py3status* in your *status_command*:
::

    status_command py3status

Usually you have your own i3status configuration, just point to it:
::

    status_command py3status -c ~/.i3/i3status.conf

Available modules
=================
You can get a list and short description of all the available modules by using the CLI:
::

    $ py3status modules list


To get more details about all the available modules and their configuration, use:
::

    $ py3status modules details

All the modules shipped with py3status are present in the sources in the `py3status/modules <https://github.com/ultrabug/py3status/tree/master/py3status/modules>`_ folder.

Most of them are **configurable directly from your current i3status.conf**, check them out to see all the configurable variables.

Installation
============
Pypi
----
Using pip:
::

    $ pip install py3status

NB: **Debian users** should use **pypi-install** from the *python-stdeb* package instead of pip.

Gentoo Linux
------------
Using emerge:
::

    $ sudo emerge -a py3status

Arch Linux
----------
Thanks to @Horgix, py3status is present in the Arch User Repository:

- `py3status <https://aur.archlinux.org/packages/py3status>`_, which is a
  stable version updated at each release
- `py3status-git <https://aur.archlinux.org/packages/py3status-git/>`_, which
  builds directly against the upstream master branch

Thanks to @waaaaargh and @carstene1ns for initially creating the packages.

Fedora
------
Using dnf:
::

    $ dnf install py3status

Options
=======
You can see the help of py3status by issuing `py3status -h`:
::

    -h, --help            show this help message and exit
    -b, --dbus-notify     use notify-send to send user notifications rather than
                        i3-nagbar, requires a notification daemon eg dunst
    -c I3STATUS_CONF, --config I3STATUS_CONF
                          path to i3status config file
    -d, --debug           be verbose in syslog
    -i INCLUDE_PATHS, --include INCLUDE_PATHS
                          include user-written modules from those directories
                          (default ~/.i3/py3status)
    -n INTERVAL, --interval INTERVAL
                          update interval in seconds (default 1 sec)
    -s, --standalone      standalone mode, do not use i3status
    -t CACHE_TIMEOUT, --timeout CACHE_TIMEOUT
                          default injection cache timeout in seconds (default 60
                          sec)
    -v, --version         show py3status version and exit

Control
=======
Just like i3status, you can force an update of your i3bar by sending a SIGUSR1 signal to py3status.
Note that this will also send a SIGUSR1 signal to i3status.
::

    killall -USR1 py3status
