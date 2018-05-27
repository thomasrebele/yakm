#!/usr/bin/env python3

"""
"yakm" stands for Yet Another Keyboard Mouse (or, alternatively, You Are Killing my Mouse).
Yakm allows you to control your mouse from your keyboard.
You can find more information in the readme.
"""

# standard imports
import copy
import string
import json


import pathlib
from os.path import expanduser
from collections import defaultdict


import draw
import input

# implemented actions:

# start
# end

# warp
# click 1
# drag 1

# move-left .5
# move-up .5
# move-down .5
# move-right .5
# cursorzoom <w> <h>: center rectangle around cursor

# grid 2x3
# cell-select 1x3
# history-back
# clear: remove keybindings

# todo

# daemonize: execute in background
# grid-nav off
# grid-nav toggle


try:
    import tkinter
    import tkinter.simpledialog

    def input_dialog(msg=""):
        """Show an input dialog using the TK library"""

        tkinter.Tk().withdraw()
        msg = str(msg) + "\n\n<Enter>  --->  OK\n<Escape>  --->  cancel"
        return tkinter.simpledialog.askstring("yakm", msg)
except Exception as e:
    print(e)
    print("WARNING: input_dialog not available")


def annotate(fn, cmd):
    """Add a string representation to the command"""
    fn.cmd = str(cmd)
    return fn

def get_cmd(x):
    """Obtain the string representation of a command"""
    if callable(x):
        try:
            return x.cmd
        except:
            if not x.__name__:
                return str(x)
            return x.__name__

    if type(x) == list:
        cmds = [get_cmd(fn) for fn in x]
        return ", ".join(cmds)


# https://stackoverflow.com/a/1633483/1562506
def iter_first_last(it):
    """Iterator which marks the first and the last item.
    Usage: for item, is_first, is_last in iter_first_last(...)
    """

    it = iter(it)
    prev = next(it)
    first = True
    for item in it:
        yield prev, first, False
        first = False
        prev = item
    # Last item
    yield prev, first, True


################################################################################
# actions
################################################################################

def warp(state):
    """Move the mouse to the middle of the zone"""

    state.nav.move(state.zone.x, state.zone.y)

def start(state):
    """Start the navigation. Enters the default mode if no other mode is active"""
    ### TODO: enter mode
    if not state.mode:
        state.enter_mode(Mode(state.nav, conf))

    state.nav.grab_keyboard()

## suspend current mode
#def suspend(state):
#    # TODO
#    pass

def exit_mode(state):
    """Exit the current mode"""
    state.exit_mode()

def end(state):
    """Exit all modes"""
    state.exit_mode(all=True)


def clear(state):
    """Clear all keybindings"""
    for k in state.nav.key_bindings():
        state.nav.input.unregister_key(k)


def info(state):
    """Write information about the current state to stdout"""
    print("bindings:")
    for key, action in state.nav.key_bindings().items():
        print("    key " + str(key) + " -> " + str(get_cmd(action)))
    win = state.nav.input.window()
    print("focused window: " + str(win))


def ignore(_state):
    """This command does nothing"""
    pass


def click(button):
    """Do a mouse click. 'button' is an integer specifying the mouse button:
    1: left, 2: middle, 3: right, 4/5: scroll"""

    return annotate(lambda state: state.nav.click(button), "click " + str(button))

def drag(button):
    """Start or stop dragging. This simulates a pressed mouse button"""

    def upd(state, button=button):
        """drag action"""
        actions = ["release"] if state.drag else ["press"]
        state.drag = not state.drag
        state.nav.click(button, actions=actions)
    return annotate(upd, "drag " + str(button))

def move_to(x, y):
    """Move the center of the zone to the specified coordinates"""

    def upd(state, x=x, y=y):
        """move_to action"""
        state.zone.x = x
        state.zone.y = y
    return annotate(upd, "move_to " + str(x) + " " + str(y))

