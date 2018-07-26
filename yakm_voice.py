#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pathlib
import os.path
import tty
import threading
import sys
from collections import defaultdict
from time import sleep
from subprocess import call

from yakm import *
import draw_gtk as draw
import input_devices
from common import *
logger = logger(__name__)

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

### commands
with command_definitions(lambda: globals()):

    def key(key, state):
        """Type a key or a key combination"""

        mods = list(state.modifiers.keys())
        if "f_key" in mods:
            if type(key) == int:
                key = "F" + str(key)
        key = "+".join(mods + [str(key)])
        logger.trace("pressing key " + str(key))
        call(["xdotool", "key", str(key)])

    def start(state):
        """Start the navigation. Enters the default mode if no other mode is active"""
        if not state.mode:
            voice_mode = VoiceMode(state.nav, configuration["bindings"])
            state.enter_mode(voice_mode, grab_keyboard=False)

    def dictate(state):
        """Start the dictation mode"""
        mode = DictateMode(state.nav, configuration["bindings"])
        state.enter_mode(mode, grab_keyboard=False)
        logger.info("entered dictation mode")

def say(word_count=1):
    """Dictate n words"""

    def _upd(state, n=word_count):
        """Start the dictation mode"""
        mode = DictateMode(state.nav, configuration["bindings"], word_count=n)
        state.enter_mode(mode, grab_keyboard=False)
        logger.info("entered say mode")

    return annotate(_upd, "say " + str(word_count))

commands.update(["say"])

class VoiceMode(Mode):
    def __init__(self, nav, conf):
        super().__init__(nav, conf)
        self.reset_mods()

    def reset_mods(self):
        self.nav.state.modifiers = {}

    def process(self, state, keys):
        if len(keys) == 0:
            return

        modifiers = self.nav.state.modifiers
        cmd = keys[0]
        if cmd in configuration["modifiers"]:
            mod = configuration["modifiers"][cmd]
            try:
                modifiers[mod] = True
                self.process(state, keys[1:])
            finally:
                try:
                    del modifiers[mod]
                except:
                    pass

        else:
            bindings = self.nav.state.get_current_bindings()
            if cmd in bindings.keys():
                action = bindings[cmd]
                for act in action:
                    act(self.nav.state)

                sleep(0.05)

                if state.mode:
                    mode = state.mode[-1]
                    mode.process(state, keys[1:])
            else:
                logger.warning("I don't understand '" + str(cmd) + "'")

    def apply(self, state):
        """Draw visualization of this mode on the screen"""

        label = draw.Label()
        label.x = 1000
        label.y = 500
        label.text = "test of the the solicitation more word whateversw"
        state.nav.draw(label)


class DictateMode(Mode):
    def __init__(self, nav, conf, word_count=0):
        super().__init__(nav, conf)
        self.first = True
        self.word_count = word_count

    def process(self, state, keys):
        if len(keys) == 0:
            return

        if self.word_count > 0:
            k = keys[:self.word_count]
            self.type(k)
            self.word_count -= len(k)
            if self.word_count == 0:
                state.exit_mode()
                logger.info("quitting say mode")

        elif keys[0] in configuration["dictate_end"]:
            state.exit_mode()
            logger.info("quitting dictation mode")
        else:
            self.type(keys)

    def type(self, keys):
        logger.debug("typing " + str(keys))
        text = str(" ".join(keys))
        if not self.first:
            text = " " + text
        self.first = False

        call(["xdotool", "type", text])


class VoiceNavigator(Navigator):
    """This class coordinates the input, the drawing, and the history.
    It is the entry point of YAKM"""

    def __init__(self, input_file):
        super().__init__()
        self.input_file = input_file

        self.grab_keyboard = lambda: None
        self.ungrab_keyboard = lambda: None

        # voice_mode = VoiceMode(self, configuration["bindings"])
        # self.state.enter_mode(voice_mode, grab_keyboard=False)

        self.label = draw.Label()
        self.label.x = 1000
        self.label.y = 500
        self.label.text = ""
        self.vis.draw(self.label)


        while True:
            try:
                line = self.readline()
            except KeyboardInterrupt:
                break

            if line == '': break
            if line == '\n': continue

            line = line[:-1]
            logger.trace(">" + str(line))

            self.label.text = line
            self.vis.draw(self.label)
            self.vis.refresh()

            # execute command
            if self.state.mode:
                mode = self.state.mode[-1]
                mode.process(self.state, line.split(' '))
            else:
                if line in configuration["bindings"]:
                    action = configuration["bindings"][line]
                    if action[0] == start:
                        for act in action:
                            act(self.state)
                else:
                    logger.error("unknown command: " + str(line))



        # TODO: exit on ctrl+c
        logger.info("exiting voice mode")
        self.vis.stop()


    def readline(self):
        prev = self.label.text
        line = ""
        while True:
            ch = self.input_file.read(1) #getch()
            if len(ch) == 0:
                return ""
            char = ord(ch)
            print(chr(char), end="", flush=True) # show input on terminal

            if char in {3,4}:
                raise KeyboardInterrupt
            elif 32 <= char <= 126:
                line += chr(char)
            elif char == ord('\r'):
                line = ""
            elif char == ord('\n'):
                return line + "\n"

            self.label.text = prev + "\n" + line
            self.vis.refresh()


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
        # https://stackoverflow.com/questions/3670323/setting-smaller-buffer-size-for-sys-stdin#comment55892838_3670470
        f = os.fdopen(sys.stdin.fileno(), 'rb', buffering=0)

    VoiceNavigator(f)

    eprint("closing")
    eprint("closing")
    eprint("closing")
    eprint("closing")
    eprint("closing")
    if f != sys.stdin:
        f.close()


    # stop application (incl. all threads)
    os._exit(1)


