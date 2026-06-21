#!/usr/bin/env python3
"""
TimeTracker Mac Agent
- Polls every 60 seconds
- Batches and uploads every 5 minutes
- Pause hotkey: Cmd+Shift+P for 30 minutes
- Runs on startup via launchd
"""

import os
import sys
import time
import uuid
import signal
import logging
import threading
import requests
from datetime import datetime, timedelta
from typing import Optional

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from agent.mac.activity_capture import capture_current_activity
from agent.common.local_db import init_db, buffer_record, get_pending_records, mark_synced, get_config, set_config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(os.path.expanduser("~/.timetracker/agent.log")),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

POLL_INTERVAL = 60       # seconds between captures
UPLOAD_INTERVAL = 300    # seconds between uploads (5 min)
PAUSE_DURATION = 1800    # 30 min pause

SERVER_URL = os.getenv("TRACKER_SERVER_URL", "http://localhost:8000")

# ── Config ────────────────────────────────────────────────────────────────────

def get_machine_id() -> str:
    mid = get_config("machine_id")
    if not mid:
        mid = str(uuid.uuid4())
        set_config("machine_id", mid)
    return mid


def get_member_id() -> Optional[int]:
    val = get_config("member_id")
    return int(val) if val else None


# ── State ──────────────────────────────────────────────────────────────────────

paused_until: Optional[datetime] = None
running = True


def is_paused() -> bool:
    global paused_until
    if paused_until and datetime.now() < paused_until:
        return True
    paused_until = None
    return False


def pause_tracking():
    global paused_until
    paused_until = datetime.now() + timedelta(seconds=PAUSE_DURATION)
    logger.info(f"Tracking paused until {paused_until.strftime('%H:%M:%S')}")


# ── Hotkey listener (Cmd+Shift+P) ─────────────────────────────────────────────

def _setup_hotkey():
    try:
        from pynput import keyboard

        HOTKEY = {keyboard.Key.cmd, keyboard.Key.shift, keyboard.KeyCode.from_char('p')}
        current_keys = set()

        def on_press(key):
            current_keys.add(key)
            if all(k in current_keys for k in HOTKEY):
                if is_paused():
                    global paused_until
                    paused_until = None
                    logger.info("Tracking resumed")
                else:
                    pause_tracking()

        def on_release(key):
            current_keys.discard(key)

        listener = keyboard.Listener(on_press=on_press, on_release=on_release)
        listener.daemon = True
        listener.start()
        logger.info("Hotkey listener started (Cmd+Shift+P to pause/resume)")
    except ImportError:
        logger.warning("pynput not installed — hotkey disabled")
    except Exception as e:
        logger.warning(f"Hotkey setup failed: {e}")


# ── Upload ────────────────────────────────────────────────────────────────────

def upload_pending(member_id: int, machine_id: str):
    records = get_pending_records(limit=300)
    if not records:
        return

    payload = {
        "team_member_id": member_id,
        "records": [
            {
                "timestamp": r["timestamp"],
                "app_name": r["app_name"],
                "window_title": r["window_title"],
                "url": r["url"],
                "duration_seconds": r["duration_seconds"],
                "machine_id": machine_id,
            }
            for r in records
        ],
    }

    try:
        resp = requests.post(
            f"{SERVER_URL}/activity",
            json=payload,
            timeout=15,
        )
        if resp.ok:
            mark_synced([r["id"] for r in records])
            logger.info(f"Uploaded {len(records)} records")
        else:
            logger.warning(f"Upload failed: {resp.status_code} {resp.text[:200]}")
    except requests.exceptions.ConnectionError:
        logger.debug("Server unreachable — records buffered locally")
    except Exception as e:
        logger.error(f"Upload error: {e}")


# ── Main loop ──────────────────────────────────────────────────────────────────

def main():
    global running

    init_db()
    machine_id = get_machine_id()
    member_id = get_member_id()

    if not member_id:
        logger.error(
            "No member_id configured. Run setup.sh first or set TRACKER_MEMBER_ID env var."
        )
        mid_env = os.getenv("TRACKER_MEMBER_ID")
        if mid_env:
            member_id = int(mid_env)
            set_config("member_id", mid_env)
        else:
            sys.exit(1)

    _setup_hotkey()

    def handle_signal(sig, frame):
        global running
        logger.info("Shutting down agent")
        running = False

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    last_upload = time.time()
    logger.info(f"TimeTracker agent started. Member ID: {member_id}, Machine: {machine_id}")

    while running:
        loop_start = time.time()

        if not is_paused():
            try:
                activity = capture_current_activity()
                buffer_record(
                    timestamp=datetime.now(),
                    app_name=activity["app_name"],
                    window_title=activity.get("window_title"),
                    url=activity.get("url"),
                    duration_seconds=POLL_INTERVAL,
                    machine_id=machine_id,
                )
            except Exception as e:
                logger.error(f"Capture error: {e}")
        else:
            logger.debug("Tracking paused — skipping capture")

        # Upload every 5 minutes
        if time.time() - last_upload >= UPLOAD_INTERVAL:
            try:
                upload_pending(member_id, machine_id)
            except Exception as e:
                logger.error(f"Upload cycle error: {e}")
            last_upload = time.time()

        # Sleep for remainder of poll interval
        elapsed = time.time() - loop_start
        sleep_time = max(0, POLL_INTERVAL - elapsed)
        time.sleep(sleep_time)

    # Final upload on shutdown
    upload_pending(member_id, machine_id)


if __name__ == "__main__":
    main()
