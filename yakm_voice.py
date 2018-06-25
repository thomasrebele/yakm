#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pathlib
import os.path
from collections import defaultdict

from yakm import *
import draw
import input_devices




class VoiceNavigator(Navigator):
    """This class coordinates the input, the drawing, and the history.
    It is the entry point of YAKM"""

    def __init__(self, input_file):
        super().__init__()

        self.grab_keyboard = lambda: None
        self.ungrab_keyboard = lambda: None

        self.state.enter_mode(Mode(self, configuration["bindings"]), grab_keyboard=False)

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
            for cmd in line.split(' '):
                bindings = self.state.get_current_bindings()
                if cmd in bindings.keys():
                    action = bindings[cmd]
                    for act in action:
                        act(self.state)

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

