#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import traceback
import threading
from time import sleep
from subprocess import call

from Xlib import X, display, Xutil
import Xlib as xlib

import common
logger = common.logger(__name__)

import ui as base
Action = base.Action

class Rectangle(base.Rectangle):
    def draw(self, ui):
        ui.window.rectangle(ui.gc,
            int(self.x),
            int(self.y),
            int(self.w),
            int(self.h)
        )

class Line(base.Line):
    def draw(self, ui):
        ui.window.line(ui.gc,
            # TODO: intersection with border
            max(0,int(self.x1)),
            max(0,int(self.y1)),
            max(0,int(self.x2)),
            max(0,int(self.y2))
        )

class Label(base.Label):
    def size(self, ui):
        info = ui.text_extents(ui.gc, self.text)
        self.width = info["overall_width"] + 2 * self.padding
        self.height = info["font_ascent"] + info["font_descent"] + 2 * self.padding
        self.shift_y = info["font_ascent"]
        return (self.width, self.height)

    def draw(self, ui):
        self.size(ui)
        # coordinates are bottom left corner of text
        left = self.x - self.anchor_x * self.width
        top = self.y - self.anchor_y * self.height

        ui.window.fill_rectangle(ui.fill_gc,
            int(left),
            int(top),
            int(self.width),
            int(self.height)
        )

        ui.window.draw_text(ui.gc,
                int(left + self.padding),
                int(top + self.shift_y + self.padding),
                self.text.encode()
        )



class Zone(base.Zone):
    def draw(self, ui):
        ui.window.rectangle(ui.gc,
            int(self.x-self.w/2),
            int(self.y-self.h/2),
            int(self.w),
            int(self.h)
        )

class UserInterface(base.UserInterface):
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

        super().__init__()

        fn_to_freq = {}
        fn_to_freq[lambda: self.refresh()] = 50

        def fn():
            try:
                self.redraw()
            except Exception as e:
                traceback.print_exc()
                print(e)
                return
        fn_to_freq[fn] = 1

        self.thread = base.RepeatingThread(fn_to_freq)


    def text_extents(self, gc, text):
        if not hasattr(gc, "_extent_cache"): setattr(gc, "_extent_cache", {})
        cache = getattr(gc, "_extent_cache")

        if text in cache: return cache[text]
        info = self.gc.query_text_extents(text.encode())._data
        cache[text] = info
        return info

    def mouse_coords(self):
        data = self.window.query_pointer()._data
        return Point(x=data["root_x"], y=data["root_y"])

    def enable(self):
        self.thread.enable()

    def disable(self):
        self.thread.disable()
        self.refresh()

    def is_enabled(self):
        return self.thread.active

    def stop(self):
        self.thread.stop()

    def refresh(self):
        # TODO: do this with xlib
        call(["xrefresh"])
        pass

    def redraw(self):
        for a in list(self.actions.keys()):
            a.draw(self)
        self.d.flush()

    def screen_width(self):
        return self.window.get_geometry().width

    def screen_height(self):
        return self.window.get_geometry().height


try:
    import tkinter
    import tkinter.simpledialog

    def input_dialog(self, msg=""):
        """Show an input dialog using the TK library"""

        tkinter.Tk().withdraw()
        msg = str(msg) + "\n\n<Enter>  --->  OK\n<Escape>  --->  cancel"
        return tkinter.simpledialog.askstring("yakm", msg)

    UserInterface.input_dialog = input_dialog

except Exception as exception:
    print(exception)
    print("WARNING: input_dialog not available")


if __name__ == '__main__':
    ui = UserInterface()
    ui.enable()
    ui.draw(Rectangle(x=500))

