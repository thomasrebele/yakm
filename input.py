
from time import sleep

import threading

import Xlib
from Xlib import X, XK
from Xlib.display import Display

disp = Display()
screen = disp.screen()
root = screen.root


def get_keycode(key):
    key_sym = XK.string_to_keysym(key)
    return disp.keysym_to_keycode(key_sym)

def get_keysym(key_code):
    key_sym = disp.keycode_to_keysym(key_code, 0)
    return XK.keysym_to_string(key_sym)


def ignore_mod(mods, mod=0):
    if len(mods) == 0:
        yield mod
    else:
        yield from ignore_mod(mods[1:], mod)
        yield from ignore_mod(mods[1:], mod|mods[0])

def grab_key(key_code, mod):
    for i in ignore_mod([X.LockMask, X.Mod2Mask]):
        root.grab_key(key_code, mod|i, 0, X.GrabModeAsync, X.GrabModeAsync)


def ungrab_key(key_code, mod):
    for i in ignore_mod([X.LockMask, X.Mod2Mask]):
        root.ungrab_key(key_code, mod|i)


Shift = X.ShiftMask
Ctrl = X.ControlMask

class Input:
    def __init__(self):
        self.active = True
        self.thread = threading.Thread(name='keyboard listener',
                                 target=self.event_loop)
        self.thread.start()
        self.actions = {}

        geo = root.get_geometry()
        print(geo)

        self.w = geo.width
        self.h = geo.height

    def handle_event(self, evt):
        if evt.type == X.KeyPress:
            key_code = evt.detail
            mod = evt.state & ~(X.LockMask | X.Mod2Mask) # todo
            # pressed_key =  get_keysym(evt.detail)
            # print("pressed " + pressed_key)

            k = (key_code, mod)
            if k in self.actions:
                self.actions[k]()


        elif evt.type == X.KeyRelease:
            print("\nrelease: " + str(evt) + "\n")

    def event_loop(self):
        while self.active:
            sleep(0.01)
            if root.display.pending_events()>0:
                evt = root.display.next_event()
                if evt.type in [X.KeyPress, X.KeyRelease]:
                     self.handle_event(evt)

    def register_key(self, key, mod_mask, action):
        if mod_mask == None: mod_mask = X.NONE
        key_code = get_keycode(key)
        grab_key(key_code, mod_mask)
        self.actions[(key_code, mod_mask)] = action

    def unregister_key(self, key, mod_mask):
        if mod_mask == None: mod_mask = X.NONE
        key_code = get_keycode(key)
        ungrab_key(key_code, mod_mask)
        del self.actions[(key_code, mod_mask)]


    def stop(self):
        self.active = False

    def move(self, x, y):
        root.warp_pointer(x, y)

    def click(self, button):
        key = X.Button1
        mod = 0

        window = root.query_pointer().child
        try:
            x = window.query_pointer().win_x
            y = window.query_pointer().win_y
        except:
            window = root
            x = root.query_pointer().win_x
            y = root.query_pointer().win_y

        for Event in [Xlib.protocol.event.ButtonPress, Xlib.protocol.event.ButtonRelease]:

            evt_key = Event(detail=key, state=mod,
                          root=root, window=window, child=X.NONE,
                          root_x=0, root_y=0, event_x=x, event_y=y,
                          same_screen=1, time=X.CurrentTime
                         )

            window.send_event(evt_key)