def move_left(ratio):
    """Move the zone left by ratio*width pixels"""

    def upd(state, ratio=ratio):
        """move_left action"""
        state.zone.x = max(0, state.zone.x - state.zone.w * ratio)
    return annotate(upd, "move_left " + str(ratio))

def move_right(ratio):
    """Move the zone right by ratio*width pixels"""

    def upd(state, ratio=ratio):
        """move_right action"""
        state.zone.x = min(state.screen.w, state.zone.x + state.zone.w * ratio)
    return annotate(upd, "move_right " + str(ratio))

def move_up(ratio):
    """Move the zone up by ratio*height pixels"""

    def upd(state, ratio=ratio):
        """move_up action"""
        state.zone.y = max(0, state.zone.y - state.zone.h * ratio)
    return annotate(upd, "move_up " + str(ratio))

def move_down(ratio):
    """Move the zone down by ratio*height pixels"""

    def upd(state, ratio=ratio):
        """move_down action"""
        state.zone.y = min(state.screen.h, state.zone.y + state.zone.h * ratio)
    return annotate(upd, "move_down " + str(ratio))

def full(state):
    """Make the zone use the whole screen"""

    state.zone.w = state.screen.w
    state.zone.h = state.screen.h
    state.zone.x = state.zone.w / 2
    state.zone.y = state.zone.h / 2

def cursorzoom(width, height):
    """Set the size of the zone to width and heigth,
    and move it so that the pointer is at the center of the zone"""

    def upd(state, w=width, h=height):
        """cursorzoom action"""
        state.zone.w = w
        state.zone.h = h
        p = state.nav.pointer()
        state.zone.x = p.x
        state.zone.y = p.y
    return annotate(upd, "cursorzoom " + str(width) + " " + str(height))

def enlarge(factor):
    """Multiply the sides of the zone by factor.
    The center of the zone stays at the same position"""

    def upd(state, f=factor):
        """enlarge action"""
        state.zone.w *= f
        state.zone.h *= f
    return annotate(upd, "enlarge " + str(factor))

def grid(width, height):
    """Activate grid mode with a width x heigth cells"""

    def upd(state, w=width, h=height):
        """grid action"""
        state.grid.w = w
        state.grid.h = h
        state.enter_mode(GridMode(state.nav, conf))

    return annotate(upd, "grid " + str(width) + " " + str(height))

def cell_select(x, y):
    """Set the zone to the cell with grid coordinates (x, y)"""

    def upd(state, x=x, y=y):
        """cell_select action"""
        print(state)
        if x > state.grid.w or y > state.grid.h:
            return

        left = state.zone.left() + x / state.grid.w  * state.zone.w
        top = state.zone.top() + y / state.grid.h  * state.zone.h

        state.zone.w = max(state.grid.w, state.zone.w / state.grid.w)
        state.zone.h = max(state.grid.h, state.zone.h / state.grid.h)
        state.zone.x = left + state.zone.w/2
        state.zone.y = top + state.zone.h/2

    return annotate(upd, "cell_select " + str(x) + " " + str(y))

# grid navigation
def grid_nav(state):
    """Start grid navigation, i.e., use grid_nav_chars for selecting rows"""

    # switch to row selection mode
    state.grid_nav = "row"


def row_select(row):
    """Select the specified row and activate column selection"""

    def upd(state, y=row):
        """row_select action"""
        print("selecting row " +str(y))
        top = state.zone.top() + y / state.grid.h  * state.zone.h
        state.zone.y = top + 0.5 * state.zone.h / state.grid.h
        state.zone.h = max(state.grid.h, state.zone.h / state.grid.h)

        # switch to col selection mode
        state.grid_nav = "col"

    return annotate(upd, "row_select " + str(row))

