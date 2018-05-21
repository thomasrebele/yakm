
from time import sleep

import threading

import Xlib
from Xlib import X, XK
from Xlib.ext.xtest import fake_input

key_mods = {
    "shift": X.ShiftMask,
    "ctrl": X.ControlMask
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

    key_sym = XK.string_to_keysym(key)
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
        self.thread = threading.Thread(name='keyboard listener',
                                 target=self.event_loop)
        self.thread.start()
        self.bindings = {}

        geo = root.get_geometry()

        self.w = geo.width
        self.h = geo.height

    def handle_event(self, evt):
        #print(evt)
        if evt.type == X.KeyPress:
            key_code = evt.detail
            mod = evt.state & ~(X.LockMask | X.Mod2Mask | X.Button1Mask | X.Button2Mask | X.Button3Mask | X.Button4Mask | X.Button5Mask) # todo
            # pressed_key =  get_keysym(evt.detail)
            # print("pressed " + pressed_key)

            k = (key_code, mod)
            if k in self.bindings:
                self.bindings[k].fn()


        elif evt.type == X.KeyRelease:
            #print("\nrelease: " + str(evt) + "\n")
            pass

    def event_loop(self):
        while self.active:
            sleep(0.01)
            if root.display.pending_events()>0:
                evt = root.display.next_event()
                if evt.type in [X.KeyPress, X.KeyRelease]:
                     self.handle_event(evt)

    def key_bindings(self):
        return dict([(b.key, b.fn) for b in self.bindings.values()])

    def register_key(self, key, fn):
        key_code, mod_mask = get_keycode(key)
        grab_key(key_code, mod_mask)

        binding = Binding()
        binding.key = key
        binding.fn = fn
        self.bindings[(key_code, mod_mask)] = binding

        #root.grab_keyboard(True, X.GrabModeAsync, X.GrabModeAsync,X.CurrentTime)

    def unregister_key(self, key):
        key_code, mod_mask = get_keycode(key)
        ungrab_key(key_code, mod_mask)
        del self.bindings[(key_code, mod_mask)]

        #root.ungrab_keyboard(True, X.GrabModeAsync, X.GrabModeAsync,X.CurrentTime)

    def stop(self):
        self.active = False

    def move(self, x, y):
        fake_input(disp, X.MotionNotify, x=int(x), y=int(y))
        #root.warp_pointer(int(x), int(y))

    def pointer(self):
        window = root.query_pointer().child
        try:
            x = window.query_pointer().win_x
            y = window.query_pointer().win_y
        except:
            window = root
            x = root.query_pointer().win_x
            y = root.query_pointer().win_y

        p = Coord()
        p.x, p.y = x, y
        return p


    def click(self, button, actions=["press", "release"]):
        key = {1: X.Button1, 2: X.Button2, 3: X.Button3, 4: X.Button4, 5: X.Button5}[button]
        mod = X.NONE

        window = root.query_pointer().child
        try:
            window.query_pointer()
        except:
            window = root

        p = self.pointer()

        m = {
            "press": Xlib.protocol.event.ButtonPress,
            "release": Xlib.protocol.event.ButtonRelease
        }
        m = {
            "press": X.ButtonPress,
            "release":  X.ButtonRelease,
        }


        for act in actions:
            print("action: " + str(act))

        #    Event = m[act]
        #    evt_key = Event(detail=key, state=mod,
        #                  root=root, window=window, child=X.NONE,
        #                  root_x=0, root_y=0, event_x=p.x, event_y=p.y,
        #                  same_screen=1, time=X.CurrentTime
        #                 )
        #    window.send_event(evt_key)

            event = m[act]

            fake_input(disp, event, key)


