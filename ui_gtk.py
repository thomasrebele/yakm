#!/usr/bin/env python3
# -*- coding: utf-8 -*-


# All Gtk commands are executed by a single thread.
# This avoids [xcb] Unknown request in queue while dequeuing gtk


import traceback
import threading
import queue
from time import sleep
from subprocess import call

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, Pango, GdkPixbuf, GObject, GLib
import cairo

import common
logger = common.logger(__name__)

import ui as base
Action = base.Action

class Rectangle(base.Rectangle):
    def region(self):
        return cairo.RectangleInt(x=int(self.x), y=int(self.y), width=int(self.w), height=int(self.h))

    def draw(self, ui):
        pass

class Line(base.Line):
    def region(self):
        w = int(abs(self.x2-self.x1))
        h = int(abs(self.y2-self.y1))
        w = max(w, 1)
        h = max(h, 1)
        return cairo.RectangleInt(x=int(self.x1), y=int(self.y1), width=w, height=h)


    def draw(self, ui):
        pass

class Label(base.Label):
    lock = threading.RLock()
    layout_lbl = Gtk.Label()
    layout = layout_lbl.get_layout()
    fd = Pango.FontDescription("Serif 20")

    def __init__(self):
        self.lbl = Gtk.Label()
        self._text = "_label_"
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

    def size(self, ui=None, changed=False):
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

    def draw(self, ui):
        self.init()
        w,h = self.size()
        w = max(w, 10)
        h = max(h, 10)
        ui.fix.put(self.lbl, self.x-w/2, self.y-h/2)



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


    def draw(self, ui):
        pass

class Window(Gtk.Window):

    def __init__(self, ui):
        super(Window, self).__init__()

        self.ui = ui
        self.click_box_width = 1

        self.screen = self.get_screen()
        self.root = self.screen.get_root_window()

        visual = self.screen.get_rgba_visual()
        if visual != None and self.screen.is_composited():
            self.set_visual(visual)

        self.set_events(Gdk.EventMask.ALL_EVENTS_MASK)
        self.connect("draw", self.on_draw)
        self.connect("motion_notify_event", self.on_mouse_move)
        self.connect("event", self.on_mouse_move)

        self.ui.fix = Gtk.Fixed()
        self.add(self.ui.fix)


        self.show_all()

    def show_all(self):
        self.resize(self.screen.get_width(), self.screen.get_height())
        self.move(0,0)

        self.region = self.get_mask()
        self.shape_combine_region(self.region)

        self.set_app_paintable(True)
        self.set_type_hint(Gdk.WindowTypeHint.DOCK)
        self.set_keep_below(True)
        self.present()
        super().show_all()

    def get_mask(self):
        w, h = self.get_size()
        region = cairo.Region(cairo.RectangleInt(width=0, height=0))

        for i in list(self.ui.actions.keys()):
            r = i.region()
            if r:
                region.union(r)
            else:
                logger.warning("warning: no region for " + str(i))

        p = self.root.get_pointer()
        self.cut_pointer(region, p.x, p.y)
        return region

    def redraw(self):
        for c in self.ui.fix.get_children():
            self.ui.fix.remove(c)

        acts = list(self.ui.actions.keys())
        for i in acts:
            i.draw(self.ui)

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



class UserInterface(base.UserInterface):
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

    def screen_width(self):
        return self.window.screen.get_width()

    def screen_height(self):
        return self.window.screen.get_height()


    def input_dialog(self, msg=""):
        # input dialog must be executed in Gtk thread
        result_queue = queue.Queue(1)
        GLib.idle_add(lambda: self._input_dialog(result_queue, msg))

        result = result_queue.get()
        print("input dialog returned " + str(result))
        return result



    def _input_dialog(self, result_queue, msg=""):
        """Show an input dialog using the GTK library"""
        msg = str(msg) + "\n\n<Enter>  --->  OK\n<Escape>  --->  cancel"

        dialog = Gtk.MessageDialog(self.window,
                              Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
                              Gtk.MessageType.QUESTION,
                              Gtk.ButtonsType.OK_CANCEL,
                              msg)
        dialog.set_title("yakm")

        content = dialog.get_content_area()
        entry = Gtk.Entry()
        entry.set_size_request(550,0)
        content.pack_end(entry, False, False, 0)

        entry.connect("activate", lambda widget: dialog.response(Gtk.ResponseType.OK))
        dialog.set_default_response(Gtk.ResponseType.OK)

        dialog.show_all()
        response = dialog.run()
        text = entry.get_text()
        dialog.destroy()
        if (response == Gtk.ResponseType.OK):
            result_queue.put(text)
        else:
            result_queue.put(None)





import signal

def sigabrt_handler():
    logger.error("SIGABRT received")
    pass

signal.signal(signal.SIGABRT, sigabrt_handler)
logger.debug("registered SIGABRT handler")

if __name__ == '__main__':
    ui = UserInterface()
    ui.enable()
    ui.draw(Rectangle(x=500))

