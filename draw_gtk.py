#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import traceback
import threading
from time import sleep
from subprocess import call

from gi.repository import Gtk, Gdk, Pango, GdkPixbuf, GObject, GLib
import cairo

# necessary? see https://stackoverflow.com/questions/21150914/python-gtk-3-safe-threading
# GLib.threads_init()
GObject.threads_init()
# Gdk.threads_init()

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
    def __init__(self):
        super().__init__()
        self.lbl = Gtk.Label()
        fd = Pango.FontDescription("Serif 20")
        self.lbl.modify_font(fd)
        self.lbl.modify_fg(Gtk.StateFlags.NORMAL,Gdk.color_parse("white"))
        self.lbl.modify_bg(Gtk.StateFlags.NORMAL,Gdk.color_parse("blue"))

    def region(self):
        rect = self.lbl.get_allocation()
        print([rect.x, rect.y, rect.width, rect.height])
        return cairo.RectangleInt(x=rect.x, y=rect.y, width=rect.width, height=rect.height)

    def size(self, drawing):
        return (0,0)

    def draw(self, drawing):
        self.lbl.set_text(self.text)
        rect = self.lbl.get_allocation()
        w = max(rect.width, 10)
        h = max(rect.height, 10)
        drawing.fix.put(self.lbl, self.x-w/2, self.y-h/2)

        pass



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
        print("here")

    def get_mask(self):
        w, h = self.get_size()
        region = cairo.Region(cairo.RectangleInt(width=0, height=0))

        for i in self.drawing.actions:
            r = i.region()
            if r:
                region.union(r)
            else:
                print("warning: no region for " + str(i))

        p = self.root.get_pointer()
        region.subtract(cairo.RectangleInt(x=int(p.x), y=int(p.y), width=10, height=10))

        return region

    def redraw(self):

        for c in self.drawing.fix.get_children():
            self.drawing.fix.remove(c)

        lbl = Gtk.Label()
        text = "xyz aba atua rartuae"
        lbl.set_text(text)

        fd = Pango.FontDescription("Serif 50")
        lbl.modify_font(fd)
        lbl.modify_fg(Gtk.StateFlags.NORMAL,Gdk.color_parse("white"))
        lbl.modify_bg(Gtk.StateFlags.NORMAL,Gdk.color_parse("blue"))
        self.drawing.fix.put(lbl, 100, 100)

        for i in self.drawing.actions.keys():
            i.draw(self.drawing)

        self.show_all()

        self.region = self.get_mask()
        self.region.union(cairo.RectangleInt(x=100, y=100, width=100, height=50))
        self.shape_combine_region(self.region)
        self.show_all()


    def undraw(self):
        self.hide()

    def on_draw(self, widget, cr):

        cr.set_source_rgba(1.0, 0.0, 0.0, .75)
        cr.paint()

    def on_mouse_move(self, widget, cr):
        if hasattr(cr, "x"):
            # remove point
            region = self.region.copy()
            d = self.click_box_width
            region.subtract(cairo.RectangleInt(
                x=int(cr.x-d),
                y=int(cr.y-d),
                width=1+2*d,
                height=1+2*d))
            #GLib.idle_add(self.shape_combine_region, region)
            self.shape_combine_region(region)



class Drawing(base.Drawing):
    def __init__(self):
        super().__init__()
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

