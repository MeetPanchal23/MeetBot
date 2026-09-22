import sys
import logging

# Ensure UTF-8 output on Windows consoles to prevent charmap/unicode errors
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

import config
from bot import create_bot_app

# Configure logging
logging.basicConfig(
    format="%(asctime)s - [%(levelname)s] - %(name)s: %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("GodfatherMain")

def main():
    print("""
    ========================================================
       [MEETBOT]: AI INVESTMENT & IPO INTELLIGENCE AGENT
       Client: Meet Panchal
       Strategy: 1 Retail Lot (Strictly Rs. 14,000 - 16,000)
       Hard Filters: GMP >= 25% | Day 3 QIB >= 25x
    ========================================================
    """)

    if not config.BOT_TOKEN or "your_bot_token" in config.BOT_TOKEN:
        logger.error("BOT_TOKEN is missing or invalid in .env! Please set your Telegram bot token.")
        sys.exit(1)

    logger.info("Initializing Godfather Telegram Application...")
    app = create_bot_app()

    logger.info("Godfather is online and polling. Press Ctrl+C to terminate.")
    try:
        app.run_polling(drop_pending_updates=False)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Godfather shut down gracefully.")

if __name__ == "__main__":
    main()
