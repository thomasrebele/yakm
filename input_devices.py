#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import traceback
import threading
from time import sleep
import queue

import Xlib
from Xlib import X, XK
from Xlib.ext.xtest import fake_input

key_mods = {
    "shift": X.ShiftMask,
    "ctrl": X.ControlMask,
    "mod1": X.Mod1Mask,
    "mod2": X.Mod2Mask,
    "mod3": X.Mod3Mask,
    "mod4": X.Mod4Mask,
    "mod5": X.Mod5Mask,
}

# use xev command to find out codes
keys_to_code = {
    '&':'ampersand', '\'':'apostrophe', '^':'asciicircum', '~':'asciitilde',
    '*':'asterisk', '@':'at', '\\':'backslash', '|':'bar', '\b':'BackSpace',
    '{':'braceleft', '}':'braceright', '[':'bracketleft', ']':'bracketright',
    ':':'colon', ',':'comma', '$':'dollar', '\e':'Escape',
    '=':'equal', '!':'exclam', '`':'grave', '>':'greater', '<':'less',
    '-':'minus', '\n':'Return', '#':'numbersign', '(':'parenleft', ')':'parenright',
    '%':'percent', '.':'period', '+':'plus', '?':'question', '"':'quotedbl',
    ';':'semicolon', '/':'slash', ' ':'space', '\t':'Tab', '_':'underscore',
    'ü':'udiaeresis', 'ö':'odiaeresis', 'ä':'adiaeresis', 'ß':'ssharp',
    "PageDown": "Next", "PageUp": "Prior"
}


disp = Xlib.display.Display()
screen = disp.screen()
root = screen.root

class Coord:
    x = 0
    y = 0

def get_keycode(key):
    mod = X.NONE
    for p in key.split("+"):
        if p in key_mods:
            mod |= key_mods[p]
        else:
            key = p

    key_sym = XK.string_to_keysym(keys_to_code.get(key, key))
    return disp.keysym_to_keycode(key_sym), mod

def get_keysym(key_code):
    key_sym = disp.keycode_to_keysym(key_code, 0)
    return XK.keysym_to_string(key_sym)



def ignore_mod(mods=[X.LockMask, X.Mod2Mask], mod=0):
    if len(mods) == 0:
        yield mod
    else:
        yield from ignore_mod(mods[1:], mod)
        yield from ignore_mod(mods[1:], mod|mods[0])

def grab_key(key_code, mod):
    for i in ignore_mod():
        root.grab_key(key_code, mod|i, False, X.GrabModeAsync, X.GrabModeAsync)

def ungrab_key(key_code, mod):
    for i in ignore_mod():
        root.ungrab_key(key_code, mod|i)

class Binding:
    key = None
    fn = None


class Input:
    def __init__(self):
        self.active = True
        self.event_thread = threading.Thread(name='input event thread', target=self.event_loop)
        self.event_thread.start()

        # use a different thread for executing the actions
        # reason: the event thread needs to receive the key release event so that ungrab_keyboard works for input_dialog
        self.action_queue = queue.Queue(1000)
        self.action_thread = threading.Thread(name='input action thread',
                        target=self.action_loop)
        self.action_thread.start()

        self.grabbing = False
        self.bindings = {}

        geo = root.get_geometry()

        self.w = geo.width
        self.h = geo.height

    def handle_event(self, evt):
        #print(evt)
        try:
            if evt.type == X.KeyPress:
                key_code = evt.detail
                mod = evt.state & ~(X.LockMask | X.Mod2Mask | X.Button1Mask | X.Button2Mask | X.Button3Mask | X.Button4Mask | X.Button5Mask) # todo
                # pressed_key =  get_keysym(evt.detail)
                # print("pressed " + pressed_key)

                k = (key_code, mod)
                if k in self.bindings:
                    self.action_queue.put(self.bindings[k].fn)
                else:
                    print("unbound key " + str(key_code))


            elif evt.type == X.KeyRelease:
                #print("\nrelease: " + str(evt) + "\n")
                pass
        except Exception as e:
            print("yakm error: an exception occurred while handling a key event")
            traceback.print_exc()
            self.ungrab_keyboard()
            for k in self.key_bindings():
                self.unregister_key(k)

    def action_loop(self):
        while self.active:
            sleep(0.01)
            if not self.action_queue.empty():
                item = self.action_queue.get()
                item()

    def event_loop(self):
        while self.active:
            sleep(0.01)
            if root.display.pending_events()>0:
                evt = root.display.next_event()
                if evt.type in [X.KeyPress, X.KeyRelease]:
                     self.handle_event(evt)

    def key_bindings(self):
        return dict([(b.key, b.fn) for b in self.bindings.values()])

    def register_key(self, key, fn, _global=False):
        key_code, mod_mask = get_keycode(key)
        if _global:
            grab_key(key_code, mod_mask)

        binding = Binding()
        binding.key = key
        binding.fn = fn
        binding._global = _global
        self.bindings[(key_code, mod_mask)] = binding

    def unregister_key(self, key):
        key_code, mod_mask = get_keycode(key)
        try:
            binding = self.bindings[(key_code, mod_mask)]
            if binding._global:
                ungrab_key(key_code, mod_mask)
            del self.bindings[(key_code, mod_mask)]
        except KeyError:
            pass

    def grab_keyboard(self):
        print("input: grabbing keyboard")
        self.grabbing = True
        root.grab_keyboard(True, X.GrabModeAsync, X.GrabModeAsync,X.CurrentTime)

    def ungrab_keyboard(self):
        print("input: ungrabbing keyboard")
        self.grabbing = False
        disp.ungrab_keyboard(X.CurrentTime)
        print("input: ungrabbing done")

    def stop(self):
        if self.grabbing:
            self.ungrab_keyboard()
        self.active = False

    def move(self, x, y):
        #fake_input(disp, X.MotionNotify, x=int(x), y=int(y))
        p = self.pointer()
        x = int(x-p.x)
        y = int(y-p.y)
        print("moving mouse to " + str(x) + " " + str(y))
        disp.warp_pointer(x, y)

    def pointer(self):
        x = root.query_pointer().win_x
        y = root.query_pointer().win_y

        p = Coord()
        p.x, p.y = x, y
        return p

    def window(self):
        win = root.query_pointer().child or root
        return {"name": win.get_wm_name(), "class": win.get_wm_class()}


    def click(self, button, actions=["press", "release"]):
        key = {1: X.Button1, 2: X.Button2, 3: X.Button3, 4: X.Button4, 5: X.Button5}[button]

        m = {
            "press": X.ButtonPress,
            "release":  X.ButtonRelease,
        }

        for act in actions:
            event = m[act]
            fake_input(disp, event, key)


