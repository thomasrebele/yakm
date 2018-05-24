#!/usr/bin/env python3


from draw import *
from time import sleep
import copy
import string
import json

import pathlib
from os.path import expanduser

from input import *

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

def annotate(fn, cmd):
    fn.cmd = str(cmd)
    return fn

def get_cmd(x):
    if callable(x):
        try:
            return x.cmd
        except:
            if not x.__name__: return str(x)
            return x.__name__

    if type(x) == list:
        cmds = [get_cmd(fn) for fn in x]
        return ", ".join(cmds)


# https://stackoverflow.com/a/1633483/1562506
def iter_first_last(it):
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
    state.nav.move(state.zone.x, state.zone.y)

def start(state):
    ### TODO: enter mode
    state.enter_mode(Mode(state.nav, conf))
    state.zone.w = state.screen.w
    state.zone.h = state.screen.h
    state.zone.x = state.screen.w/2
    state.zone.y = state.screen.h/2

    state.nav.grab_keyboard()

# suspend current mode
def suspend(state):
    # TODO
    pass

# exit current mode
def exit_mode(state):
    state.exit_mode()

# exit all modes
def end(state):
    state.exit_mode(all=True)


def clear(state):
    for k in state.nav.key_bindings():
        state.nav.input.unregister_key(k)


def info(state):
    print("bindings:")
    for key, action in state.nav.key_bindings().items():
        print("    key " + str(key) + " -> " + str(get_cmd(action)))
    win = state.nav.input.window()
    print("focused window: " + str(win))


def ignore(state):
    pass


def click(button):
    return annotate(lambda state: state.nav.click(button), "click " + str(button))

def drag(button):
    def upd(state, button=button):
        actions = ["release"] if state.drag else ["press"]
        state.drag = not state.drag
        state.nav.click(button, actions=actions)
    return annotate(upd, "drag " + str(button))

def move_to(x, y):
    def upd(state, x=x, y=y):
        state.zone.x = x
        state.zone.y = y
    return annotate(upd, "move_to " + str(x) + " " + str(y))

def move_left(ratio):
    def upd(state, ratio=ratio):
        state.zone.x = max(0, state.zone.x - state.zone.w * ratio)
    return annotate(upd, "move_left " + str(ratio))

def move_right(ratio):
    def upd(state, ratio=ratio):
        state.zone.x = min(state.screen.w, state.zone.x + state.zone.w * ratio)
    return annotate(upd, "move_right " + str(ratio))

def move_up(ratio):
    def upd(state, ratio=ratio):
        state.zone.y = max(0, state.zone.y - state.zone.h * ratio)
    return annotate(upd, "move_up " + str(ratio))

def move_down(ratio):
    def upd(state, ratio=ratio):
        state.zone.y = min(state.screen.h, state.zone.y + state.zone.h * ratio)
    return annotate(upd, "move_down " + str(ratio))

def cursorzoom(w, h):
    def upd(state, w=w, h=h):
        state.zone.w = w
        state.zone.h = h
        p = state.nav.pointer()
        state.zone.x = p.x
        state.zone.y = p.y
    return annotate(upd, "cursorzoom " + str(w) + " " + str(h))

def enlarge(ratio):
    def upd(state, ratio=ratio):
        state.zone.w *= ratio
        state.zone.h *= ratio
    return annotate(upd, "enlarge " + str(ratio))

def grid(w, h):
    def upd(state, w=w, h=h):
        state.grid.w = w
        state.grid.h = h
        state.enter_mode(GridMode(state.nav, conf))

    return annotate(upd, "grid " + str(w) + " " + str(h))

def cell_select(x, y):
    def upd(state, x=x, y=y):
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
    global grid_nav_chars

    # switch to row selection mode
    state.grid_nav = "row"


def row_select(y):
    def upd(state, y=y):
        print("selecting row " +str(y))
        top = state.zone.top() + y / state.grid.h  * state.zone.h
        state.zone.y = top + 0.5 * state.zone.h / state.grid.h
        state.zone.h = max(state.grid.h, state.zone.h / state.grid.h)

        # switch to col selection mode
        state.grid_nav = "col"

    return annotate(upd, "row_select " + str(y))

def col_select(x):
    def upd(state, x=x):
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
    global dart_nav_chars

    # switch to grid mode
    w = len(dart_nav_chars[0])
    h = len(dart_nav_chars)
    grid(w,h)(state)

    # switch to dart selection mode
    state.grid_nav = "dart"



def history_back(state):
    state.nav.undo()

def record_mark(state):
    state.enter_mode(MarkMode(state.nav, conf, record=True))

def apply_mark(state):
    state.enter_mode(MarkMode(state.nav, conf))


