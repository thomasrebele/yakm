#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pathlib
import os.path
from collections import defaultdict

from yakm import *
import draw
import input_devices

### commands

def key(to_press):
    """Type a key or a key combination"""

    def _upd(state, key=to_press):
        key = "+".join(list(state.modifiers.keys()) + [str(key)])
        print("pressing key " + str(key))
        call(["xdotool", "key", str(key)])

    return annotate(_upd, "key " + str(to_press))

commands.update(["key"])
print(commands)

class VoiceMode(Mode):
    def __init__(self, nav, conf):
        super().__init__(nav, conf)
        self.reset_mods()

    def reset_mods(self):
        self.nav.state.modifiers = {}

    def process(self, keys):
        if len(keys) == 0:
            return

        modifiers = self.nav.state.modifiers
        cmd = keys[0]
        if cmd in configuration["modifiers"]:
            mod = configuration["modifiers"][cmd]
            try:
                modifiers[mod] = True
                self.process(keys[1:])
            finally:
                del modifiers[mod]

        else:
            bindings = self.nav.state.get_current_bindings()
            if cmd in bindings.keys():
                action = bindings[cmd]
                for act in action:
                    act(self.nav.state)
            else:
                print("I don't understand '" + str(cmd) + "'")






class VoiceNavigator(Navigator):
    """This class coordinates the input, the drawing, and the history.
    It is the entry point of YAKM"""

    def __init__(self, input_file):
        super().__init__()

        self.grab_keyboard = lambda: None
        self.ungrab_keyboard = lambda: None

        voice_mode = VoiceMode(self, configuration["bindings"])
        self.state.enter_mode(voice_mode, grab_keyboard=False)

        while True:
            try:
                line = f.readline()
            except KeyboardInterrupt:
                break

            if line == '': break
            if line == '\n': continue

            line = line[:-1]
            print(">" + str(line))

            # execute command
            voice_mode.process(line.split(' '))

        # TODO: exit on ctrl+c
        self.vis.stop()



if __name__ == '__main__':
    ################################################################################
    # configuration
    ################################################################################

    # determine path
    conf_dir = "~/.yakm/"
    script_dir = os.path.dirname(os.path.realpath(__file__))
    conf_file = script_dir + "/example_voice.conf" # TODO: resolve configuration path

    # setup configuration dir
    conf_dir = os.path.expanduser(conf_dir)
    pathlib.Path(conf_dir).mkdir(parents=True, exist_ok=True)

    # load configuration from file
    configuration = {}

    if os.path.isfile(conf_file):
        with open(conf_file, "r") as f_config:
            # we limit exec(...) to the above defined yakm commands
            exec_globals = {"__builtins__": {"print" : print}}
            _globals = globals()
            for i in commands:
                print("adding " + str(i))
                exec_globals[i] = _globals[i]

            # read configuration
            conf_str = f_config.read()
            print(exec_globals)
            exec(conf_str, exec_globals, configuration)
    else:
        print("WARNING: silvius-mode could not open configuration file " + str(conf_file))

    ################################################################################
    # start
    ################################################################################
    import sys
    if len(sys.argv) > 1:
        filename = sys.argv[1]
        f = open(filename)
    else:
        f = sys.stdin

    VoiceNavigator(f)

    if f != sys.stdin:
        f.close()

