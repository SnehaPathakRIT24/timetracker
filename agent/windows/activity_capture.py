"""
Windows activity capture using pygetwindow + win32gui.
"""

import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

BROWSER_PROCESS_NAMES = {
    "chrome.exe": "chrome",
    "msedge.exe": "edge",
    "brave.exe": "brave",
    "firefox.exe": "firefox",
    "opera.exe": "opera",
}


def get_active_app_and_title() -> Tuple[Optional[str], Optional[str]]:
    """Returns (app_name, window_title) for the currently focused window."""
    try:
        import win32gui
        import win32process
        import psutil

        hwnd = win32gui.GetForegroundWindow()
        if not hwnd:
            return None, None

        title = win32gui.GetWindowText(hwnd)
        _, pid = win32process.GetWindowThreadProcessId(hwnd)

        try:
            proc = psutil.Process(pid)
            app_name = proc.name()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            app_name = "Unknown"

        return app_name, title or None
    except ImportError:
        logger.warning("win32gui/psutil not installed")
    except Exception as e:
        logger.debug(f"Windows capture error: {e}")

    return None, None


def get_browser_url(app_name: Optional[str]) -> Optional[str]:
    """
    Try to get the browser URL from Chrome/Edge via UI Automation.
    Requires pywinauto or uiautomation.
    """
    if not app_name:
        return None

    browser = BROWSER_PROCESS_NAMES.get(app_name.lower())
    if not browser:
        return None

    try:
        import uiautomation as auto

        # Chrome / Edge / Brave — all Chromium, same UI structure
        if browser in ("chrome", "edge", "brave"):
            # Find address bar
            ctrl = auto.EditControl(searchDepth=8, Name="Address and search bar")
            if ctrl.Exists(0, 0):
                return ctrl.GetValuePattern().Value or None
    except ImportError:
        pass
    except Exception as e:
        logger.debug(f"Browser URL capture error: {e}")

    return None


def capture_current_activity() -> dict:
    app_name, window_title = get_active_app_and_title()
    url = get_browser_url(app_name)
    return {
        "app_name": app_name or "Unknown",
        "window_title": window_title,
        "url": url,
    }
