import os
import json
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base Bot Config (Reads production or legacy env vars)
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN") or os.environ.get("BOT_TOKEN", "")
ADMIN_USER_ID = os.environ.get("TELEGRAM_CHAT_ID") or os.environ.get("ADMIN_USER_ID") or os.environ.get("CHAT_ID", "")

# Target User Profile
TARGET_USER = os.getenv("TARGET_USER", "Meet Panchal")

# Capital & Retail Lot Budget Constraints (Strictly 1 Mainline Retail Lot)
BUDGET_MIN = 14000
BUDGET_MAX = 16000

# The Godfather Decision Matrix Criteria
MIN_GMP_PERCENT = 25.0        # GMP must be >= 25% for Green Light
AVOID_GMP_PERCENT = 20.0      # GMP < 20% is immediate Avoid/High Risk
MIN_QIB_SUBSCRIPTION = 25.0   # Day 3 QIB must be >= 25x
RETAIL_TRAP_RETAIL = 10.0     # Retail > 10x
RETAIL_TRAP_QIB = 5.0         # QIB < 5x (Retail trap condition)

# Timezone & Schedule Settings
TIMEZONE = os.getenv("TIMEZONE", "Asia/Kolkata")

# Storage for dynamic notification subscribers
SUBSCRIBERS_FILE = Path(__file__).parent / "subscribers.json"

# Auto-Disappearing Chat Configuration (Default: 24 Hours)
AUTO_DELETE_HOURS = float(os.getenv("AUTO_DELETE_HOURS", "24"))
CLEANUP_INTERVAL_SECONDS = int(os.getenv("CLEANUP_INTERVAL_SECONDS", "60"))

# Database path (configurable for persistent volumes)
db_env = os.environ.get("DATABASE_PATH")
if db_env:
    DB_FILE = Path(db_env)
    DB_FILE.parent.mkdir(parents=True, exist_ok=True)
else:
    DB_FILE = Path(__file__).parent / "chat_history.db"

def get_subscribers() -> set:
    """Returns set of chat IDs to receive automated push alerts."""
    subscribers = set()
    
    # Check env TELEGRAM_CHAT_ID, ADMIN_USER_ID, or CHAT_ID
    for env_key in ["TELEGRAM_CHAT_ID", "ADMIN_USER_ID", "CHAT_ID"]:
        env_val = os.getenv(env_key)
        if env_val and env_val.strip():
            try:
                subscribers.add(int(env_val.strip()))
            except ValueError:
                pass

    if SUBSCRIBERS_FILE.exists():
        try:
            with open(SUBSCRIBERS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    for cid in data:
                        subscribers.add(int(cid))
        except Exception:
            pass
            
    return subscribers

def add_subscriber(chat_id: int):
    """Registers a chat ID to receive automated alerts."""
    subscribers = get_subscribers()
    subscribers.add(int(chat_id))
    try:
        with open(SUBSCRIBERS_FILE, "w", encoding="utf-8") as f:
            json.dump(list(subscribers), f)
    except Exception as e:
        print(f"Error saving subscriber: {e}")
