# 👑 GODFATHER — Dedicated AI IPO Intelligence & Execution Agent

> **Exclusive Agent for Meet Panchal**  
> Capital Discipline | Mathematically Favored Allotments | Zero Speculation

---

## 🎯 Strategic Objective
Protect Meet Panchal's capital (budget strictly capped at **₹14,000 to ₹16,000** for 1 Mainline Retail Lot) and ensure applications are placed **only** in high-conviction, mathematically favorable IPOs with high listing gains.

---

## 🛡️ The Godfather Protocol & Decision Matrix

1. **Budget Constraint:**
   - Strictly 1 Retail Lot (~₹14,000 to ₹16,000).
   - Never bid multiple lots under a single PAN (SEBI lottery model yields zero additional probability).
   - Strictly bid at the **Cut-off Price**.

2. **Hard No-Go Filters:**
   - **GMP Threshold:** Grey Market Premium must be **≥ 25% to 30%**. If GMP < 20%, immediate **AVOID - High Risk**.
   - **QIB Demand:** Day 3 QIB subscription must be **≥ 25x – 30x+** by 1:30 PM IST.
   - **Retail Trap Shield:** High Retail (>10x) with Cold QIB (<5x) is immediately flagged as **RETAIL TRAP: Do not apply**.

3. **Strategic Edges:**
   - **Shareholder Quota Radar:** Early alerts to buy 1 share of a listed parent company (e.g., Tata Motors, Bajaj Finance, NTPC, HDFC Bank) before the record date to unlock dual-quota applications (Shareholder + Retail).
   - **Bid Timing Window:** Strictly submit bids between **1:00 PM and 3:30 PM IST** on Day 3.
   - **UPI Mandate Panic Alert:** High-priority reminder at **3:45 PM IST** to approve the UPI mandate before the 4:30 PM technical cutoff.
   - **Listing Day Strategy:** Pre-open guidance at **9:15 AM** to lock in 100% listing profits or place defensive stop-losses.
   - **🤖 Automated Background Push Engine (Zero Manual Effort):**
     * **9:30 AM IST Morning Scan:** Scrapes newly announced/open IPOs, checks GMP trends, applies the Profit-Only Filter (GMP ≥ 25%, ₹14k-₹16k budget), and pushes direct actionable alerts to Meet.
     * **1:15 PM IST Day 3 Closing Alert:** Evaluates live Day 3 institutional QIB and retail subscriptions against the profit matrix.
     * **3:45 PM IST Mandate Panic Watchdog:** Reminds Meet to approve the UPI mandate before 4:30 PM IST.
     * **Zero Spam Policy:** Risky or low-GMP IPOs are silently logged and skipped.
   - **⏳ 24-Hour Auto-Disappearing Chat:** Bot automatically cleans up chat messages after 24 hours to keep the chat uncluttered. Any message pinned using Telegram's default pin feature is permanently preserved and protected from deletion.

---

## 📁 System Architecture

```text
├── config.py          # User profile, budget cap, filters, auto-delete settings
├── chat_cleaner.py    # SQLite message tracker & 24h auto-delete scheduler with pin shield
├── scraper.py         # Live IPOWatch GMP parser, NSE India live bidding API, shareholder radar
├── engine.py          # The Godfather Decision Matrix & Telegram blueprint generators
├── bot.py             # Telegram bot handlers, TrackedBot wrapper, interactive buttons
├── main.py            # Application entry point
├── test_chat_cleaner.py # Unit test suite for auto-delete and pin protection
└── .env               # Telegram bot token & credentials
```

---

## 🚀 Setup & Launch

1. **Configure Environment:**
   Ensure [`.env`](file:///.env) contains your Telegram bot token:
   ```env
   BOT_TOKEN=your_bot_token_here
   ADMIN_USER_ID=your_telegram_chat_id
   ```

2. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Start Godfather:**
   ```bash
   python main.py
   ```

---

## 💬 Bot Commands

- `/start` — Register Meet's Telegram chat and open the control panel
- `/force_scan` — Manually trigger the autonomous 100% Proactive Live Market Watcher audit
- `/pnl` — Personal P&L Tracker dashboard (realized returns, win rate, monthly breakdown)
- `/pnl add <IPO> <Amount>` — Log a realized listing profit (e.g., `/pnl add Bajaj Housing 18190`)
- `/ipos` or `/live` — List active mainline IPOs and quick verdict badges
- `/gmp` — Live GMP leaderboard sorted by % gain and profit per lot
- `/verdict <ipo>` — Full Godfather Decision Matrix evaluation and action checklist
- `/radar` — Shareholder Quota radar (parent companies & 1-share action)
- `/testalert` — Simulate the 4 live automated Godfather alerts
- `/rules` — Review the zero-effort rules and criteria