def col_select(x):
    """Select the specified col"""

    def upd(state, x=x):
        """col_select action"""
        print("selecting col " +str(x))
        left = state.zone.left() + x / state.grid.w  * state.zone.w
        state.zone.x = left + 0.5 * state.zone.w / state.grid.w
        state.zone.w = max(state.grid.w, state.zone.w / state.grid.w)

        warp(state)

        state.grid_nav = None
        grid_nav(state)


    return annotate(upd, "col_select " + str(x))

# dart navigation
def dart_nav(state):
    """Start dart grid navigation"""

    # switch to grid mode
    global dart_nav_chars
    w = len(dart_nav_chars[0])
    h = len(dart_nav_chars)
    grid(w, h)(state)

    # switch to dart selection mode
    state.grid_nav = "dart"



def history_back(state):
    """Roll back the navigation to the state before the last key stroke"""

    state.nav.undo()

def record_mark(state):
    """Save the current pointer position as a mark
    associated with the next pressed letter"""

    state.enter_mode(MarkMode(state.nav, conf, record=True))

def apply_mark(state):
    """On the next pressed letter, move the zone
    and the pointer to the position saved for that letter"""

    state.enter_mode(MarkMode(state.nav, conf))


# annotate functions without arguments
for i in [warp, start, clear, info, exit_mode, end, grid_nav, history_back, full]:
    i = annotate(i, i.__name__)


################################################################################
# configuration
################################################################################

conf_dir = "~/.yakm/"

conf_dir = expanduser(conf_dir)
pathlib.Path(conf_dir).mkdir(parents=True, exist_ok=True)

conf = {
    "u": [move_left(0.5), warp],
    "e": [move_right(0.5), warp],
    "i": [move_up(0.5), warp],
    "a": [move_down(0.5), warp],

    "n": [click(1)],
    "r": [click(2)],
    "t": [click(3)],
    "PageUp": [click(4)],
    "PageDown": [click(5)],


    "shift+n": [drag(1)],
    "shift+r": [drag(2)],
    "shift+t": [drag(3)],

    "b" : [grid(9, 9), grid_nav],
    "m" : [record_mark],
    "period" : [apply_mark],

    ",": [cursorzoom(342, 192)],
    "mod4+r": [full],
    "p": [enlarge(1.5)],
    "mod4+a": [start, cursorzoom(342, 192), grid(9, 9), grid_nav, apply_mark],
    "mod4+e": [start, cursorzoom(342, 192), grid(9, 9), grid_nav],
    "mod4+s": [start, full, dart_nav],
    "s": [dart_nav],

    "ctrl+shift+i": [info],

    "o": [history_back, warp],
    "z": [exit_mode],
    "Escape": [end],
}

# QWERTY layout
grid_nav_chars = ["q", "w", "e", "r", "t", "y", "u", "i", "i", "o", "p"]

# Neo2 layout
grid_nav_chars = ["x", "v", "l", "c", "w", "k", "h", "g", "f", "q"]

dart_nav_chars = [
    ["1", "2", "3", "4", "6", "7", "8", "9", "0"],
    ["x", "v", "l", "c", "k", "h", "g", "f", "q"],
    ["u", "i", "a", "e", "s", "n", "r", "t", "d"],
    ["ü", "ö", "ä", "p", "b", "m", ", ", ".", "j"],
]


class Size:
    """Class storing the size of a zone / window / screen /..."""
    def __init__(self):
        self.w = 0
        self.h = 0

    def __str__(self):
        return "size: " + str(self.w) + "," + str(self.h)

