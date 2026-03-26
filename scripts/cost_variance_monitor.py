"""
Cost Variance Monitor

Monitors raw materials (RAWMATT, RAWMATNTE, RAWMATNT) and sends a Teams alert
when an item's Current Cost newly exceeds its Standard Cost.

Implements the same "High Water Mark" state logic as raw_material_monitor.py:
- On first run (no state file): baselines current violations without alerting.
- Subsequent runs: alerts only for NEWLY appearing items.
- A single card is sent listing all new violations.
"""

import sys
import json
import time
import argparse
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from secrets_loader import load_project_secrets
from db_pool import get_connection
from inventory_queries import fetch_cost_variance_items
from notifications.teams_notifier import send_cost_variance_alert, send_test_message
from logging_config import get_logger, setup_logging

LOGGER = get_logger(__name__)
setup_logging(enable_console=True, enable_file=True)

STATE_FILE = Path(__file__).parent.parent / "data" / "cost_variance_state.json"
RAW_MATERIAL_CLASSES = ["RAWMATT", "RAWMATNTE", "RAWMATNT", "CONTAINERS"]


def get_cost_variance_items() -> list[dict]:
    """Query GP for raw materials where CURRCOST > STNDCOST."""
    with get_connection() as conn:
        cursor = conn.cursor()
        rows, _ = fetch_cost_variance_items(cursor, RAW_MATERIAL_CLASSES)

    results = []
    for row in rows:
        results.append({
            "ITEMNMBR": row.ITEMNMBR.strip(),
            "ITEMDESC": (row.ITEMDESC or "").strip(),
            "ITMCLSCD": (row.ITMCLSCD or "").strip(),
            "STNDCOST": float(row.STNDCOST or 0),
            "CURRCOST": float(row.CURRCOST or 0),
        })
    return results


def load_state() -> dict:
    if not STATE_FILE.exists():
        return {}
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        LOGGER.error(f"Error loading state file: {e}")
        return {}


def save_state(state: dict):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        LOGGER.error(f"Error saving state file: {e}")


def main():
    parser = argparse.ArgumentParser(description="Cost Variance Monitor")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--interval", type=int, default=3600, help="Interval in seconds (default 1 hour)")
    parser.add_argument("--test", action="store_true", help="Send test notification")
    args = parser.parse_args()

    secrets = load_project_secrets()
    webhook_url = secrets.get("teams", {}).get("webhook_url")

    if args.test:
        if not webhook_url:
            print("No Teams webhook URL configured in secrets.toml")
            return
        print("Sending test message...")
        if send_test_message(webhook_url):
            print("Test message sent!")
        else:
            print("Failed to send test message.")
        return

    if not webhook_url:
        LOGGER.error("No Teams webhook URL configured. Exiting.")
        return

    LOGGER.info("Starting Cost Variance Monitor...")

    # Baseline on first run — suppress alerts for already-existing variances
    if not STATE_FILE.exists():
        LOGGER.info("State file not found. Initializing baseline state...")
        try:
            current_items = get_cost_variance_items()
            initial_state = {item["ITEMNMBR"]: datetime.now().isoformat() for item in current_items}
            save_state(initial_state)
            LOGGER.info(
                f"Baseline initialized with {len(initial_state)} items. "
                "Alerts suppressed for these existing variances."
            )
        except Exception as e:
            LOGGER.error(f"Error initializing baseline state: {e}")

    while True:
        try:
            current_items = get_cost_variance_items()
            current_map = {item["ITEMNMBR"]: item for item in current_items}

            previous_state = load_state()

            new_items = []
            new_state = {}

            for item_code, item_data in current_map.items():
                if item_code not in previous_state:
                    new_items.append(item_data)
                    new_state[item_code] = datetime.now().isoformat()
                else:
                    new_state[item_code] = previous_state[item_code]

            for old_code in previous_state:
                if old_code not in new_state:
                    LOGGER.info(f"Cost variance RESOLVED: {old_code}")

            if new_items:
                LOGGER.info(f"Found {len(new_items)} new cost variance item(s). Sending alert.")
                send_cost_variance_alert(new_items, webhook_url)
            else:
                LOGGER.info(f"No new cost variances. {len(current_items)} item(s) currently above standard cost.")

            save_state(new_state)

        except Exception as e:
            LOGGER.error(f"Error in monitor loop: {e}", exc_info=True)

        if args.once:
            break

        time.sleep(args.interval)


if __name__ == "__main__":
    main()
