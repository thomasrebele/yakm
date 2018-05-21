#!/usr/bin/env python3


from draw import *
from time import sleep
import sys

from input import *

# implemented actions:

# warp
# move-left .5
# move-up .5
# move-down .5
# move-right .5
# cursorzoom <w> <h>: center rectangle around cursor
# click 1
# grid 2x3
# drag 1

# todo

# start
# end
# clear: remove keybindings
# daemonize: execute in background
# grid-nav off
# grid-nav toggle
# cell-select 1x3
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

################################################################################
# actions
################################################################################

def warp(state):
    state.move(state.zone.x, state.zone.y)

def start(state):
    ### TODO: enter mode
    state.zone.w = state.screen.w
    state.zone.h = state.screen.h
    state.zone.x = state.screen.w/2
    state.zone.y = state.screen.h/2

    state.grab_keyboard()


def end(state):
    state.ungrab_keyboard()


def clear(state):
    for k in state.key_bindings():
        state.unregister_key(k)


def info(state):
    print("bindings:")
    for key, action in state.key_bindings().items():
        print("    key " + str(key) + " -> " + str(get_cmd(action)))

def ignore(state):
    pass


def click(button):
    return annotate(lambda state: state.click(button), "click " + str(button))

def drag(button):
    def upd(state, button=button):
        actions = ["release"] if state.drag else ["press"]
        state.drag = not state.drag
        state.click(button, actions=actions)
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
        p = state.pointer()
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
        print("set to " + str(x) + " " + str(y))
        left = state.zone.left() + x / state.grid.w  * state.zone.w
        top = state.zone.top() + y / state.grid.h  * state.zone.h

        state.zone.w = state.zone.w / state.grid.w
        state.zone.h = state.zone.h / state.grid.h
        state.zone.x = left + state.zone.w/2
        state.zone.y = top + state.zone.h/2

    return annotate(upd, "cell_select " + str(x) + " " + str(y))


# annotate functions without arguments
for i in [warp, start, clear, info]:
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

    "o" : [grid(3,3)],
    "h" : [cell_select(1,3)],

    "k": [cursorzoom(342, 192)],
    "p": [enlarge(1.5)],
    "ctrl+shift+7": [start],
    "x": [info],
    "ctrl+shift+i": [info],
    "c": [clear],
}



class Mode:
    def __init__(self, conf):
        self.conf = conf
        pass

    def update(self, state):
        # draw grid
        state.undraw()
        state.vis.disable()

        for gx in range(state.grid.w+1):
            for gy in range(state.grid.h+1):
                # horizontal
                h = Line()
                h.x1 = state.zone.left() + gx * state.zone.w / state.grid.w
                h.x2 = state.zone.right()

                h.y1 = state.zone.top() + gy * state.zone.h / state.grid.h
                h.y2 = h.y1
                state.draw(h)

                # vertical
                v = Line()

                v.x1 = state.zone.left() + gx * state.zone.w / state.grid.w
                v.x2 = v.x1

                v.y1 = state.zone.top() + gy * state.zone.h / state.grid.h
                v.y2 = state.zone.bottom()
                state.draw(v)

        state.vis.enable()

        pass

    def enter(self, state):
        for key, action in conf.items():
            def fn(action=action, state=state):
                for act in action:
                    act(state)
                self.update(state)

            fn = annotate(fn, get_cmd(action))
            state.register_key(key, fn)

        state.draw(state.zone)
        self.state = state

    def exit(self, state):
        for key in conf:
            state.unregister_key(key)

        state.undraw()

class Size:
    w = 0
    h = 0

class State:
    def __init__(self, nav):
        # functions
        self.move = nav.input.move
        self.click = nav.input.click

        self.register_key = nav.register_key
        self.unregister_key = nav.unregister_key
        self.key_bindings = nav.input.key_bindings
        self.grab_keyboard = nav.input.grab_keyboard
        self.ungrab_keyboard = nav.input.ungrab_keyboard

        self.vis = nav.vis
        self.draw = nav.vis.draw
        self.undraw = nav.vis.undraw
        self.pointer = nav.input.pointer

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

class Navigator:
    def __init__(self):
        self.vis = Drawing()
        self.input = Input()

        self.register_key = self.input.register_key
        self.unregister_key = self.input.unregister_key

        self.input.register_key("ctrl+shift+8", lambda: self.enter_mode(Mode(conf)))

        self.state = State(self)
        self.mode = []

    def __del__(self):
        self.vis.stop()

    def enter_mode(self, mode):
        self.vis.enable()
        self.input.grab_keyboard()

        self.mode += [mode]
        mode.enter(self.state)
        self.input.register_key("z", lambda: self.exit_mode())
        self.input.register_key("Escape", lambda: self.exit_mode(all=True))

    def exit_mode(self, all=False):
        while len(self.mode) > 0:
            self.mode[-1].exit(self.state)
            self.mode = self.mode[:-1]
            if not all: break

        if len(self.mode) == 0:
            self.vis.disable()
            self.input.ungrab_keyboard()
            self.input.unregister_key("z")
            self.input.unregister_key("Escape")





if __name__ == '__main__':
    n = Navigator()

    print("started ...")

    try:
        sleep(100)
    except KeyboardInterrupt:
        sys.exit()



