#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
"yakm" stands for Yet Another Keyboard Mouse (or, alternatively, You Are Killing my Mouse).
Yakm allows you to control your mouse from your keyboard.
You can find more information in the readme.
"""

# standard imports
import copy
import string
import json
import fcntl
from sys import exit
import subprocess
import os

import pathlib
import os.path
from collections import defaultdict

try:
    import ui_gtk as ui
except Exception as exception:
    print(exception)
    print("WARNING: GTK not available, trying Xlib user interface")

    import ui_xlib as ui

import input_devices
from common import *
logger = logger("yakm")




################################################################################
# commands
################################################################################

with command_definitions(lambda: globals()):

    def warp(state):
        """Move the mouse to the middle of the zone"""
        logger.debug("moving mouse to " + str(state.zone.x) + " " + str(state.zone.y))
        state.nav.move(state.zone.x, state.zone.y)

    def start(state):
        """Start the navigation. Enters the default mode if no other mode is active"""
        if not state.mode:
            state.enter_mode(Mode(state.nav, configuration["bindings"]))

        state.nav.grab_keyboard()

    def exit_mode(state):
        """Exit the current mode"""
        state.exit_mode()

    def end(state):
        """Exit all modes"""
        state.exit_mode(all_modes=True)


    def clear(state):
        """Clear all keybindings"""
        for k in state.nav.key_bindings():
            state.nav.input.unregister_key(k)

    def sh(command, state):
        """Execute a command"""
        try:
            pid = os.fork()
        except OSError as e:
            raise e
        if pid == 0:
            subprocess.Popen(command, shell=True, close_fds=True)
            os._exit(0)
        print("done")

    def info(state):
        """Write information about the current state to stdout"""
        logger.debug("bindings:")
        for key, action in state.nav.key_bindings().items():
            logger.debug("    key " + str(key) + " -> " + str(get_cmd(action)))
        win = state.nav.input.window()
        logger.debug("focused window: " + str(win))


    def ignore(_state):
        """This command does nothing"""
        pass


    def click(button, state):
        """Do a mouse click. 'button' is an integer specifying the mouse button:
        1: left, 2: middle, 3: right, 4/5: scroll"""

        state.nav.click(button)

    def drag(button, state):
        """Start or stop dragging. This simulates a pressed mouse button"""

        actions = ["release"] if state.drag else ["press"]
        state.drag = not state.drag
        state.nav.click(button, actions=actions)

    def move_to(x_coord, y_coord, state):
        """Move the center of the zone to the specified coordinates"""

        state.zone.x = x_coord
        state.zone.y = y_coord

    def move_left(ratio, state):
        """Move the zone left by ratio*width pixels"""

        state.zone.x = max(0, state.zone.x - state.zone.w * ratio)

    def move_right(ratio, state):
        """Move the zone right by ratio*width pixels"""

        state.zone.x = min(state.screen.width(), state.zone.x + state.zone.w * ratio)

    def move_up(ratio, state):
        """Move the zone up by ratio*height pixels"""

        state.zone.y = max(0, state.zone.y - state.zone.h * ratio)

    def move_down(ratio, state):
        """Move the zone down by ratio*height pixels"""

        state.zone.y = min(state.screen.height(), state.zone.y + state.zone.h * ratio)

    def full(state):
        """Make the zone use the whole screen"""

        state.zone.w = state.screen.width()
        state.zone.h = state.screen.height()
        state.zone.x = state.zone.w / 2
        state.zone.y = state.zone.h / 2

    def cursorzoom(width, height, state):
        """Set the size of the zone to width and height,
        and move it so that the pointer is at the center of the zone"""

        state.zone.w = width
        state.zone.h = height
        pointer = state.nav.pointer()
        state.zone.x = pointer.x
        state.zone.y = pointer.y

    def enlarge(factor, state):
        """Multiply the sides of the zone by factor.
        The center of the zone stays at the same position"""
        state.zone.w *= factor
        state.zone.h *= factor

    def grid(width, height, state):
        """Activate grid mode with a width x height cells"""
        state.grid.w = width
        state.grid.h = height
        state.enter_mode(GridMode(state.nav, configuration["bindings"]))


    def cell_select(col, row, state):
        """Set the zone to the cell with grid coordinates (col, row)"""
        if col > state.grid.w or row > state.grid.h:
            return

        left = state.zone.left() + col / state.grid.w  * state.zone.w
        top = state.zone.top() + row / state.grid.h  * state.zone.h

        state.zone.w = max(state.grid.w, state.zone.w / state.grid.w)
        state.zone.h = max(state.grid.h, state.zone.h / state.grid.h)
        state.zone.x = left + state.zone.w/2
        state.zone.y = top + state.zone.h/2

    # grid navigation
    def grid_nav(state):
        """Start grid navigation, i.e., use grid_nav_chars for selecting rows"""

        # switch to row selection mode
        state.grid_nav = "row"


    def row_select(row, state):
        """Select the specified row and activate column selection"""

        logger.debug("selecting row " +str(row))
        top = state.zone.top() + row / state.grid.h  * state.zone.h
        state.zone.y = top + 0.5 * state.zone.h / state.grid.h
        state.zone.h = max(state.grid.h, state.zone.h / state.grid.h)

        warp(state)

        # switch to col selection mode
        state.grid_nav = "col"


    def col_select(col, state):
        """Select the specified col"""

        logger.debug("selecting col " +str(col))
        left = state.zone.left() + col / state.grid.w  * state.zone.w
        state.zone.x = left + 0.5 * state.zone.w / state.grid.w
        state.zone.w = max(state.grid.w, state.zone.w / state.grid.w)

        warp(state)

        state.grid_nav = None
        grid_nav(state)



    def dart_nav(state):
        """Enter grid mode with dart navigation"""

        # switch to grid mode
        grid_width = len(configuration["dart_nav_chars"][0])
        grid_height = len(configuration["dart_nav_chars"])
        grid(grid_width, grid_height)(state)

        # switch to dart selection mode
        state.grid_nav = "dart"



    def history_back(state):
        """Roll back the navigation to the state before the last key stroke"""

        state.nav.undo_step()

    def record_mark(state):
        """Save the current pointer position as a mark
        associated with the next pressed letter"""

        state.enter_mode(MarkMode(state.nav, configuration["bindings"], record=True))

    def apply_mark(state):
        """On the next pressed letter, move the zone
        and the pointer to the position saved for that letter"""

        state.enter_mode(MarkMode(state.nav, configuration["bindings"]))


    def press_key(to_press, state):
        """Type a key or a key combination"""

        subprocess.call(["xdotool", "key", str(to_press)])


################################################################################
# behavior
################################################################################

class Size:
    """Class storing the size of a zone / window / screen /..."""
    def __init__(self):
        self.w = 0
        self.h = 0

    def __str__(self):
        return "size: " + str(self.w) + "," + str(self.h)

class ScreenSize:
    def __init__(self, ui):
        self.ui = ui
        self.width = ui.screen_width
        self.height = ui.screen_height

    def __str__(self):
        return "size: " + str(self.width()) + "," + str(self.height())

class State:
    """This class tracks the state of the navigation. This includes
    - the current zone: the region that the user selected
    - the modes: a stack of modes
    - the grid: how many rows and columns
    - whether the user is dragging
    """

    def __init__(self, nav):
        # references
        self.nav = nav
        self.screen = ScreenSize(nav.ui)

        # state
        self.mode = []
        self.zone = ui.Zone()
        self.grid = Size()
        self.grid.w = 1
        self.grid.h = 1
        self.drag = False
        self.grid_nav = None # or "row", or "col"
        self._settings = {} # settings for modes

    def __str__(self):
        result = "state: " + \
            "  zone " + str(self.zone) + \
            "  grid " + str(self.grid) + \
            " mode " + ",".join([str(i.__class__.__name__) for i in self.mode])
        return result

    def copy(self):
        """Create a copy of this state."""

        result = State(self.nav)
        result.screen = self.screen
        result.mode = self.mode[:]
        exclude = set(dir(State))
        exclude.update(["nav", "screen", "mode"])

        for attr in dir(self):
            if attr in exclude:
                continue
            setattr(result, attr, copy.deepcopy(getattr(self, attr)))
        return result

    def enter_mode(self, mode, grab_keyboard=True):
        """Enter a mode"""

        self.nav.ui.enable()
        if grab_keyboard:
            self.nav.grab_keyboard()

        self.mode += [mode]
        mode.enter(self)

    def exit_mode(self, all_modes=False):
        """Leave the currently active mode"""

        while self.mode:
            self.mode[-1].exit(self)
            self.mode = self.mode[:-1]
            if not all_modes:
                break

        if self.mode:
            self.mode[-1].enter(self)
        else:
            self.nav.ui.disable()
            self.nav.ui.refresh()
            self.nav.ungrab_keyboard()

    def get_current_bindings(self):
        bindings = {}
        for mode in self.mode:
            bindings = mode.get_bindings(self, bindings)
        return bindings

    def update(self, undoable=True):
        """Update the user interface and set the right mode"""

        if self.mode:
            self.mode[-1].apply(self)

        if undoable:
            self.nav.do_step(self)

    def settings(self, inst, default=None):
        """Save settings for a mode based on its class name."""
        if default is None:
            default = {}

        name = inst.__class__.__name__
        if not name in self._settings:
            self._settings[name] = default

        return self._settings[name]


class Mode:
    """A mode is a mapping from keys to actions with a visualization.
    The mapping is active if the mode is active.
    Modes can be nested."""

    def __init__(self, nav, conf):
        self.nav = nav
        self.conf = conf

    def apply(self, state):
        """Draw visualization of this mode on the screen"""

        state.nav.draw(state.zone)

    def get_bindings(self, _state, bindings=None):
        """Calculate the mapping from a key to an action for this mode.
        The dict 'bindings' contains binding of outer modes.
        If the mode allows to use functions from the outer modes,
        those should also appear in the returned mapping."""

        if bindings is None:
            bindings = {}

        bindings.update(self.conf)
        return bindings

    def update_bindings(self, state):
        """Activate the key bindings of this mode"""

        bindings = state.get_current_bindings()

        for key, action in bindings.items():
            # use state of navigation, so that we can undo actions
            def _upd(action=action, nav=state.nav):
                """wrap action in a lambda function"""

                # update zone if user has moved the cursor
                pointer = nav.pointer()
                if nav.prev_pointer != pointer:
                    nav.state.zone.x = pointer.x
                    nav.state.zone.y = pointer.y

                for act in action:
                    act(nav.state)

                if not history_back in action:
                    nav.state.update()

                # store cursor positions after our actions
                nav.prev_pointer = nav.pointer()

            _upd = annotate(_upd, get_cmd(action))
            state.nav.input.register_key(key, _upd)

    def enter(self, state):
        """This method is called when the user activates this mode"""

        self.update_bindings(state)
        state.nav.draw(state.zone)

    def exit(self, state):
        """This method is called when the user de-activates this mode"""

        # only unregister my keybindings
        # other keybindings are restored when entering previous mode
        for key, action in self.get_bindings(state).items():
            if not start in action:
                state.nav.input.unregister_key(key)

        state.nav.undraw()


class GridMode(Mode):
    """The grid mode draws a grid on the screen.
    Pressing a button restricts the current zone to a row, column or cell.

    There are two sub-modes:
    - normal: pressing a key in grid_nav_chars first selects the row, then the column
    - dart: pressing a key in dart_nav_chars directly jumps to the corresponding cell
    """

    def get_bindings(self, state, bindings=None):
        new_bindings = {}
        if state.grid_nav == "row":
            for row, key in enumerate(configuration["grid_nav_chars"]):
                new_bindings[key] = [row_select(row)]


        if state.grid_nav == "col":
            for col, key in enumerate(configuration["grid_nav_chars"]):
                new_bindings[key] = [col_select(col)]

        if state.grid_nav == "dart":
            for grid_row, keyboard_row in enumerate(configuration["dart_nav_chars"]):
                for grid_col, key in enumerate(keyboard_row):
                    # uggly hack
                    new_bindings[key] = [cell_select(grid_col, grid_row), warp]

        if bindings is None:
            return new_bindings

        bindings.update(new_bindings)
        return bindings

    def apply(self, state):
        # draw grid
        state.nav.ui.clear()
        enabled = state.nav.ui.is_enabled()

        # do we need this?
        if not enabled:
            return

        state.nav.ui.disable()
        self.update_bindings(state)

        # draw horizontal lines
        for grid_row, first_y, last_y in iter_first_last(range(state.grid.h+1)):
            # avoid drawing lines in grid if grid is very small
            horizontal_until_x = state.zone.right()
            if state.zone.w < state.grid.w * 30 and not first_y and not last_y:
                horizontal_until_x = state.zone.left() - 10

            if first_y or last_y or state.grid_nav is None or \
                    state.grid_nav == "row" or state.grid_nav == "dart":

                line = ui.Line()
                line.x1 = state.zone.left()
                line.x2 = horizontal_until_x

                line.y1 = state.zone.top() + grid_row * state.zone.h / state.grid.h
                line.y2 = line.y1
                state.nav.draw(line)

        # draw vertical lines
        for grid_col, first_x, last_x in iter_first_last(range(state.grid.w+1)):
            # avoid drawing lines in grid if grid is very small
            vertical_until_y = state.zone.bottom()
            if state.zone.h < state.grid.h * 30 and not first_x and not last_x:
                vertical_until_y = state.zone.top() - 10

            if first_x or last_x or state.grid_nav is None or \
                    state.grid_nav == "col" or state.grid_nav == "dart":

                line = ui.Line()
                line.x1 = state.zone.left() + grid_col * state.zone.w / state.grid.w
                line.x2 = line.x1

                line.y1 = state.zone.top()
                line.y2 = vertical_until_y
                state.nav.draw(line)

        if state.grid_nav == "row":
            delta = state.zone.h / state.grid.h
            for grid_row in range(state.grid.h):
                label = ui.Label()
                label.x = state.zone.left() + 0.5 * state.zone.w / state.grid.w
                label.y = state.zone.top() + (grid_row + 0.5) * delta
                label.text = str(configuration["grid_nav_chars"][grid_row])

                if label.size(state.nav.ui)[1] > delta:
                    break
                state.nav.draw(label)

        if state.grid_nav == "col":
            delta = state.zone.w / state.grid.w
            for grid_col in range(state.grid.w):
                label = ui.Label()
                label.x = state.zone.left() + (grid_col + 0.5) * delta
                label.y = state.zone.top() + 0.5 * state.zone.h / state.grid.h
                label.text = str(configuration["grid_nav_chars"][grid_col])

                if label.size(state.nav.ui)[0] > delta:
                    break
                state.nav.draw(label)

        if state.grid_nav == "dart":
            delta_x = state.zone.w / state.grid.w
            delta_y = state.zone.h / state.grid.h
            label = ui.Label()
            label.text = "Ig"
            if max(label.size(state.nav.ui)) < min(delta_x, delta_y):
                for grid_col in range(state.grid.w):
                    for grid_row in range(state.grid.h):
                        label = ui.Label()
                        label.x = state.zone.left() + (grid_col + 0.5) * delta_x
                        label.y = state.zone.top() + (grid_row + 0.5) * delta_y
                        label.text = str(configuration["dart_nav_chars"][grid_row][grid_col])
                        state.nav.draw(label)

        state.nav.ui.refresh()
        state.nav.ui.enable()

class MarkMode(Mode):
    """The mark mode allows the user to "bookmark" the current pointer position as a letter.

    There are two sub-modes:
    - record: pressing a letter saves the current position
    - otherwise: pressing a letter moves the pointer to the saved position
    """

    def __init__(self, nav, conf, record=False):
        self.nav = nav
        my_marks = self.marks()

        if not my_marks:
            try:
                with open(conf_dir + "marks", "r") as marks_file:
                    my_marks.update(json.loads(marks_file.read()))
            except FileNotFoundError:
                pass

        conf = {}
        if record:
            # currently only alphabetic marks
            for key in list(string.ascii_lowercase):
                def register(state, key=key):
                    """register a mark for the current pointer position"""

                    my_marks = self.marks()

                    win = self.nav.input.window()
                    msg = ("enter a filter for mark " + str(key) + "\n" +
                           "leave empty for global mark" + "\n\n" +
                           str(win).lower()
                          )
                    cond = nav.input_dialog(msg)

                    if cond != None:
                        my_marks[cond][key] = (state.zone.x, state.zone.y)

                register = annotate(register, "register '" + key + "'")
                conf[key] = [register, self.save, exit_mode]
        else:
            for key, coord in self.bindings().items():
                conf[key] = [move_to(coord[0], coord[1]), warp, exit_mode]

        super().__init__(nav, conf)

    def marks(self):
        """mapping from condition -> key -> action"""
        return self.nav.state.settings(self, defaultdict(lambda: dict()))

    def bindings(self):
        """get mapping from key -> action"""

        result = {}
        win = str(self.nav.input.window()).lower()
        for cond, bindings in self.marks().items():
            if not cond.lower() in str(win):
                continue
            result.update(bindings)
        logger.debug(result)
        return result

    def apply(self, state):
        # draw grid
        state.nav.undraw()
        enabled = state.nav.ui.is_enabled()
        state.nav.ui.disable()

        bindings = self.bindings()

        if not bindings:
            label = ui.Label()
            label.x = state.screen.width() / 2
            label.y = state.screen.height() / 2
            label.text = "no marks"
            state.nav.draw(label)

        for key, coord in bindings.items():
            label = ui.Label()
            label.x = coord[0]
            label.y = coord[1]
            label.text = key
            state.nav.draw(label)

        if enabled:
            state.nav.ui.enable()

    def save(self, _state):
        """save the current marks in a file in the config dir"""
        with open(conf_dir + "marks", "w") as marks_file:
            marks_file.write(json.dumps(self.marks(), indent=4, sort_keys=True))


class Navigator:
    def __init__(self):
        # components
        self.ui = ui.UserInterface()
        self.input = input_devices.Input()

        # state
        self.state = State(self)
        self.history = []

        # functions
        self.move = self.input.move
        self.click = self.input.click
        self.pointer = self.input.pointer
        self.prev_pointer = self.pointer()

        self.draw = self.ui.draw
        self.undraw = self.ui.undraw

        self.key_bindings = self.input.key_bindings
        self.grab_keyboard = self.input.grab_keyboard
        self.ungrab_keyboard = self.input.ungrab_keyboard

    def __del__(self):
        self.ui.stop()

    def do_step(self, state):
        """Add the current step to the history"""

        logger.debug("do " + str(state))
        # TODO: only add state if it has changed
        # something like
        #    if len(self.history) == 0: state != self.history[-1]:
        self.history.append(state.copy())

    def undo_step(self):
        """Undo last action, i.e., go back one step in history"""
        if len(self.history) > 1:
            del self.history[-1]
            self.state = self.history[-1].copy()
            self.state.update(undoable=False)

            logger.debug("roling back to state " + str(self.state))



class KeyNavigator(Navigator):
    """This class coordinates the input, the user interface, and the history.
    It is the entry point of YAKM"""

    def __init__(self):
        super().__init__()

        # setup bindings
        for key, action in configuration["bindings"].items():
            if start in action:
                def _upd(self=self, action=action):

                    self.state.enter_mode(Mode(self, configuration["bindings"]))
                    for act in action:
                        act(self.state)

                    self.state.update()

                self.input.register_key(key, _upd, _global=True)

    def input_dialog(self, msg=""):
        """Ask the user to type in text"""

        enabled = self.ui.is_enabled()
        self.ui.disable()
        self.ui.refresh()
        grabbing = self.input.grabbing
        self.ungrab_keyboard()

        text = self.ui.input_dialog(msg)

        if enabled:
            self.ui.enable()
        if grabbing:
            self.grab_keyboard()

        return text






if __name__ == '__main__':

    # check whether another instance is already running (https://stackoverflow.com/a/384493/1562506)
    pid_file = '/tmp/yakm.pid'
    fp = open(pid_file, 'w')
    try:
        fcntl.lockf(fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except IOError:
        # another instance is running
        print("Warning: another instance is already running, exiting")
        exit(0)

    logger.debug("available commands: %s", commands)

    ################################################################################
    # read configuration
    ################################################################################

    conf_dir = "~/.yakm/"
    script_dir = os.path.dirname(os.path.realpath(__file__))
    conf_file = script_dir + "/example_neo.conf" # TODO: resolve configuration path

    # setup configuration dir
    conf_dir = os.path.expanduser(conf_dir)
    pathlib.Path(conf_dir).mkdir(parents=True, exist_ok=True)

    # load configuration from file
    configuration = {}

    if os.path.isfile(conf_file):
        with open(conf_file, "r") as f_config:
            # we limit exec(...) to the above defined yakm commands
            exec_globals = {"__builtins__": None}
            _globals = globals()
            for i in commands:
                exec_globals[i] = _globals[i]

            # read configuration
            conf_str = f_config.read()
            exec(conf_str, exec_globals, configuration)
    else:
        print("WARNING: yakm could not open configuration file " + str(conf_file))

    ################################################################################
    # start
    ################################################################################

    KeyNavigator()
    logger.info("started ...")

