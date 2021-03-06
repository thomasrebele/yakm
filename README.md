yakm
======

"yakm" stands for Yet Another Keyboard Mouse (or, alternatively, You Are Killing my Mouse).
Yakm allows you to control your mouse from your keyboard.

Yakm is based on the ideas from [keynav](https://github.com/jordansissel/keynav) with additional features.


Installation
---

Dependencies:
* python3
* GTK3 libraries for python (`python3-gi`, `gir1.2-gtk-3.0`)

Alternatively you can use the Xlib fallback mode:
* python3-xlib: `pip3 install python-xlib` and python3-tk (only for the mark mode)


Configuration
---
An example configuration file for the QWERTY keyboard layout can be found in `example_qwerty.conf`.
Another example configuration is provided for the [Neo](http://neo-layout.org/) keyboard layout with the file `example_neo.conf`.

Starting
---

To start Yakm, execute `python3 yakm.py`.
The following keyboard shortcuts are for the example configuration (QWERTY layout).
Press <kbd>Win</kbd>+<kbd>F</kbd> to activate the grid mode described below. 


Modes
---

**Default mode:**
A red rectangle shows the current zone. 
It can be moved around with <kbd>A</kbd>, <kbd>S</kbd>, <kbd>D</kbd>, and <kbd>F</kbd>.
Press <kbd>J</kbd>, <kbd>K</kbd>, and <kbd>L</kbd> for left, middle, and right click respectively.

**Grid mode:**
The zone is divided into rows and columns.
It supports grid navigation (first selecting a row, then selecting a column),
and dart navigation (directly selecting a cell by pressing a key).

**Mark mode:**
First, the user "bookmarks" a pixel on the screen as a letter, e.g., "a".
Then, the user may jump directly to that pixel by entering the mark mode and pressing key "a".


Commands
---

All commands are defined in the `commands` section of `yakm.py`.
The docstring of each command describes its purpose.

If you see a command like

    def warp(state):
        """Move the mouse to the middle of the zone"""

you can assign it to key "w" in your configuration file as follows:

    bindings = {
       # ...
       "w": warp,
    }

Note: You must not specify the `state` argument.

In the following example, the command takes an argument different from `state`: 

    def click(button):
        """Do a mouse click. 'button' is an integer specifying the mouse button:
        1: left, 2: middle, 3: right, 4/5: scroll"""

In that case, you have to specify it in the configuration file:

    bindings = {
       # ...
       "c": click(1),
    }

User interface
---

### Gtk
The Gtk user interface uses a GTK window. 
The shape of the window is modified, so that it only covers those pixels that are used for drawing the lines or labels.
This mimics the behavior of keynav (although keynav uses Xlib for this purpose). 
This module still contains some bugs that might cause fatal crashes.

### Xlib (fallback)
The Xlib user interface directly draws on the screen.
Currently it uses the external command `xrefresh` to remove previously drawn lines.
This causes a noticable flickering.

Caveats
---

* Right click does not work in some programs (e.g., Evince)
* Left click does not work in some programs (e.g., XFCE panel)
* Drag and drop does not work in some programs (e.g., Zotero)
* Key bindings are not updated when user executes a setxkbmap command
* YAKM does not react to 'xdotool key Left' in grid mode
* Programs started with 'sh' terminate after stopping YAKM
* Some commands of keynav are not yet implemented (e.g., grid-nav off/toggle, record, cut-\*, ...)

