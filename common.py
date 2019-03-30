
import logging
import contextlib
from collections import namedtuple

def logger(name):
    # setup logger
    logger = logging.getLogger(name)
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)-23s %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

    # add trace level (https://stackoverflow.com/a/13638084/1562506)
    TRACE = 9
    logging.addLevelName(TRACE, "TRACE")
    def trace(self, message, *args, **kws):
        # Yes, logger takes its '*args' as 'args'.
        if self.isEnabledFor(TRACE):
            self._log(TRACE, message, args, **kws)
    logging.Logger.trace = trace
    return logger

_logger = logger(__name__)

# dataclasses
Coord = namedtuple("Coord", "x y")



def annotate(function, cmd):
    """Add a string representation to the command"""
    function.cmd = str(cmd)
    return function

def get_cmd(value):
    """Obtain the string representation of a command"""
    if isinstance(value, list):
        cmds = [str(get_cmd(fn)) for fn in value]
        return "[ " +  ", ".join(cmds) + " ]"

    if callable(value):
        try:
            return value.cmd
        except:
            if not value.__name__:
                return str(value)
            return value.__name__

    return None


# https://stackoverflow.com/a/1633483/1562506
def iter_first_last(iterator):
    """Iterator which marks the first and the last item.
    Usage: for item, is_first, is_last in iter_first_last(...)
    """

    iterator = iter(iterator)
    prev = next(iterator)
    first = True
    for item in iterator:
        yield prev, first, False
        first = False
        prev = item
    # Last item
    yield prev, first, True


@contextlib.contextmanager
def command_definitions(globals):
    # save previouslydefined functions
    prev_def = set()
    prev_def.update(globals())

    yield

    # get newly defined functions
    glob = globals()
    command_names = set(glob).difference(prev_def)

    # convert functions to commands [i.e., a function cmd(state)]
    for name in command_names:
        _logger.trace("registering command %s", name)
        cmd = glob[name]
        argcount = cmd.__code__.co_argcount
        fn = globals()[name]

        if argcount == 1:
            fn = annotate(fn, fn.__name__)
        else:
            # partially apply 'argcount-1' parameters
            def wrap(*args, name=name, n=argcount-1, fn=fn):
                if len(args) != n:
                    _logger.error("wrong number of parameters for command %s expected %d, got %d", name, n, len(args))

                return annotate(lambda state: fn(*args, state), name + "(" + ",".join([str(a) for a in args]) + ")")

            fn = wrap

        globals()[name] = fn

    # register commands
    if "commands" in globals():
        command_names.update(globals()["commands"])
    globals()["commands"] = command_names




