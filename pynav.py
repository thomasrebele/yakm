#!/usr/bin/env python3


from draw import *
from time import sleep
import sys

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

# todo

# clear: remove keybindings
# daemonize: execute in background
# grid-nav off
# grid-nav toggle
# history-back

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
    state.nav.exit_mode()

# exit all modes
def end(state):
    state.nav.exit_mode(all=True)


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

    state.nav.update_mode()


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

        state.nav.update_mode()

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



# annotate functions without arguments
for i in [warp, start, clear, info, exit_mode, end, grid_nav]:
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

    "k": [cursorzoom(342, 192)],
    "p": [enlarge(1.5)],
    "ctrl+shift+7": [start, grid(9,9), grid_nav],
    "ctrl+shift+8": [start, cursorzoom(342, 192), grid(9,9), grid_nav],
    "x": [info],
    "ctrl+shift+i": [info],
    #"c": [clear],

    "z": [exit_mode],
    "Escape": [end],
}

# QWERTY layout
grid_nav_chars = ["q", "w", "e", "r", "t", "y", "u", "i", "i", "o", "p"]

# QWERTZ layout
grid_nav_chars = ["x", "v", "l", "c", "w", "k", "h", "g", "f", "q"]


class Mode:
    def __init__(self, conf):
        self.conf = conf
        pass

    def update(self, state):
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

        pass

    def enter(self, state):
        self.prev_bindings = state.nav.key_bindings()

        for key, action in conf.items():
            def fn(action=action, state=state):
                for act in action:
                    act(state)
                self.update(state)

            fn = annotate(fn, get_cmd(action))
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

class Size:
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
        self.zone = Zone()
        self.grid = Size()
        self.grid.w = 1
        self.grid.h = 1
        self.drag = False
        self.grid_nav = None # or "row", or "col"

class Navigator:
    def __init__(self):
        self.vis = Drawing()
        self.input = Input()

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
                    self.enter_mode(Mode(conf))
                    for act in action:
                        act(self.state)

                self.input.register_key(key, fn, _global=True)

        self.state = State(self)
        self.mode = []

    def __del__(self):
        self.vis.stop()

    def enter_mode(self, mode):
        self.vis.enable()
        self.input.grab_keyboard()

        self.mode += [mode]
        mode.enter(self.state)

    def exit_mode(self, all=False):
        while len(self.mode) > 0:
            self.mode[-1].exit(self.state)
            self.mode = self.mode[:-1]
            if not all: break


        if len(self.mode) == 0:
            self.vis.disable()
            self.vis.refresh()
            self.input.ungrab_keyboard()

    def update_mode(self):
        if len(self.mode) > 0:
            self.mode[-1].update(self.state)




if __name__ == '__main__':
    n = Navigator()

    print("started ...")

    try:
        sleep(100)
    except KeyboardInterrupt:
        sys.exit()



