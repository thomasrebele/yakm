#!/usr/bin/env python3


from draw import *
from time import sleep
import sys
from os import _exit

from input import *
import threading



class Mode:
    pass

class NormalMode(Mode):
    def __init__(self, nav):
        self.nav = nav

    def enter(self):
        self.nav.register_key("u", None, self.move_left)
        self.nav.register_key("e", None, self.move_right)
        self.nav.register_key("i", None, self.move_up)
        self.nav.register_key("a", None, self.move_down)
        self.nav.register_key("n", None, self.warp)

        self.r = self.nav.o.rectangle()
        self.nav.o.draw(self.r)

    def exit(self):
        self.nav.unregister_key("u", None)
        self.nav.unregister_key("e", None)
        self.nav.unregister_key("i", None)
        self.nav.unregister_key("a", None)
        self.nav.unregister_key("n", None)

        self.nav.o.undraw(self.r)

    def move_left(self):
        self.r.x = max(int(-self.r.w/2), self.r.x - self.r.w)

    def move_right(self):
        self.r.x = min(int(self.nav.input.w-self.r.w/2), self.r.x + self.r.w)

    def move_up(self):
        self.r.y = max(int(-self.r.h/2), self.r.y - self.r.h)

    def move_down(self):
        self.r.y = min(int(self.nav.input.h-self.r.h/2), self.r.y + self.r.h)

    def warp(self):
        self.nav.input.move(self.r.x + int(self.r.w/2), self.r.y + int(self.r.h/2))
        self.nav.input.click(1)


class Navigator:
    def __init__(self):
        self.o = Drawing()
        self.input = Input()

        self.register_key = self.input.register_key
        self.unregister_key = self.input.unregister_key

        self.input.register_key("8", Ctrl|Shift, lambda: self.enter_mode(NormalMode(self)))

        self.mode = []
        self._mask = {"Control_L": False}

    def __del__(self):
        self.o.stop()
        print('stop')

    def mask(self):
        return set([k for k,v in self._mask.items() if v])

    def enter_mode(self, mode):
        self.o.enable()
        self.mode += [mode]
        mode.enter()
        self.input.register_key("z", None, lambda: self.exit_mode())
        self.input.register_key("Escape", None, lambda: self.exit_mode(all=True))

    def exit_mode(self, all=False):
        while len(self.mode) > 0:
            self.mode[-1].exit()
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



