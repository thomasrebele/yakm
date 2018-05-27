#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import traceback
import threading
from time import sleep
from subprocess import call

from Xlib import X, display, Xutil
import Xlib as xlib

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

class Label(Action):
    def __init__(self):
        self.x = 0
        self.y = 0
        self.anchor_x = 0.5
        self.anchor_y = 0.5
        self.text = "<label>"
        self.padding = 2

    def size(self, drawing):
        info = drawing.text_extents(drawing.gc, self.text)
        self.width = info["overall_width"] + 2 * self.padding
        self.height = info["font_ascent"] + info["font_descent"] + 2 * self.padding
        self.shift_y = info["font_ascent"]
        return (self.width, self.height)

    def draw(self, drawing):
        self.size(drawing)
        # coordinates are bottom left corner of text
        left = self.x - self.anchor_x * self.width
        top = self.y - self.anchor_y * self.height

        drawing.window.fill_rectangle(drawing.fill_gc,
            int(left),
            int(top),
            int(self.width),
            int(self.height)
        )

        drawing.window.draw_text(drawing.gc,
                int(left + self.padding),
                int(top + self.shift_y + self.padding),
                self.text.encode()
        )

        pass



class Zone(Action):
    def __init__(self):
        self.x = 0
        self.y = 0
        self.w = 100
        self.h = 100

    def __str__(self):
        return "zone: " + str(self.x) + "," + str(self.y) + " size " + str(self.w) + "," + str(self.h)


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
        font = self.d.open_font("-adobe-helvetica-*-r-normal-*-25-*-*-*-*-*-*-*")
        if font == None:
            font = self.d.open_font("-*-*-bold-r-normal--25-*-*-75-*-*-*-*")

        self.screen = self.d.screen()
        self.window = self.screen.root


        fg = 0xff0000
        bg = 0x00ff00

        self.gc = self.window.create_gc(
            line_width = 2,
            foreground = fg,
            background = bg,
            subwindow_mode = X.IncludeInferiors,
            font = font,
        )

        self.fill_gc = self.window.create_gc(
            line_width = 4,
            foreground = 0xffffff,
            background = 0xffffff,
            subwindow_mode = X.IncludeInferiors,
            font = font,
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
                sleep(0.04)
                cnt += 1
                if cnt % 50 == 0: self.refresh()
                try:
                    self.redraw()
                except Exception as e:
                    traceback.print_exc()
                    print(e)
                    return
            e.clear()

    def text_extents(self, gc, text):
        if not hasattr(gc, "_extent_cache"): setattr(gc, "_extent_cache", {})
        cache = getattr(gc, "_extent_cache")

        if text in cache: return cache[text]
        info = self.gc.query_text_extents(text.encode())._data
        cache[text] = info
        return info

    def refresh(self):
        # TODO: do this with xlib
        call(["xrefresh"])

    def redraw(self):
        for a in list(self.actions.keys()):
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