class State:
    """This class tracks the state of the navigation. This includes
    - the current zone: the region that the user selected
    - the modes: a stack of modes
    - the grid: how many rows and columns
    - whether the user is dragging
    """

    def __init__(self, nav):
        # references
        self.nav = nav

        # info
        self.screen = Size()
        self.screen.w = nav.input.w
        self.screen.h = nav.input.h

        # state
        self.mode = []
        self.zone = draw.Zone()
        self.grid = Size()
        self.grid.w = 1
        self.grid.h = 1
        self.drag = False
        self.grid_nav = None # or "row", or "col"

    def __str__(self):
        r = "state: \n" + \
            "  zone " + str(self.zone) + \
            "  grid " + str(self.grid) + \
            " mode " + ",".join([str(i.__class__.__name__) for i in self.mode])
        return r

    def copy(self):
        """Create a copy of this state."""

        c = State(self.nav)
        c.screen = self.screen
        c.mode = self.mode[:]
        exclude = set(dir(State))
        exclude.update(["nav", "screen", "mode"])

        for attr in dir(self):
            if attr in exclude:
                continue
            setattr(c, attr, copy.deepcopy(getattr(self, attr)))
        return c

    def enter_mode(self, mode):
        """Enter a mode"""

        self.nav.vis.enable()
        self.nav.grab_keyboard()

        self.mode += [mode]
        mode.enter(self)

    def exit_mode(self, all=False):
        """Leave the currently active mode"""

        while self.mode:
            self.mode[-1].exit(self)
            self.mode = self.mode[:-1]
            if not all:
                break

        if self.mode:
            self.mode[-1].enter(self)
        else:
            self.nav.vis.disable()
            self.nav.vis.refresh()
            self.nav.ungrab_keyboard()

    def update(self, undoable=True):
        """Update the visualization and set the right mode"""

        if self.mode:
            self.mode[-1].apply(self)

        if undoable:
            self.nav.do(self)

    #
    def settings(self, inst, default={}):
        """Save settings for a mode based on its class name."""

        if not hasattr(self, "_settings"):
            self._settings = {}

        name = inst.__class__.__name__
        if not name in self._settings:
            self._settings[name] = default

        return self._settings[name]


class Mode:
    """A mode is a mapping from keys to actions with a visualization.
    The mapping is active if the mode is active.
    Modes can be nested."""

    def __init__(self, nav, conf):
        self.nav = nav
        self.conf = conf
        pass

    def apply(self, state):
        """Draw visualization of this mode on the screen"""

        state.nav.draw(state.zone)

    def get_bindings(self, _state, bindings={}):
        """Calculate the mapping from a key to an action for this mode.
        The dict 'bindings' contains binding of outer modes.
        If the mode allows to use functions from the outer modes,
        those should also appear in the returned mapping."""

        bindings.update(self.conf)
        return bindings

    def update_bindings(self, state):
        """Activate the key bindings of this mode"""

        bindings = {}
        for mode in state.mode:
            bindings = mode.get_bindings(state, bindings)

        for key, action in bindings.items():
            # use state of navigation, so that we can undo actions
            def fn(action=action, nav=state.nav):
                """wrap action in a lambda function"""

                for act in action:
                    act(nav.state)

                if not history_back in action:
                    nav.state.update()

            fn = annotate(fn, get_cmd(action))
            state.nav.input.register_key(key, fn)

    def enter(self, state):
        """This method is called when the user activates this mode"""

        self.update_bindings(state)
        state.nav.draw(state.zone)

    def exit(self, state):
        """This method is called when the user de-activates this mode"""

        # only unregister my keybindings
        # other keybindings are restored when entering previous mode
        for key, action in self.get_bindings(state).items():
            if not start in action:
                state.nav.input.unregister_key(key)

        state.nav.undraw()


