#!/usr/bin/env python3
"""
TimeTracker Windows Agent
Pause hotkey: Ctrl+Shift+P
"""

import os
import sys
import time
import uuid
import signal
import logging
import requests
from datetime import datetime, timedelta
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from agent.windows.activity_capture import capture_current_activity
from agent.common.local_db import (
    init_db, buffer_record, get_pending_records, mark_synced,
    get_config, set_config
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(os.path.expandvars(r"%APPDATA%\TimeTracker\agent.log")),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

POLL_INTERVAL = 60
UPLOAD_INTERVAL = 300
PAUSE_DURATION = 1800

SERVER_URL = os.getenv("TRACKER_SERVER_URL", "http://localhost:8000")

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


def get_machine_id() -> str:
    mid = get_config("machine_id")
    if not mid:
        mid = str(uuid.uuid4())
        set_config("machine_id", mid)
    return mid


def get_member_id() -> Optional[int]:
    val = get_config("member_id")
    return int(val) if val else None


def _setup_hotkey():
    try:
        import keyboard
        keyboard.add_hotkey("ctrl+shift+p", lambda: pause_tracking() if not is_paused() else None)
        logger.info("Hotkey registered: Ctrl+Shift+P")
    except ImportError:
        logger.warning("keyboard package not installed — hotkey disabled")
    except Exception as e:
        logger.warning(f"Hotkey setup failed: {e}")


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
        resp = requests.post(f"{SERVER_URL}/activity", json=payload, timeout=15)
        if resp.ok:
            mark_synced([r["id"] for r in records])
            logger.info(f"Uploaded {len(records)} records")
        else:
            logger.warning(f"Upload failed: {resp.status_code}")
    except requests.exceptions.ConnectionError:
        logger.debug("Server unreachable — buffered locally")
    except Exception as e:
        logger.error(f"Upload error: {e}")


def main():
    global running

    # Create log dir
    log_dir = os.path.expandvars(r"%APPDATA%\TimeTracker")
    os.makedirs(log_dir, exist_ok=True)

    init_db()
    machine_id = get_machine_id()
    member_id = get_member_id()

    if not member_id:
        mid_env = os.getenv("TRACKER_MEMBER_ID")
        if mid_env:
            member_id = int(mid_env)
            set_config("member_id", mid_env)
        else:
            logger.error("No member_id. Run setup.bat first.")
            sys.exit(1)

    _setup_hotkey()

    def handle_signal(sig, frame):
        global running
        running = False

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    last_upload = time.time()
    logger.info(f"TimeTracker agent started. Member: {member_id}")

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

        if time.time() - last_upload >= UPLOAD_INTERVAL:
            upload_pending(member_id, machine_id)
            last_upload = time.time()

        elapsed = time.time() - loop_start
        time.sleep(max(0, POLL_INTERVAL - elapsed))

    upload_pending(member_id, machine_id)


if __name__ == "__main__":
    main()
