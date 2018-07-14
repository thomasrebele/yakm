#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import traceback
import threading
from time import sleep
from subprocess import call

from gi.repository import Gtk, Gdk, Pango, GdkPixbuf, GObject, GLib
import cairo



import draw as base

Action = base.Action

class Rectangle(base.Rectangle):
    def region(self):
        return cairo.RectangleInt(x=int(self.x), y=int(self.y), width=int(self.w), height=int(self.h))

    def draw(self, drawing):
        pass

class Line(base.Line):
    def region(self):
        w = int(abs(self.x2-self.x1))
        h = int(abs(self.y2-self.y1))
        w = max(w, 1)
        h = max(h, 1)
        return cairo.RectangleInt(x=int(self.x1), y=int(self.y1), width=w, height=h)


    def draw(self, drawing):
        pass

class Label(base.Label):
    lock = threading.RLock()
    layout_lbl = Gtk.Label()
    layout = layout_lbl.get_layout()
    fd = Pango.FontDescription("Serif 20")

    def __init__(self):
        self.lbl = Gtk.Label()
        self._text = "<label>"
        super().__init__()

    @property
    def text(self):
        return self._text

    @text.setter
    def text(self, value):
        self._text = value
        self.size(changed=True)

    @text.getter
    def text(self):
        return self._text

    def init(self):
        self.lbl.set_text(self.text)
        self.lbl.modify_font(self.fd)
        self.lbl.modify_fg(Gtk.StateFlags.NORMAL,Gdk.color_parse("white"))

    def size(self, drawing=None, changed=False):
        # workaround: calling get_layout too often causes a segmentation fault
        if hasattr(self, "width") and not changed:
            return self.width, self.height

        self.lock.acquire()
        try:
            # https://stackoverflow.com/a/23187879/1562506
            self.layout.set_markup(self.text)
            self.layout.set_font_description(self.fd)
            self.width, self.height = self.layout.get_pixel_size()
            return self.width, self.height
        finally:
            self.lock.release()

    def region(self):
        w,h = self.size()
        return cairo.RectangleInt(x=int(self.x-w/2), y=int(self.y-h/2), width=w, height=h)

    def draw(self, drawing):
        self.init()
        w,h = self.size()
        w = max(w, 10)
        h = max(h, 10)
        drawing.fix.put(self.lbl, self.x-w/2, self.y-h/2)



class Zone(base.Zone):
    def region(self):
        # TODO
        x1 = int(self.left())
        x2 = int(self.right())
        y1 = int(self.top())
        y2 = int(self.bottom())
        w = int(self.w)
        h = int(self.h)
        r = cairo.Region(cairo.RectangleInt(x=x1, y=y1, width=1, height=h))
        r.union(cairo.RectangleInt(x=x1, y=y1, width=w, height=1))
        r.union(cairo.RectangleInt(x=x2, y=y1, width=1, height=h))
        r.union(cairo.RectangleInt(x=x1, y=y2, width=w, height=1))
        return r


    def draw(self, drawing):
        pass

class Window(Gtk.Window):

    def __init__(self, drawing):
        super(Window, self).__init__()

        self.drawing = drawing
        self.click_box_width = 1

        self.set_app_paintable(True)
        self.set_type_hint(Gdk.WindowTypeHint.DOCK)
        self.set_keep_below(True)

        self.screen = self.get_screen()
        self.root = self.screen.get_root_window()

        visual = self.screen.get_rgba_visual()
        if visual != None and self.screen.is_composited():
            self.set_visual(visual)

        self.set_events(Gdk.EventMask.ALL_EVENTS_MASK)
        self.connect("draw", self.on_draw)
        self.connect("motion_notify_event", self.on_mouse_move)
        self.connect("event", self.on_mouse_move)

        self.drawing.fix = Gtk.Fixed()
        self.add(self.drawing.fix)



        self.resize(self.screen.get_width(), self.screen.get_height())
        self.move(0,0)

        self.region = self.get_mask()
        self.shape_combine_region(self.region)


        self.show_all()

    def get_mask(self):
        w, h = self.get_size()
        region = cairo.Region(cairo.RectangleInt(width=0, height=0))

        for i in self.drawing.actions.keys():
            r = i.region()
            if r:
                region.union(r)
            else:
                print("warning: no region for " + str(i))

        p = self.root.get_pointer()
        self.cut_pointer(region, p.x, p.y)
        return region

    def redraw(self):
        for c in self.drawing.fix.get_children():
            self.drawing.fix.remove(c)

        acts = list(self.drawing.actions.keys())
        for i in acts:
            i.draw(self.drawing)

        self.region = self.get_mask()
        self.shape_combine_region(self.region)
        self.show_all()


    def undraw(self):
        self.hide()

    def on_draw(self, widget, cr):
        cr.set_source_rgba(1.0, 0.0, 0.0, .75)
        cr.paint()

    def cut_pointer(self, region, x, y):
        d = self.click_box_width
        region.subtract(cairo.RectangleInt(
            x=int(x-d),
            y=int(y-d),
            width=1+2*d,
            height=1+2*d))

    def on_mouse_move(self, widget, cr):
        if hasattr(cr, "x"):
            # remove point
            region = self.region.copy()
            self.cut_pointer(region, cr.x, cr.y)
            self.shape_combine_region(region)



class Drawing(base.Drawing):
    def __init__(self):
        super().__init__()

        # https://stackoverflow.com/questions/21150914/python-gtk-3-safe-threading
        GObject.threads_init()
        gtk_thread = threading.Thread(name='update',
                         target=self._run_gtk,
                         args=(None,))



        self.window = Window(self)
        self.enabled = False

        # avoid error on ctrl+c
        import signal
        signal.signal(signal.SIGINT, signal.SIG_DFL)

        gtk_thread.start()

    def _run_gtk(self, e):
        Gtk.main()

    def refresh(self):
        GLib.idle_add(self.window.redraw)

    def undraw(self):
        self.actions.clear()
        GLib.idle_add(self.window.undraw)

    def enable(self):
        GLib.idle_add(self.window.redraw)
        super().enable()
        self.enabled = True

    def is_enabled(self):
        return self.enabled

    def disable(self):
        super().disable()
        #self.window.hide()
        self.enabled = False

import signal

def sigabrt_handler():
    print("SIGABRT received")
    pass

signal.signal(signal.SIGABRT, sigabrt_handler)
print("registered SIGABRT handler")

if __name__ == '__main__':
    draw = Drawing()


    draw.enable()
    draw.draw(Rectangle(x=500))

