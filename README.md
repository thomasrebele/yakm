yakm
======

"yakm" stands for Yet Another Keyboard Mouse (or, alternatively, You Are Killing my Mouse).
Yakm allows you to control your mouse from your keyboard.

Yakm is based on the ideas from [keynav](https://github.com/jordansissel/keynav) with additional features.


Installation
---

Dependencies:
* python3
* python3-xlib: `pip3 install python-xlib`
* python3-tk (only for the mark mode)


Configuration
---
An example configuration file for the QWERTY keyboard layout can be found in `example_qwerty.conf`.
Another example configuration is provided for the [Neo](http://neo-layout.org/) keyboard layout with the file `example_neo.conf`.


Modes
---

**Default mode:**
A red rectangle shows the current zone. 
It can be moved around and made smaller or larger.

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


Caveats
---

* Right click does not work in some programs (e.g., Evince)
* Left click does not work in some programs (e.g., XFCE panel)
* Drag and drop does not work in some programs (e.g., Zotero)
* Some commands of keynav are not yet implemented (e.g., grid-nav off/toggle, record, sh, cut-\*, ...)
* The drawing module could be improved. Currently it uses the external command `xrefresh` to remove previously drawn lines. This causes a noticable flickering.