# annotate functions without arguments
for i in [warp, start, clear, info, exit_mode, end, grid_nav, history_back]:
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


    "shift+n": [drag(1)],
    "shift+r": [drag(2)],
    "shift+t": [drag(3)],

    "h" : [cell_select(0,2)],
    "b" : [grid_nav],
    "m" : [record_mark],
    "period" : [apply_mark],

    "k": [cursorzoom(342, 192)],
    "p": [enlarge(1.5)],
    "mod4+a": [start, cursorzoom(342, 192), grid(9,9), grid_nav, apply_mark],
    "mod4+e": [start, cursorzoom(342, 192), grid(9,9), grid_nav],
    "mod4+n": [start, dart_nav],
    #"mod4+shift+a": [start, grid(9,9), grid_nav],

    "s": [info],
    "ctrl+shift+i": [info],
    #"c": [clear],

    "o": [history_back],
    "z": [exit_mode],
    "Escape": [end],
}

# QWERTY layout
grid_nav_chars = ["q", "w", "e", "r", "t", "y", "u", "i", "i", "o", "p"]

# Neo2 layout
grid_nav_chars = ["x", "v", "l", "c", "w", "k", "h", "g", "f", "q"]

dart_nav_chars = [
        ["1","2","3","4","6","7","8","9","0"],
        ["x","v","l","c","k","h","g","f","q"],
        ["u","i","a","e","s","n","r","t","d"],
        ["ü","ö","ä","p","b","m",",",".","j"],
    ]


class Size:
    def __init__(self):
        w = 0
        h = 0

    def __str__(self):
        return "size: " + str(self.w) + "," + str(self.h)

class State:
    def __init__(self, nav):
        # references
        self.nav = nav

        # info
        self.screen = Size()
        self.screen.w = nav.input.w
        self.screen.h = nav.input.h

        # state
        self.mode = []
        self.zone = Zone()
        self.grid = Size()
        self.grid.w = 1
        self.grid.h = 1
        self.drag = False
        self.grid_nav = None # or "row", or "col"

    def copy(self):
        c = State(self.nav)
        c.screen = self.screen
        c.mode = self.mode[:]
        exclude = set(dir(State))
        exclude.update(["nav", "screen", "mode"])

        for attr in dir(self):
            if attr in exclude: continue
            setattr(c, attr, copy.deepcopy(getattr(self, attr)))
        return c

    def __str__(self):
        return "state: \n" + "  " + str(self.zone) + "  grid " + str(self.grid) + " mode " + ",".join([str(i.__class__.__name__) for i in self.mode])

    def enter_mode(self, mode):
        self.nav.vis.enable()
        self.nav.grab_keyboard()

        self.mode += [mode]
        mode.enter(self)

    def exit_mode(self, all=False):
        while len(self.mode) > 0:
            self.mode[-1].exit(self)
            self.mode = self.mode[:-1]
            if not all: break

        if len(self.mode) > 0:
            self.mode[-1].enter(self)
        else:
            self.nav.vis.disable()
            self.nav.vis.refresh()
            self.nav.ungrab_keyboard()

    def update(self, undoable=True):
        if len(self.mode) > 0:
            self.mode[-1].apply(self)

        if undoable:
            self.nav.do(self)

    # save settings for class
    def settings(self, inst):
        if not hasattr(self, "_settings"):
            self._settings = {}

        name = inst.__class__.__name__
        if not name in self._settings:
            self._settings[name] = {}

        return self._settings[name]


class Mode:
    def __init__(self, nav, conf):
        self.nav = nav
        self.conf = conf
        pass

    def apply(self, state):
        state.nav.draw(state.zone)

    # this method is called also for non-active modes
    # the dict 'bindings' contains binding of outer modes
    def get_bindings(self, state, bindings={}):
        bindings.update(self.conf)
        return bindings

    def update_bindings(self, state):
        bindings = {}
        for mode in state.mode:
            bindings = mode.get_bindings(state, bindings)

        for key, action in bindings.items():
            # use state of navigation, so that we can undo actions
            def fn(action=action, nav=state.nav):
                for act in action:
                    act(nav.state)

                if not history_back in action:
                    nav.state.update()

            fn = annotate(fn, get_cmd(action))
            state.nav.input.register_key(key, fn)

    def enter(self, state):
        self.update_bindings(state)
        state.nav.draw(state.zone)

    def exit(self, state):
        # only unregister my keybindings
        # other keybindings are restored when entering previous mode
        for key, action in self.get_bindings(state).items():
            if not start in action:
                state.nav.input.unregister_key(key)

        state.nav.undraw()