class GridMode(Mode):
    """The grid mode draws a grid on the screen.
    Pressing a button restricts the current zone to a row, column or cell.

    There are two sub-modes:
    - normal: pressing a key in grid_nav_chars first selects the row, then the column
    - dart: pressing a key in dart_nav_chars directly jumps to the corresponding cell
    """

    def __init__(self, nav, conf):
        super().__init__(nav, conf)

    def get_bindings(self, state, bindings={}):
        new = {}
        if state.grid_nav == "row":
            print("apply row bindings")
            for i, c in enumerate(grid_nav_chars):
                new[c] = [row_select(i)]


        if state.grid_nav == "col":
            print("apply col bindings")
            for i, c in enumerate(grid_nav_chars):
                new[c] = [col_select(i)]

        if state.grid_nav == "dart":
            print("apply dart bindings")
            for y, row in enumerate(dart_nav_chars):
                for x, key in enumerate(row):
                    # uggly hack
                    new[key] = [cell_select(x, y), warp]

        bindings.update(new)
        return bindings

    def apply(self, state):
        # draw grid
        state.nav.undraw()
        enabled = state.nav.vis.active

        # do we need this?
        if not enabled:
            return

        state.nav.vis.disable()
        self.update_bindings(state)

        # draw horizontal lines
        for gy, first_y, last_y in iter_first_last(range(state.grid.h+1)):
            # avoid drawing lines in grid if grid is very small
            horizontal_until_x = state.zone.right()
            if state.zone.w < state.grid.w * 30 and not first_y and not last_y:
                horizontal_until_x = state.zone.left() - 10

            if first_y or last_y or state.grid_nav is None or \
                    state.grid_nav == "row" or state.grid_nav == "dart":

                h = draw.Line()
                h.x1 = state.zone.left()
                h.x2 = horizontal_until_x

                h.y1 = state.zone.top() + gy * state.zone.h / state.grid.h
                h.y2 = h.y1
                state.nav.draw(h)

        # draw vertical lines
        for gx, first_x, last_x in iter_first_last(range(state.grid.w+1)):
            # avoid drawing lines in grid if grid is very small
            vertical_until_y = state.zone.bottom()
            if state.zone.h < state.grid.h * 30 and not first_x and not last_x:
                vertical_until_y = state.zone.top() - 10

            if first_x or last_x or state.grid_nav is None or \
                    state.grid_nav == "col" or state.grid_nav == "dart":

                v = draw.Line()
                v.x1 = state.zone.left() + gx * state.zone.w / state.grid.w
                v.x2 = v.x1

                v.y1 = state.zone.top()
                v.y2 = vertical_until_y
                state.nav.draw(v)

        if state.grid_nav == "row":
            delta = state.zone.h / state.grid.h
            for gy in range(state.grid.h):
                l = draw.Label()
                l.x = state.zone.left() + 0.5 * state.zone.w / state.grid.w
                l.y = state.zone.top() + (gy + 0.5) * delta
                l.text = str(grid_nav_chars[gy])

                if l.size(state.nav.vis)[1] > delta:
                    break
                state.nav.draw(l)

        if state.grid_nav == "col":
            delta = state.zone.w / state.grid.w
            for gx in range(state.grid.w):
                l = draw.Label()
                l.x = state.zone.left() + (gx + 0.5) * delta
                l.y = state.zone.top() + 0.5 * state.zone.h / state.grid.h
                l.text = str(grid_nav_chars[gx])

                if l.size(state.nav.vis)[0] > delta:
                    break
                state.nav.draw(l)

        if state.grid_nav == "dart":
            delta_x = state.zone.w / state.grid.w
            delta_y = state.zone.h / state.grid.h
            l = draw.Label()
            l.text = "Ig"
            if max(l.size(state.nav.vis)) < min(delta_x, delta_y):
                for gx in range(state.grid.w):
                    for gy in range(state.grid.h):
                        l = draw.Label()
                        l.x = state.zone.left() + (gx + 0.5) * delta_x
                        l.y = state.zone.top() + (gy + 0.5) * delta_y
                        l.text = str(dart_nav_chars[gy][gx])
                        state.nav.draw(l)

        state.nav.vis.enable()

