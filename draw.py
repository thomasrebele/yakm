from Xlib import X, display, Xutil
from time import sleep

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
            self.x,
            self.y,
            self.w,
            self.h
        )


class Drawing:
    def __init__(self):
        self.d = display.Display()
        self.window = self.d.screen().root

        white = 0xffffff
        black = 0x000000

        self.gc = self.window.create_gc(
            line_width = 2,
            foreground = white,
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

            while self.active:
                sleep(0.01)
                self.redraw()
            e.clear()

    def redraw(self):
        for a in self.actions.keys():
            a.draw(self)
        self.d.flush()

    def enable(self):
        if not self.active:
            self.active = True
            self.event.set()

    def stop(self):
        self.shutdown = True
        self.activate = False
        self.event.set()

    def rectangle(self):
        return Rectangle()

    def draw(self, action):
        self.actions[action] = True
        self.enable()



