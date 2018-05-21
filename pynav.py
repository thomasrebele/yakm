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


# todo

# start
# end
# clear: remove keybindings
# daemonize: execute in background
# grid 2x3
# grid-nav off
# grid-nav toggle
# cell-select 1x3
# drag 1
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

# annotate functions without arguments
for i in [warp, start, clear, info]:
    i = annotate(i, i.__name__)


################################################################################
# configuration
################################################################################

conf = {
    #"u": [move_left(0.5), warp],
    #"e": [move_right(0.5), warp],
    #"i": [move_up(0.5), warp],
    #"a": [move_down(0.5), warp],

    "u": [ignore],
    "e": [ignore],
    "i": [ignore],
    "a": [ignore],


    "n": [click(1)],
    "r": [click(2)],
    "t": [click(3)],

    "h": [cursorzoom(342, 192)],
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

    def enter(self, state):
        for key, action in conf.items():
            def fn(action=action, state=state):
                for act in action:
                    act(state)

            fn = annotate(fn, get_cmd(action))
            state.register_key(key, fn)

        state.draw(state.zone)
        self.state = state

    def exit(self, state):
        for key in conf:
            state.unregister_key(key)

        state.undraw(state.zone)

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

        self.draw = nav.o.draw
        self.undraw = nav.o.undraw
        self.pointer = nav.input.pointer

        # info
        self.screen = Size()
        self.screen.w = nav.input.w
        self.screen.h = nav.input.h

        # state
        self.zone = Zone()
        self.drag = False

class Navigator:
    def __init__(self):
        self.o = Drawing()
        self.input = Input()

        self.register_key = self.input.register_key
        self.unregister_key = self.input.unregister_key

        self.input.register_key("ctrl+shift+8", lambda: self.enter_mode(Mode(conf)))

        self.state = State(self)
        self.mode = []

    def __del__(self):
        self.o.stop()

    def enter_mode(self, mode):
        self.o.enable()
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
            self.o.disable()
            self.input.unregister_key("z")
            self.input.unregister_key("Escape")





if __name__ == '__main__':
    n = Navigator()

    print("started ...")

    try:
        sleep(100)
    except KeyboardInterrupt:
        sys.exit()



