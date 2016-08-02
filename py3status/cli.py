import sys

from pydbus import SessionBus


def main():
    if len(sys.argv) < 2:
        sys.exit(1)
    bus = SessionBus()
    try:
        manager = bus.get("py3status.control")
    except:
        print('py3status dbus service not available')
        sys.exit(2)
    if not manager.Command(' '.join(sys.argv[1:])):
        print('An error occured')
        sys.exit(2)


if __name__ == '__main__':
    main()
