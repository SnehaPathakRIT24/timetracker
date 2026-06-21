"""
Mac activity capture using AppKit / Quartz.
Captures active app name, window title, and browser URL.
"""

import subprocess
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

BROWSER_BUNDLE_IDS = {
    "com.google.Chrome": "chrome",
    "com.apple.Safari": "safari",
    "company.thebrowser.Browser": "arc",  # Arc
    "com.microsoft.edgemac": "edge",
    "com.brave.Browser": "brave",
    "org.mozilla.firefox": "firefox",
}


def get_active_app() -> Tuple[Optional[str], Optional[str]]:
    """Returns (app_name, bundle_id) of the frontmost application."""
    try:
        from AppKit import NSWorkspace
        ws = NSWorkspace.sharedWorkspace()
        app = ws.frontmostApplication()
        if app:
            return app.localizedName(), app.bundleIdentifier()
    except ImportError:
        pass
    except Exception as e:
        logger.debug(f"AppKit error: {e}")

    # Fallback via AppleScript
    try:
        script = 'tell application "System Events" to get name of first application process whose frontmost is true'
        result = subprocess.run(
            ["osascript", "-e", script], capture_output=True, text=True, timeout=3
        )
        if result.returncode == 0:
            return result.stdout.strip(), None
    except Exception as e:
        logger.debug(f"AppleScript app name fallback error: {e}")

    return None, None


def get_active_window_title() -> Optional[str]:
    """Get the title of the frontmost window via Quartz accessibility API."""
    try:
        import Quartz
        from AppKit import NSWorkspace

        ws = NSWorkspace.sharedWorkspace()
        app = ws.frontmostApplication()
        if not app:
            return None

        pid = app.processIdentifier()
        ax_app = Quartz.AXUIElementCreateApplication(pid)
        err, focused_window = Quartz.AXUIElementCopyAttributeValue(
            ax_app, "AXFocusedWindow", None
        )
        if err:
            # Try main window
            err, focused_window = Quartz.AXUIElementCopyAttributeValue(
                ax_app, "AXMainWindow", None
            )
        if err or not focused_window:
            return None
        err, title = Quartz.AXUIElementCopyAttributeValue(focused_window, "AXTitle", None)
        return title if not err else None
    except ImportError:
        pass
    except Exception as e:
        logger.debug(f"Quartz window title error: {e}")

    # AppleScript fallback
    try:
        script = '''
        tell application "System Events"
            set frontApp to first application process whose frontmost is true
            set appName to name of frontApp
            tell process appName
                try
                    return name of front window
                end try
            end tell
        end tell
        '''
        result = subprocess.run(
            ["osascript", "-e", script], capture_output=True, text=True, timeout=3
        )
        if result.returncode == 0:
            return result.stdout.strip() or None
    except Exception as e:
        logger.debug(f"AppleScript window title fallback error: {e}")

    return None


def get_browser_url(bundle_id: Optional[str]) -> Optional[str]:
    """Extract the active tab URL from supported browsers via AppleScript."""
    if not bundle_id:
        return None

    browser = BROWSER_BUNDLE_IDS.get(bundle_id)
    if not browser:
        return None

    scripts = {
        "chrome": '''tell application "Google Chrome" to return URL of active tab of front window''',
        "safari": '''tell application "Safari" to return URL of current tab of front window''',
        "arc": '''tell application "Arc" to return URL of active tab of front window''',
        "edge": '''tell application "Microsoft Edge" to return URL of active tab of front window''',
        "brave": '''tell application "Brave Browser" to return URL of active tab of front window''',
        "firefox": None,  # Firefox doesn't support AppleScript well
    }

    script = scripts.get(browser)
    if not script:
        return None

    try:
        result = subprocess.run(
            ["osascript", "-e", script], capture_output=True, text=True, timeout=3
        )
        if result.returncode == 0:
            url = result.stdout.strip()
            return url if url else None
    except Exception as e:
        logger.debug(f"Browser URL capture error ({browser}): {e}")

    return None


def capture_current_activity() -> dict:
    """Single snapshot: returns dict with app_name, window_title, url."""
    app_name, bundle_id = get_active_app()
    window_title = get_active_window_title()
    url = get_browser_url(bundle_id)

    return {
        "app_name": app_name or "Unknown",
        "window_title": window_title,
        "url": url,
    }
