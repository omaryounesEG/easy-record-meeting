# -*- coding: utf-8 -*-
"""Easy Record Meeting — entry point.

Run from source:      python omar_rec.py
Frozen build:         OMAR_REC.exe  (built by build_exe.bat / PyInstaller)

The DPI awareness and the AppUserModelID must be set *before* Tk creates its
windows, otherwise Windows scales the UI blurrily and shows the generic Python
icon in the taskbar.
"""

from __future__ import annotations

import os
import sys


def _bootstrap_windows() -> None:
    try:
        import ctypes

        try:                       # per-monitor DPI (Win 8.1+)
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            ctypes.windll.user32.SetProcessDPIAware()
        # Taskbar grouping + our own icon instead of python.exe's
        from easyrec import APP_ID
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
    except Exception:
        pass


def main() -> int:
    _bootstrap_windows()

    here = os.path.dirname(os.path.abspath(__file__))
    if here not in sys.path:
        sys.path.insert(0, here)

    import tkinter as tk

    from easyrec.app import EasyRecordApp

    root = tk.Tk()
    root.withdraw()
    app = EasyRecordApp(root)          # noqa: F841  (must stay referenced)
    root.deiconify()
    try:
        root.mainloop()
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
