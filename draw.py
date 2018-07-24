#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import traceback
import threading
from time import sleep
from subprocess import call

class Action:
    def draw(self):
        print("WARNING: drawing action not implemented")
        pass

class Point:
    def __init__(self, x=0, y=0):
        self.x = x
        self.y = y

    def __str__(self):
        return "x:" + str(self.x) + " y:" + str(self.y)

class Rectangle(Action):
    def __init__(self, x=0, y=0, w=100, h=100):
        self.x = x
        self.y = y
        self.w = w
        self.h = h

class Line(Action):
    def __init__(self):
        self.x1 = 0
        self.y1 = 0
        self.x2 = 100
        self.y2 = 100

    def __str__(self):
        return "line: " + str(self.x1) + "," + str(self.y1) + " - " + str(self.x2) + "," + str(self.y2)

class Label(Action):
    def __init__(self):
        self.x = 0
        self.y = 0
        self.anchor_x = 0.5
        self.anchor_y = 0.5
        self.text = "_label_"
        self.padding = 2

    def size(self, drawing):
        print("Warning: Label.size not implemented")
        return (0, 0)

class Zone(Action):
    def __init__(self):
        self.x = 0
        self.y = 0
        self.w = 100
        self.h = 100

    def __str__(self):
        return "zone: " + str(self.x) + "," + str(self.y) + " size " + str(self.w) + "," + str(self.h)

    def left(self):
        return self.x-self.w/2

    def right(self):
        return self.x+self.w/2

    def top(self):
        return self.y-self.h/2

    def bottom(self):
        return self.y+self.h/2


class RepeatingThread:
    """Execute several functions periodically. Every function can have a different cycle"""

    def __init__(self, fn_to_freq = {}, rate=1/25):
        self.rate = rate
        self.fn_to_freq = fn_to_freq

        self.event = threading.Event()
        self.thread = threading.Thread(name='update',
                         target=self._run,
                         args=(self.event,))
        self.thread.start()
        self.active = False
        self.shutdown = False

    def _run(self, e):
        while True:
            event_is_set = e.wait()
            print("thread: " + str(self.active))
            if self.shutdown:
                break

            cnt = 0
            while self.active:
                sleep(self.rate)
                cnt += 1
                for fn, freq in self.fn_to_freq.items():
                    if cnt % freq == 0: fn()

            e.clear()

    def enable(self):
        if not self.active:
            self.active = True
            self.event.set()

    def disable(self):
        self.active = False

    def stop(self):
        self.shutdown = True
        self.activate = False
        self.event.set()




class Drawing:
    def __init__(self):
        self.actions = {}

    def refresh(self):
        pass

    def redraw(self):
        pass

    def enable(self):
        pass

    def disable(self):
        self.refresh()

    def is_enabled(self):
        print("Warning: is_enabled not implemented")
        pass

    def stop(self):
        pass

    def clear(self):
        self.actions.clear()

    def draw(self, action):
        self.actions[action] = True

    def undraw(self, action=None):
        if not action:
            self.actions.clear()
        else:
            del self.actions[action]


if __name__ == '__main__':
    draw = Drawing()
    print(draw.mouse_coords())

    draw.enable()
    draw.draw(Rectangle(x=500))

