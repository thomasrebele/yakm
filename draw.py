from Xlib import X, display, Xutil
import Xlib as xlib
from time import sleep

from subprocess import call

import threading

class Action:
    def draw(self):
        pass

class Rectangle(Action):
    def __init__(self):
        self.x = 0
        self.y = 0
        self.w = 100
        self.h = 100

    def draw(self, drawing):
        drawing.window.rectangle(drawing.gc,
            int(self.x),
            int(self.y),
            int(self.w),
            int(self.h)
        )

class Line(Action):
    def __init__(self):
        self.x1 = 0
        self.y1 = 0
        self.x2 = 100
        self.y2 = 100

    def draw(self, drawing):
        drawing.window.line(drawing.gc,
            # TODO: intersection with border
            max(0,int(self.x1)),
            max(0,int(self.y1)),
            max(0,int(self.x2)),
            max(0,int(self.y2))
        )

    def __str__(self):
        return "line: " + str(self.x1) + "," + str(self.y1) + " - " + str(self.x2) + "," + str(self.y2)



class Zone(Action):
    def __init__(self):
        self.x = 0
        self.y = 0
        self.w = 100
        self.h = 100

    def draw(self, drawing):
        drawing.window.rectangle(drawing.gc,
            int(self.x-self.w/2),
            int(self.y-self.h/2),
            int(self.w),
            int(self.h)
        )

    def left(self):
        return self.x-self.w/2

    def right(self):
        return self.x+self.w/2

    def top(self):
        return self.y-self.h/2

    def bottom(self):
        return self.y+self.h/2


class Drawing:
    def __init__(self):
        self.d = display.Display()
        self.screen = self.d.screen()
        self.window = self.screen.root


        fg = 0xff0000

        self.gc = self.window.create_gc(
            line_width = 4,
            foreground = fg,
            subwindow_mode = X.IncludeInferiors,
        )

        self.actions = {}
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
                sleep(0.01)
                cnt += 1
                if cnt % 4 == 0: self.refresh()
                self.redraw()
            e.clear()

    def refresh(self):
        # TODO: do this with xlib
        call(["xrefresh"])

    def redraw(self):
        for a in self.actions.keys():
            a.draw(self)
        self.d.flush()

    def enable(self):
        if not self.active:
            self.active = True
            self.event.set()

    def disable(self):
        self.active = False
        self.refresh()

    def stop(self):
        self.shutdown = True
        self.activate = False
        self.event.set()

    def draw(self, action):
        self.actions[action] = True

    def undraw(self, action=None):
        if not action:
            self.actions.clear()
        else:
            del self.actions[action]