class GridMode(Mode):
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
                    new[key] = [cell_select(x,y), warp]

            new["Escape"] = [exit_mode]

        bindings.update(new)
        return bindings

    def apply(self, state):
        # draw grid
        state.nav.undraw()
        enabled = state.nav.vis.active

        # do we need this?
        if not enabled: return

        state.nav.vis.disable()
        self.update_bindings(state)

        # draw horizontal lines
        for gy, first_y, last_y in iter_first_last(range(state.grid.h+1)):
            # avoid drawing lines in grid if grid is very small
            horizontal_until_x = state.zone.right()
            if state.zone.w < state.grid.w * 30 and not first_y and not last_y:
                horizontal_until_x = state.zone.left() - 10

            if first_y or last_y or state.grid_nav == None or state.grid_nav == "row" or state.grid_nav == "dart":
                h = Line()
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

            if first_x or last_x or state.grid_nav == None or state.grid_nav == "col" or state.grid_nav == "dart":
                v = Line()
                v.x1 = state.zone.left() + gx * state.zone.w / state.grid.w
                v.x2 = v.x1

                v.y1 = state.zone.top()
                v.y2 = vertical_until_y
                state.nav.draw(v)

        if state.grid_nav == "row":
            delta = state.zone.h / state.grid.h
            for gy in range(state.grid.h):
                l = Label()
                l.x = state.zone.left() + 0.5 * state.zone.w / state.grid.w
                l.y = state.zone.top() + (gy + 0.5) * delta
                l.text = str(grid_nav_chars[gy])

                if l.size(state.nav.vis)[1] > delta: break
                state.nav.draw(l)

        if state.grid_nav == "col":
            delta = state.zone.w / state.grid.w
            for gx in range(state.grid.w):
                l = Label()
                l.x = state.zone.left() + (gx + 0.5) * delta
                l.y = state.zone.top() + 0.5 * state.zone.h / state.grid.h
                l.text = str(grid_nav_chars[gx])

                if l.size(state.nav.vis)[0] > delta: break
                state.nav.draw(l)

        if state.grid_nav == "dart":
            delta_x = state.zone.w / state.grid.w
            delta_y = state.zone.h / state.grid.h
            l = Label()
            l.text = "Ig"
            if max(l.size(state.nav.vis)) < min(delta_x, delta_y):
                for gx in range(state.grid.w):
                    for gy in range(state.grid.h):
                        l = Label()
                        l.x = state.zone.left() + (gx + 0.5) * delta_x
                        l.y = state.zone.top() + (gy + 0.5) * delta_y
                        l.text = str(dart_nav_chars[gy][gx])
                        state.nav.draw(l)

        state.nav.vis.enable()

class MarkMode(Mode):
    def __init__(self, nav, conf, record = False):
        marks = nav.state.settings(self)
        if len(marks) == 0:
            try:
                with open(conf_dir + "marks", "r") as f:
                    marks.update(json.loads(f.read()))
            except FileNotFoundError:
                pass

        conf = {}
        if record:
            # currently only alphabetic marks
            for key in list(string.ascii_lowercase):
                def register(state, key=key):
                    marks = nav.state.settings(self)
                    marks[key] = (state.zone.x,state.zone.y)
                register = annotate(register, "register '" + key + "'")
                conf[key] = [register, self.save, exit_mode]
        else:
            for key, coord in marks.items():
                conf[key] = [move_to(coord[0], coord[1]), warp, exit_mode]

        super().__init__(nav, conf)

    def marks(self):
        return self.nav.state.settings(self)

    def apply(self, state):
        # draw grid
        state.nav.undraw()
        enabled = state.nav.vis.active
        state.nav.vis.disable()

        for key, coord in self.marks().items():
            l = Label()
            l.x = coord[0]
            l.y = coord[1]
            l.text = key
            state.nav.draw(l)

        if enabled: state.nav.vis.enable()

    def save(self, state):
        print("saving!")
        with open(conf_dir + "marks", "w") as f:
            f.write(json.dumps(self.marks()))




class Navigator:
    def __init__(self):
        # components
        self.vis = Drawing()
        self.input = Input()

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
                def fn(self=self, action=action):
                    self.state.enter_mode(Mode(self, conf))
                    for act in action:
                        act(self.state)

                self.input.register_key(key, fn, _global=True)


    def __del__(self):
        self.vis.stop()

    def do(self, state):
        print("do " + str(state))
        # TODO: only add if change, something like if len(self.history) == 0: state != self.history[-1]:
        self.history.append(state.copy())


    def undo(self):
        if len(self.history) > 1:
            del self.history[-1]
            self.state = self.history[-1].copy()
            self.state.update(undoable=False)

            print("roling back to state " + str(self.state))


if __name__ == '__main__':
    n = Navigator()

    print("started ...")




