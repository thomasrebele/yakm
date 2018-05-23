#!/usr/bin/env python3


from draw import *
from time import sleep
import copy
import string

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
    if type(x) == type(lambda: x):
        try:
            return x.cmd
        except:
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
        state.nav.unregister_key(k)


def info(state):
    print("bindings:")
    for key, action in state.nav.key_bindings().items():
        print("    key " + str(key) + " -> " + str(get_cmd(action)))

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
    def upd(state, x=x-1, y=y-1):
        if x > state.grid.w or y > state.grid.h:
            return

        left = state.zone.left() + x / state.grid.w  * state.zone.w
        top = state.zone.top() + y / state.grid.h  * state.zone.h

        state.zone.w = state.zone.w / state.grid.w
        state.zone.h = state.zone.h / state.grid.h
        state.zone.x = left + state.zone.w/2
        state.zone.y = top + state.zone.h/2

    return annotate(upd, "cell_select " + str(x) + " " + str(y))

# grid navigation
def grid_nav(state):
    global grid_nav_chars

    # prepare for selecting rows
    state.grid_nav = "row"
    for i, c in enumerate(grid_nav_chars):
        state.nav.register_key(c, lambda state=state, i=i: row_select(i)(state))

    state.update()


def row_select(y):
    def upd(state, y=y):
        print("selecting row " +str(y))
        top = state.zone.top() + y / state.grid.h  * state.zone.h
        state.zone.y = top + 0.5 * state.zone.h / state.grid.h
        state.zone.h /= state.grid.h

        # prepare for selecting cols
        state.grid_nav = "col"
        for i, c in enumerate(grid_nav_chars):
            state.nav.register_key(c, lambda state=state, i=i: col_select(i)(state))

        state.update()

    return annotate(upd, "row_select " + str(y))

def col_select(x):
    def upd(state, x=x):
        print("selecting col " +str(x))
        left = state.zone.left() + x / state.grid.w  * state.zone.w
        state.zone.x = left + 0.5 * state.zone.w / state.grid.w
        state.zone.w /= state.grid.w

        warp(state)

        state.grid_nav = None

        grid_nav(state)


    return annotate(upd, "col_select " + str(x))

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

    "h" : [cell_select(1,3)],
    "b" : [grid_nav],
    "m" : [record_mark],
    "period" : [apply_mark],

    "k": [cursorzoom(342, 192)],
    "p": [enlarge(1.5)],
    "ctrl+shift+h": [start, grid(9,9), grid_nav],
    "ctrl+shift+g": [start, cursorzoom(342, 192), grid(9,9), grid_nav],
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


class Size:
    def __init__(self):
        w = 0
        h = 0

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
        return "state: \n" + "  " + str(self.zone)

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


        if len(self.mode) == 0:
            self.nav.vis.disable()
            self.nav.vis.refresh()
            self.nav.ungrab_keyboard()

    def update(self, undoable=True):
        if len(self.mode) > 0:
            self.mode[-1].apply(self)

        if undoable:
            self.nav.do(self)


class Mode:
    def __init__(self, nav, conf):
        self.nav = nav
        self.conf = conf
        pass

    def apply(self, state):
        state.nav.draw(state.zone)

    def enter(self, state):
        print("enter " + str(self))
        self.prev_bindings = state.nav.key_bindings()

        for key, action in self.conf.items():
            # use state of navigation, so that we can undo actions
            def fn(action=action, nav=state.nav):
                for act in action:
                    act(nav.state)

                if not history_back in action:
                    nav.state.update()

            fn = annotate(fn, get_cmd(action))
            print("   register " + str(key) + " -> " + get_cmd(fn))
            state.nav.register_key(key, fn)

        state.nav.draw(state.zone)
        self.state = state

    def exit(self, state):
        for key, action in conf.items():
            if not start in action:
                state.nav.unregister_key(key)

        for key, action in self.prev_bindings.items():
            state.nav.register_key(key, action)

        state.nav.undraw()


class GridMode(Mode):
    def __init__(self, nav, conf):
        super().__init__(nav, conf)

    def apply(self, state):
        # draw grid
        state.nav.undraw()
        enabled = state.nav.vis.active
        state.nav.vis.disable()

        print("grid nav " + str(state.grid_nav))

        for gx, first_x, last_x in iter_first_last(range(state.grid.w+1)):
            for gy, first_y, last_y in iter_first_last(range(state.grid.h+1)):
                if first_y or last_y or state.grid_nav == None or state.grid_nav == "row":
                    # horizontal
                    h = Line()
                    h.x1 = state.zone.left() + gx * state.zone.w / state.grid.w
                    h.x2 = state.zone.right()

                    h.y1 = state.zone.top() + gy * state.zone.h / state.grid.h
                    h.y2 = h.y1
                    state.nav.draw(h)

                if first_x or last_x or state.grid_nav == None or state.grid_nav == "col":
                    # vertical
                    v = Line()
                    v.x1 = state.zone.left() + gx * state.zone.w / state.grid.w
                    v.x2 = v.x1

                    v.y1 = state.zone.top() + gy * state.zone.h / state.grid.h
                    v.y2 = state.zone.bottom()
                    state.nav.draw(v)

        if state.grid_nav == "row":
            for gy in range(state.grid.h):
                l = Label()
                l.x = state.zone.left() + 0.5 * state.zone.w / state.grid.w
                l.y = state.zone.top() + (gy + 0.5) * state.zone.h / state.grid.h
                l.text = str(grid_nav_chars[gy])
                state.nav.draw(l)

        if state.grid_nav == "col":
            for gx in range(state.grid.w):
                l = Label()
                l.x = state.zone.left() + (gx + 0.5) * state.zone.w / state.grid.w
                l.y = state.zone.top() + 0.5 * state.zone.h / state.grid.h
                l.text = str(grid_nav_chars[gx])
                state.nav.draw(l)


        if enabled: state.nav.vis.enable()

class MarkMode(Mode):
    def __init__(self, nav, conf, record = False):
        if not hasattr(nav, "mark"):
            nav.mark = {"a": (40, 100), "b": (500, 700)}

        conf = {}
        if record:
            # currently only alphabetic marks
            for key in list(string.ascii_lowercase):
                def register(state, key=key, mark=nav.mark):
                    mark[key] = (state.zone.x,state.zone.y)
                register = annotate(register, "register '" + key + "'")
                conf[key] = [register, exit_mode]
        else:
            for key, coord in nav.mark.items():
                conf[key] = [move_to(coord[0], coord[1]), warp, exit_mode]

        super().__init__(nav, conf)


    def apply(self, state):
        # draw grid
        state.nav.undraw()
        enabled = state.nav.vis.active
        state.nav.vis.disable()

        for key, coord in self.nav.mark.items():
            l = Label()
            l.x = coord[0]
            l.y = coord[1]
            l.text = key
            state.nav.draw(l)

        if enabled: state.nav.vis.enable()




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

        self.register_key = self.input.register_key
        self.unregister_key = self.input.unregister_key

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
        # TODO: only add if change, something like if len(self.history) == 0: state != self.history[-1]:
        print()
        print("--do step! zone " + str(self.state.zone))
        self.history.append(state.copy())
        for i in self.history:
            print("    " + str(i.zone))


    def undo(self):
        if len(self.history) > 1:
            print()
            print("undo step! zone " + str(self.state.zone))
            del self.history[-1]
            self.state = self.history[-1].copy()
            print("     after zone " + str(self.state.zone))

            self.state.update(undoable=False)
            for i in self.history:
                print("    " + str(i.zone))


if __name__ == '__main__':
    n = Navigator()

    print("started ...")




