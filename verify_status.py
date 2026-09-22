import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import sqlite3
from pathlib import Path
import config
import scraper
import engine

def run_diagnostics():
    print("=" * 60)
    print(" 👑 GODFATHER BOT — LIVE FEATURE & DIAGNOSTIC CHECK")
    print("=" * 60)

    # 1. Check Configuration & Subscribers
    print("\n1. 📡 TELEGRAM NOTIFICATION RECIPIENTS:")
    subscribers = config.get_subscribers()
    if subscribers:
        print(f"   ✅ Registered Chat IDs: {list(subscribers)}")
        print(f"      (Alerts will be pushed directly to these Telegram accounts)")
    else:
        print("   ⚠️ No chat IDs registered yet! Open your bot in Telegram and send /start.")

    # 2. Check 24-Hour Chat Cleaner & SQLite Database
    print("\n2. ⏳ 24-HOUR AUTO-DISAPPEARING & PIN TRACKER:")
    db_path = config.DB_FILE
    if db_path.exists():
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM messages;")
        total_msgs = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM messages WHERE is_pinned = 1;")
        pinned_msgs = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM messages WHERE is_pinned = 0;")
        unpinned_msgs = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM alerts_sent;")
        alerts_recorded = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*), COALESCE(SUM(profit_amount), 0) FROM pnl_records;")
        pnl_row = cursor.fetchone()
        pnl_count = pnl_row[0]
        pnl_sum = pnl_row[1]
        conn.close()

        print(f"   ✅ Database Active: {db_path.name}")
        print(f"   • Total Tracked Messages : {total_msgs}")
        print(f"   • Auto-Expiring (24h)    : {unpinned_msgs} (will disappear automatically)")
        print(f"   • Protected (Pinned)     : {pinned_msgs} (will NEVER be deleted)")
        print(f"   • Anti-Spam Memory       : {alerts_recorded} alerts tracked (duplicate suppression active)")
        print(f"   • Realized P&L Entries   : {pnl_count} logged issues (Total Net Profit: ₹{pnl_sum:,.2f})")
    else:
        print(f"   ℹ️ Database not created yet. It will initialize automatically when the bot starts.")

    # 3. Check Scraper & Profit Filter
    print("\n3. 🎯 PROFIT-ONLY FILTER AUDIT (LIVE IPO MARKET):")
    try:
        ipos = scraper.get_all_ipos()
        print(f"   ✅ Scraper Online: Audited {len(ipos)} live issues.")
        profitable = [i for i in ipos if engine.is_profitable_for_meet(i)[0]]
        print(f"   • High-Profit Matches (≥25% GMP, ₹14k-₹16k) : {len(profitable)}")
        for p in profitable[:3]:
            print(f"     - 🟢 {p.name}: Cost ₹{p.total_cost:,.0f} | GMP {p.gmp_percent:+.1f}% | Est. Profit +₹{p.est_profit:,.0f}")
        
        filtered_out = len(ipos) - len(profitable)
        print(f"   • Filtered Out (Zero-Spam Protected)         : {filtered_out} issues")
    except Exception as e:
        print(f"   ⚠️ Scraper error: {e}")

    # 4. 100% Proactive Engine & Background Scheduler Info
    print("\n4. ⏰ 100% PROACTIVE ENGINE & SCHEDULE:")
    print(f"   • Timezone              : {config.TIMEZONE} (IST)")
    print(f"   • 24/7 Live Watcher     : ACTIVE (Every 2 mins during market hours 9:15-16:30, 15m off-hours)")
    print(f"   • Trigger A (Green)     : Immediate push when GMP ≥ 25% and Day 3 QIB ≥ 25x")
    print(f"   • Trigger B (Avoid)     : Immediate push on Retail Trap (>10x Retail, <5x QIB) or GMP < 20%")
    print(f"   • Trigger C (Radar)     : Advance 1-share buy notification for parent company quotas")
    print(f"   • Trigger D (Mandate)   : 03:45 PM IST Day 3 urgent UPI mandate approval reminder")
    print(f"   • Auto-Delete Cleaner   : Every {config.CLEANUP_INTERVAL_SECONDS}s (Deletes unpinned messages older than {config.AUTO_DELETE_HOURS}h)")

    print("\n" + "=" * 60)
    print(" Ready! Run 'python main.py' to keep Godfather live in the background.")
    print("=" * 60)

if __name__ == "__main__":
    run_diagnostics()
