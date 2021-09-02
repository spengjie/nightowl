import threading


class Manager:

    def __init__(self):
        self.timers = {}

    def set_timer(self, name, interval, function,
                  args=None, kwargs=None):
        if name in self.timers:
            self.timers[name].cancel()
        if args is None:
            args = []
        if kwargs is None:
            kwargs = {}
        timer = threading.Timer(interval, self._execute, args=(name, function),
                                kwargs={'args': args, 'kwargs': kwargs})
        self.timers[name] = timer
        timer.start()

    def _execute(self, name, function, args=None, kwargs=None):
        if args is None:
            args = []
        if kwargs is None:
            kwargs = {}
        self.timers.pop(name)
        function(*args, **kwargs)


manager = Manager()


def set_timer(name, interval, function, args=None, kwargs=None):
    return manager.set_timer(name, interval, function,
                             args=args, kwargs=kwargs)
