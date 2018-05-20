#!/usr/bin/env python3


from draw import *
from time import sleep
import sys
from os import _exit

from pymouse import PyMouse
from pymouse import PyMouseEvent
from pykeyboard import PyKeyboard
from pykeyboard import PyKeyboardEvent
m = PyMouse()

import threading


#x_dim, y_dim = m.screen_size()
#m.click(500, 500, 1)

#k = PyKeyboard()
#k.type_string('Hello, World abc def!')

#m.move(0,0)

class MouseListener(PyMouseEvent):
    def click(self, x, y, button, pressed):
        print("x: " + str(x) + " y: " + str(y))

    def move(self, x, y):
        print "the mouse was moved to", x, y



class KeyListener(PyKeyboardEvent):
    def __init__(self, navigator):
        PyKeyboardEvent.__init__(self)
        self.navigator = navigator

    def tap(self, keycode, character, press):
        self.navigator.tap(keycode, character, press)


class Navigator:
    def __init__(self):
        self.o = Drawing()

        self.ml = MouseListener()
        self.ml.start()

        self.kl = KeyListener(self)
        self.kl.start()

        self.r = self.o.rectangle()
        self.o.draw(self.r)

        self._mask = {"Control_L": False}

    def __del__(self):
        self.o.stop()
        print('stop')

    def mask(self):
        return set([k for k,v in self._mask.items() if v])

    def tap(self, keycode, character, press):
        print("")
        print("received key event")
        print("tap " + str(keycode) + "  character: " + str(character) +  "  pressed " + str(press))

        if character in self._mask:
            self._mask[character] = press

        if character == "c" and self.mask() == set(["Control_L"]):
            self.o.stop()
            ### this does not work
            #self.kl.exit()
            #self.ml.exit()
            _exit(0)

        if character == "u":
            self.r.x -= 100
        elif character == "i":
            self.r.y -= 100
        elif character == "a":
            self.r.y += 100
        elif character == "e":
            self.r.x += 100

        elif character == "n":
            m.move(self.r.x, self.r.y)


        self.o.enable()


if __name__ == '__main__':
    n = Navigator()

    print("started ...")

    try:
        sleep(100)
    except KeyboardInterrupt:
        sys.exit()



