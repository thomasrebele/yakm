#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import traceback
import threading
from time import sleep
from subprocess import call

from gi.repository import Gtk, Gdk, Pango, GdkPixbuf
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
    def region(self):
        # TODO
        return cairo.RectangleInt(x=int(self.x), y=int(self.y), width=10, height=10)

    def size(self, drawing):
        return (0,0)

    def draw(self, drawing):
        pass



class Zone(base.Zone):
    def region(self):
        # TODO
        return cairo.RectangleInt(x=int(self.left()), y=int(self.top()), width=int(self.w), height=int(self.h))


    def draw(self, drawing):
        pass

class Window(Gtk.Window):

    def __init__(self, actions):
        super(Window, self).__init__()

        self.actions = actions

        self.set_app_paintable(True)
        self.set_type_hint(Gdk.WindowTypeHint.DOCK)
        self.set_keep_below(True)

        screen = self.get_screen()
        self.root = screen.get_root_window()

#        visual = screen.get_rgba_visual()
#        if visual != None and screen.is_composited():
#            self.set_visual(visual)

        self.set_events(Gdk.EventMask.ALL_EVENTS_MASK)
        self.connect("draw", self.on_draw)
        self.connect("motion_notify_event", self.on_mouse_move)
        self.connect("event", self.on_mouse_move)

        lbl = Gtk.Label()
        text = "xyz"
        lbl.set_text(text)

        fd = Pango.FontDescription("Serif 20")
        lbl.modify_font(fd)
        lbl.modify_fg(Gtk.StateFlags.NORMAL,Gdk.color_parse("white"))

        self.add(lbl)

        self.resize(screen.get_width(), screen.get_height())
        self.move(0,0)
        self.show_all()


        self.region = self.get_mask()
        self.shape_combine_region(self.region)

    def get_mask(self):
        w, h = self.get_size()
        region = cairo.Region(cairo.RectangleInt(width=0, height=0))
        region.union(cairo.RectangleInt(x=0, y=0, width=10, height=10))
        region.union(cairo.RectangleInt(x=10, y=10, width=10, height=10))
        region.union(cairo.RectangleInt(x=-20, y=20, width=50, height=10))

        print(len(self.actions))
        for i in self.actions:
            r = i.region()
            if r:
                region.union(r)
            else:
                print("warning: no region for " + str(i))

        p = self.root.get_pointer()
        region.subtract(cairo.RectangleInt(x=int(p.x), y=int(p.y), width=10, height=10))

        return region

    def redraw(self):
        self.region = self.get_mask()
        self.shape_combine_region(self.region)

    def hide(self):
        self.region = cairo.Region(cairo.RectangleInt(width=0, height=0))
        self.shape_combine_region(self.region)

    def on_draw(self, widget, cr):
        cr.set_source_rgba(1.0, 0.0, 0.0, .75)
        cr.paint()

    def on_mouse_move(self, widget, cr):
        if hasattr(cr, "x"):
            # remove point
            region = self.region.copy()
            region.subtract(cairo.RectangleInt(x=int(cr.x), y=int(cr.y), width=10, height=10))
            self.shape_combine_region(region)



class Drawing(base.Drawing):
    def __init__(self):
        super().__init__()
        gtk_thread = threading.Thread(name='update',
                         target=self._run_gtk,
                         args=(self.event,))
        self.window = Window(self.actions)

        # avoid error on ctrl+c
        import signal
        signal.signal(signal.SIGINT, signal.SIG_DFL)

        gtk_thread.start()

    def _run_gtk(self, e):
        Gtk.main()

    def refresh(self):
        pass

    def undraw(self):
        self.window.hide()
        self.actions.clear()

    def enable(self):
        self.window.redraw()
        super().enable()

    def disable(self):
        super().disable()
        self.window.hide()

if __name__ == '__main__':
    draw = Drawing()
    print(draw.mouse_coords())

    draw.enable()
    draw.draw(Rectangle(x=500))

