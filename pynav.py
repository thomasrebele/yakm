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



################################################################################
# actions
################################################################################

def warp(state):
    state.move(state.zone.x, state.zone.y)

def click(button):
    return lambda state: state.click(button)


def move_left(ratio):
    def upd(state, ratio=ratio):
        state.zone.x = max(0, state.zone.x - state.zone.w * ratio)
    return upd

def move_right(ratio):
    def upd(state, ratio=ratio):
        state.zone.x = min(state.screen.w, state.zone.x + state.zone.w * ratio)
    return upd

def move_up(ratio):
    def upd(state, ratio=ratio):
        state.zone.y = max(0, state.zone.y - state.zone.h * ratio)
    return upd

def move_down(ratio):
    def upd(state, ratio=ratio):
        state.zone.y = min(state.screen.h, state.zone.y + state.zone.h * ratio)
    return upd

def cursorzoom(w, h):
    def upd(state, w=w, h=h):
        state.zone.w = w
        state.zone.h = h
        p = state.pointer()
        state.zone.x = p.x
        state.zone.y = p.y
    return upd

def enlarge(ratio):
    def upd(state, ratio=ratio):
        state.zone.w *= ratio
        state.zone.h *= ratio
    return upd





################################################################################
# configuration
################################################################################

conf = {
    "u": [move_left(0.5), warp],
    "e": [move_right(0.5), warp],
    "i": [move_up(0.5), warp],
    "a": [move_down(0.5), warp],
    "n": [click(1)],
    "r": [cursorzoom(20, 20)],
    "p": [enlarge(1.5)],
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
            state.register_key(key, None, fn)

        state.draw(state.zone)
        self.state = state

    def exit(self, state):
        for key in conf:
            state.unregister_key(key, None)

        state.undraw(state.zone)

class Size:
    w = 0
    h = 0

class State:
    def __init__(self, nav):
        self.move = nav.input.move
        self.click = nav.input.click

        self.zone = Zone()
        self.register_key = nav.register_key
        self.unregister_key = nav.unregister_key

        self.draw = nav.o.draw
        self.undraw = nav.o.undraw
        self.pointer = nav.input.pointer

        self.screen = Size()
        self.screen.w = nav.input.w
        self.screen.h = nav.input.h


class Navigator:
    def __init__(self):
        self.o = Drawing()
        self.input = Input()

        self.register_key = self.input.register_key
        self.unregister_key = self.input.unregister_key

        self.input.register_key("8", Ctrl|Shift, lambda: self.enter_mode(Mode(conf)))

        self.state = State(self)
        self.mode = []

    def __del__(self):
        self.o.stop()

    def enter_mode(self, mode):
        self.o.enable()
        self.mode += [mode]
        mode.enter(self.state)
        self.input.register_key("z", None, lambda: self.exit_mode())
        self.input.register_key("Escape", None, lambda: self.exit_mode(all=True))

    def exit_mode(self, all=False):
        while len(self.mode) > 0:
            self.mode[-1].exit(self.state)
            self.mode = self.mode[:-1]
            if not all: break

        if len(self.mode) == 0:
            self.o.disable()
            self.input.unregister_key("z", None)
            self.input.unregister_key("Escape", None)





if __name__ == '__main__':
    n = Navigator()

    print("started ...")

    try:
        sleep(100)
    except KeyboardInterrupt:
        sys.exit()