class MarkMode(Mode):
    """The mark mode allows the user to "bookmark" the current pointer position as a letter.

    There are two sub-modes:
    - record: pressing a letter saves the current position
    - otherwise: pressing a letter moves the pointer to the saved position
    """

    def __init__(self, nav, conf, record=False):
        self.nav = nav
        _marks = self.marks()

        if not _marks:
            try:
                with open(conf_dir + "marks", "r") as f:
                    _marks.update(json.loads(f.read()))
            except FileNotFoundError:
                pass

        conf = {}
        if record:
            # currently only alphabetic marks
            for key in list(string.ascii_lowercase):
                def register(state, key=key):
                    """register a mark for the current pointer position"""

                    _marks = self.marks()

                    win = self.nav.input.window()
                    msg = ("enter a filter for mark " + str(key) + "\n" +
                           "leave empty for global mark" + "\n\n" +
                           str(win).lower()
                          )
                    cond = nav.input_dialog(msg) or ""

                    if cond:
                        _marks[cond][key] = (state.zone.x, state.zone.y)

                register = annotate(register, "register '" + key + "'")
                conf[key] = [register, self.save, exit_mode]
        else:
            for key, coord in self.bindings().items():
                conf[key] = [move_to(coord[0], coord[1]), warp, exit_mode]

        super().__init__(nav, conf)

    def marks(self):
        """mapping from condition -> key -> action"""
        return self.nav.state.settings(self, defaultdict(lambda: {}))

    def bindings(self):
        """get mapping from key -> action"""

        result = {}
        win = str(self.nav.input.window()).lower()
        for cond, bindings in self.marks().items():
            if not cond.lower() in str(win):
                continue
            result.update(bindings)
        print(result)
        return result

    def apply(self, state):
        # draw grid
        state.nav.undraw()
        enabled = state.nav.vis.active
        state.nav.vis.disable()

        bindings = self.bindings()

        if not bindings:
            l = draw.Label()
            l.x = state.screen.w / 2
            l.y = state.screen.h / 2
            l.text = "no marks"
            state.nav.draw(l)

        for key, coord in bindings.items():
            l = draw.Label()
            l.x = coord[0]
            l.y = coord[1]
            l.text = key
            state.nav.draw(l)

        if enabled:
            state.nav.vis.enable()

    def save(self, _state):
        """save the current marks in a file in the config dir"""
        with open(conf_dir + "marks", "w") as f:
            f.write(json.dumps(self.marks(), indent=4, sort_keys=True))




class Navigator:
    """This class coordinates the input, the drawing, and the history.
    It is the entry point of YAKM"""

    def __init__(self):
        # components
        self.vis = draw.Drawing()
        self.input = input.Input()

        # state
        self.state = State(self)
        self.history = []

        # functions
        self.move = self.input.move
        self.click = self.input.click
        self.pointer = self.input.pointer

        self.key_bindings = self.input.key_bindings
        self.grab_keyboard = self.input.grab_keyboard
        self.ungrab_keyboard = self.input.ungrab_keyboard

        self.draw = self.vis.draw
        self.undraw = self.vis.undraw


        for key, action in conf.items():
            if start in action:
                def upd(self=self, action=action):
                    """start command"""

                    self.state.enter_mode(Mode(self, conf))
                    for act in action:
                        act(self.state)

                self.input.register_key(key, upd, _global=True)


    def __del__(self):
        self.vis.stop()

    def do(self, state):
        """Add the current step to the history"""
        print("do " + str(state))
        # TODO: only add if change, something like
        #   if len(self.history) == 0: state != self.history[-1]:
        self.history.append(state.copy())


    def undo(self):
        """Undo last action, i.e., go back one step in history"""
        if len(self.history) > 1:
            del self.history[-1]
            self.state = self.history[-1].copy()
            self.state.update(undoable=False)

            print("roling back to state " + str(self.state))

    def input_dialog(self, msg=""):
        """Ask the user to type in text"""

        enabled = self.vis.active
        self.vis.disable()
        self.vis.refresh()
        grabbing = self.input.grabbing
        self.ungrab_keyboard()

        text = input_dialog(msg)

        if enabled:
            self.vis.enable()
        if grabbing:
            self.grab_keyboard()

        return text


if __name__ == '__main__':
    Navigator()
    print("started ...")

