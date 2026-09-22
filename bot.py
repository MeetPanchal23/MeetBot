import os
import sys
import asyncio
import logging
import datetime
from pathlib import Path
from typing import List

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")
import pytz
import schedule
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    ExtBot,
    filters
)

import config
import scraper
import engine
import chat_cleaner

# Setup Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("GodfatherBot")

class TrackedBot(ExtBot):
    """Custom ExtBot that automatically logs all outgoing messages for 24h auto-deletion."""
    async def send_message(self, *args, **kwargs):
        msg = await super().send_message(*args, **kwargs)
        if msg and msg.chat and msg.message_id:
            sent_at = msg.date.timestamp() if msg.date else None
            chat_cleaner.record_message(msg.chat.id, msg.message_id, sent_at=sent_at)
        return msg

    async def send_photo(self, *args, **kwargs):
        msg = await super().send_photo(*args, **kwargs)
        if msg and msg.chat and msg.message_id:
            sent_at = msg.date.timestamp() if msg.date else None
            chat_cleaner.record_message(msg.chat.id, msg.message_id, sent_at=sent_at)
        return msg

    async def send_document(self, *args, **kwargs):
        msg = await super().send_document(*args, **kwargs)
        if msg and msg.chat and msg.message_id:
            sent_at = msg.date.timestamp() if msg.date else None
            chat_cleaner.record_message(msg.chat.id, msg.message_id, sent_at=sent_at)
        return msg

async def incoming_message_tracker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tracks incoming user messages and detects Telegram's native pin actions."""
    if not update.effective_chat or not update.effective_message:
        return
    chat_id = update.effective_chat.id
    msg = update.effective_message

    # Detect if message is a pin service notification
    if msg.pinned_message:
        chat_cleaner.mark_message_pinned(chat_id, msg.pinned_message.message_id, is_pinned=True)
        logger.info(f"User pinned message {msg.pinned_message.message_id} in chat {chat_id}. Marked to stay permanently.")

    # Record message for 24h expiration
    sent_at = msg.date.timestamp() if msg.date else None
    chat_cleaner.record_message(chat_id, msg.message_id, sent_at=sent_at)


def get_broker_apply_keyboard() -> InlineKeyboardMarkup:
    """One-Click Broker Deep-Links for Green Light Action Alerts (Groww & Angel One)."""
    keyboard = [
        [
            InlineKeyboardButton("🚀 Apply on Groww", url="https://groww.in/ipo"),
            InlineKeyboardButton("🚀 Apply on Angel One", url="https://www.angelone.in/ipo"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_main_keyboard() -> InlineKeyboardMarkup:
    """Standard quick-action buttons for Meet."""
    keyboard = [
        [
            InlineKeyboardButton("⚡ Force Live Scan", callback_data="cmd_force_scan"),
            InlineKeyboardButton("🎩 Secretary Briefing", callback_data="cmd_secretary"),
        ],
        [
            InlineKeyboardButton("🔥 Live IPOs", callback_data="cmd_ipos"),
            InlineKeyboardButton("📈 GMP Tracker", callback_data="cmd_gmp"),
        ],
        [
            InlineKeyboardButton("🏢 Shareholder Radar", callback_data="cmd_radar"),
            InlineKeyboardButton("💰 My P&L Tracker", callback_data="cmd_pnl"),
        ],
        [
            InlineKeyboardButton("🚨 Test Alert", callback_data="cmd_testalert"),
            InlineKeyboardButton("🧹 Clear Chat", callback_data="cmd_clear"),
        ],
        [
            InlineKeyboardButton("ℹ️ Operational Rules", callback_data="cmd_rules"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Welcomes Meet and registers his chat ID for automated push alerts."""
    chat_id = update.effective_chat.id
    config.add_subscriber(chat_id)
    
    welcome_text = (
        f"👑 <b>MEETBOT IS ONLINE | {config.TARGET_USER.upper()}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Meet, your dedicated AI IPO Intelligence & Execution Agent is active.\n"
        f"🤖 <b>100% Proactive Live Watcher:</b> Active 24/7 with zero SME protection and instant broker deep-links!\n\n"
        f"🛡️ <b>Core Directives:</b>\n"
        f"• Capital Limit: <b>Strictly ₹14,000 – ₹16,000</b> (1 Mainline Retail Lot)\n"
        f"• Execution Strategy: <b>Cut-off Price only</b> (SEBI lottery model)\n"
        f"• Hard Filters: <b>GMP ≥ 25%</b> & <b>Day 3 QIB ≥ 25x</b>\n"
        f"• Retail Trap Defense: High Retail (&gt;10x) with Cold QIB (&lt;5x) is an immediate <b>AVOID</b>\n"
        f"• Shareholder Quota Radar: Early alerts to buy 1 parent share for double quota\n"
        f"• 💰 <b>P&L Tracking:</b> Track your listing returns with <code>/pnl</code>\n"
        f"• ⏳ <b>Auto-Clean:</b> Chats auto-disappear after 24h. Pin any message in Telegram to keep it!\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )
    avatar_path = Path(__file__).parent / "assets" / "meetbot_avatar.jpg"
    if avatar_path.exists():
        try:
            with open(avatar_path, "rb") as photo_file:
                await update.message.reply_photo(
                    photo=photo_file,
                    caption=welcome_text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=get_main_keyboard()
                )
                return
        except Exception as e:
            logger.warning(f"Could not send avatar photo: {e}")

    await update.message.reply_text(
        welcome_text,
        parse_mode=ParseMode.HTML,
        reply_markup=get_main_keyboard()
    )

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays available commands."""
    help_text = (
        f"📋 <b>MEETBOT COMMAND DIRECTORY</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"• <b>/start</b> — Initialize MeetBot & open control panel\n"
        f"• <b>/force_scan</b> — Instantly audit live market & push proactive triggers\n"
        f"• <b>/pnl</b> — View lifetime realized listing profits & win rates\n"
        f"• <b>/pnl add &lt;IPO&gt; &lt;Amount&gt;</b> — Log realized listing profit (e.g. /pnl add Bajaj Housing 18190)\n"
        f"• <b>/secretary_test</b> — Immediate proactive briefing from Meet's Financial Secretary\n"
        f"• <b>/clear</b> — Instantly clear chat in 1-2s (pinned messages stay safe)\n"
        f"• <b>/scan</b> — On-demand market scan against Godfather Profit Matrix\n"
        f"• <b>/ipos</b> or <b>/live</b> — List active mainline IPOs & quick verdicts\n"
        f"• <b>/gmp</b> — Live Grey Market Premium ranking table\n"
        f"• <b>/verdict &lt;ipo_name&gt;</b> — Instant MeetBot Decision & Action Checklist\n"
        f"• <b>/radar</b> — Shareholder Quota Radar (Parent company opportunities)\n"
        f"• <b>/testalert</b> — Push simulated live Godfather Direct Push Alert\n"
        f"• <b>/rules</b> — The MeetBot Investment Protocol\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )
    await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)

async def cmd_ipos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lists current and upcoming mainline IPOs."""
    msg_target = update.message if update.message else update.callback_query.message
    await msg_target.reply_text("🔄 <i>MeetBot is auditing current IPOs...</i>", parse_mode=ParseMode.HTML)

    ipos = scraper.get_all_ipos()
    if not ipos:
        await msg_target.reply_text("⚠️ No mainline IPOs actively detected in current cycle.")
        return

    lines = [
        f"👑 <b>CURRENT MAINLINE IPOS | {config.TARGET_USER.upper()}</b>",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    ]
    for ipo in ipos[:8]:
        verdict, _, _ = engine.evaluate_ipo(ipo)
        badge = "🟢 APPLY" if "APPLY" in verdict else ("🔴 AVOID" if "AVOID" in verdict else "🟡 WATCH")
        quota = "🏢 [Quota Available]" if ipo.shareholder_quota else ""
        lines.append(
            f"📌 <b>{ipo.name}</b>\n"
            f"   • Cost: ₹{ipo.total_cost:,.0f} | GMP: ₹{ipo.gmp:,.0f} ({ipo.gmp_percent:+.1f}%)\n"
            f"   • Day {ipo.current_day} QIB: {ipo.qib_sub:.1f}x | Retail: {ipo.retail_sub:.1f}x\n"
            f"   • Verdict: <b>{badge}</b> {quota}\n"
            f"   • Quick Check: <code>/verdict {ipo.name.split()[0]}</code>\n"
        )
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("💡 <i>Tap any quick command or type /verdict &lt;name&gt; for full blueprint.</i>")

    await msg_target.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)

async def cmd_gmp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays live GMP leaderboard sorted by estimated listing gain %."""
    msg_target = update.message if update.message else update.callback_query.message
    ipos = scraper.get_all_ipos()
    # Sort by GMP % descending
    sorted_ipos = sorted(ipos, key=lambda x: x.gmp_percent, reverse=True)

    lines = [
        f"📈 <b>LIVE GREY MARKET PREMIUM (GMP) LEADERBOARD</b>",
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    ]
    for idx, ipo in enumerate(sorted_ipos[:8], 1):
        status_icon = "🟢" if ipo.gmp_percent >= config.MIN_GMP_PERCENT else ("🔴" if ipo.gmp_percent < config.AVOID_GMP_PERCENT else "🟡")
        lines.append(
            f"{idx}. {status_icon} <b>{ipo.name}</b>\n"
            f"   • Price: ₹{ipo.upper_price:,.0f} | GMP: <b>₹{ipo.gmp:,.0f}</b> ({ipo.gmp_percent:+.1f}%)\n"
            f"   • Est. Lot Profit: <b>+₹{ipo.est_profit:,.0f}</b> (Lot: {ipo.lot_size} sh.)\n"
        )
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("🛡️ <i>MeetBot Rule: Only IPOs with GMP ≥ 25% pass to the final QIB filter.</i>")

    await msg_target.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)

async def cmd_verdict(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Executes the complete decision matrix and sends the Blueprint alert."""
    msg_target = update.message if update.message else update.callback_query.message
    query = " ".join(context.args) if context.args else ""
    
    if not query:
        # Default to highest profile active IPO
        ipos = scraper.get_all_ipos()
        if ipos:
            ipo = ipos[0]
        else:
            await msg_target.reply_text("Please specify IPO name: e.g. <code>/verdict Bajaj</code>", parse_mode=ParseMode.HTML)
            return
    else:
        ipo = scraper.get_ipo_by_name(query)
        if not ipo:
            await msg_target.reply_text(f"❌ IPO '{query}' not found. Check <code>/ipos</code> for available issues.", parse_mode=ParseMode.HTML)
            return

    blueprint_msg = engine.generate_blueprint_alert(ipo)
    await msg_target.reply_text(blueprint_msg, parse_mode=ParseMode.HTML)

async def cmd_radar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shareholder Quota radar to capture double-application advantage."""
    msg_target = update.message if update.message else update.callback_query.message
    ipos = scraper.get_all_ipos()
    quota_ipos = [i for i in ipos if i.shareholder_quota and i.parent_company]

    lines = [
        f"🏢 <b>SHAREHOLDER QUOTA RADAR | {config.TARGET_USER.upper()}</b>",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "🎯 <i>The MeetBot Strategic Edge: Applying in both Retail Quota AND Shareholder Quota gives Meet double allotment odds mathematically!</i>\n"
    ]

    if not quota_ipos:
        lines.append("ℹ️ No current IPOs have listed parent companies.")
    else:
        for ipo in quota_ipos:
            lines.append(
                f"📌 <b>{ipo.name}</b>\n"
                f"• Listed Parent: <b>{ipo.parent_company}</b>\n"
                f"• Status: Bidding {ipo.open_date} - {ipo.close_date}\n"
                f"⚡ <b>ACTION FOR MEET:</b> Buy <b>1 share</b> of {ipo.parent_company} before the record date to qualify!\n"
            )
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    await msg_target.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)

async def cmd_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Explains the zero-effort rules for Meet."""
    msg_target = update.message if update.message else update.callback_query.message
    rules_text = (
        f"🛡️ <b>THE MEETBOT PROTOCOL FOR {config.TARGET_USER.upper()}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"1. <b>Strict Budget:</b> ₹14,000 to ₹16,000 max (1 Retail Lot).\n"
        f"2. <b>Cut-off Price:</b> Never enter custom bid prices. Always check 'Cut-off Price'.\n"
        f"3. <b>One Lot Per PAN:</b> Multiple lots under 1 PAN give zero extra odds under SEBI's lottery rules.\n"
        f"4. <b>GMP Gate:</b> Must be ≥ 25% – 30%. Anything &lt; 20% is AVOID.\n"
        f"5. <b>QIB Gate:</b> Must be ≥ 25x on Day 3 by 1:30 PM.\n"
        f"6. <b>Retail Trap Shield:</b> Retail &gt; 10x with QIB &lt; 5x is rejected immediately.\n"
        f"7. <b>Bid Timing:</b> Bid strictly between 1:00 PM and 3:30 PM on Day 3.\n"
        f"8. <b>UPI Mandate Watchdog:</b> Approve mandate by 4:30 PM IST sharp.\n"
        f"9. <b>Auto-Disappearing Chat:</b> Messages auto-delete after 24 hours. Pin any message using Telegram's built-in pin feature to keep it permanently.\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )
    await msg_target.reply_text(rules_text, parse_mode=ParseMode.HTML)

async def cmd_force_scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Manually triggers the autonomous 100% Proactive Live Market Watcher audit.
    Evaluates live issues against Trigger A (Green Light), Trigger B (Retail Trap),
    Trigger C (Shareholder Quota Radar), and Trigger D (Mandate Reminder).
    Pushes triggered alerts to Meet's chat and provides an audit summary.
    """
    msg_target = update.message if update.message else update.callback_query.message
    chat_id = update.effective_chat.id
    config.add_subscriber(chat_id)

    # Allow /force_scan reset to wipe memory for testing
    if context.args and context.args[0].lower() == "reset":
        chat_cleaner.clear_alerts_memory()
        await msg_target.reply_text("🧹 <i>Anti-spam alert memory reset. All triggers will re-evaluate from scratch.</i>", parse_mode=ParseMode.HTML)

    await msg_target.reply_text("⚡ <i>Godfather 100% Proactive Live Engine is auditing live market right now...</i>", parse_mode=ParseMode.HTML)

    stats = await execute_live_market_scan(context.application, is_forced=False, requesting_chat_id=chat_id)

    summary_lines = [
        f"👑 <b>GODFATHER AUTONOMOUS LIVE AUDIT COMPLETE</b>",
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"• <b>Live Issues Audited:</b> {stats['total_scanned']}",
        f"• <b>Green Light (High Conviction):</b> {stats['green_light']}",
        f"• <b>Retail Traps / High Risk:</b> {stats['retail_trap']}",
        f"• <b>Shareholder Quota Radars:</b> {stats['shareholder_radar']}",
        f"• <b>Fresh Alerts Pushed to Meet:</b> {stats['dispatched']}",
        f"• <b>Anti-Spam Memory Suppressed:</b> {stats['suppressed']}",
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"🛡️ <i>The engine runs 24/7 autonomously in the background. You do not need to check manually — Meet will receive instant alerts the moment market criteria match!</i>\n",
        f"💡 <i>Tip: Type <code>/force_scan reset</code> to clear alert memory and re-trigger demo alerts.</i>"
    ]
    await msg_target.reply_text("\n".join(summary_lines), parse_mode=ParseMode.HTML)

async def execute_live_market_scan(app: Application, is_forced: bool = False, requesting_chat_id: int = None) -> dict:
    """
    Scans live market, evaluates proactive triggers against anti-spam memory,
    and pushes real-time alerts immediately to Meet's Telegram.
    Returns audit statistics.
    """
    stats = {
        "total_scanned": 0,
        "green_light": 0,
        "retail_trap": 0,
        "shareholder_radar": 0,
        "dispatched": 0,
        "suppressed": 0,
        "details": []
    }

    try:
        ipos = await asyncio.to_thread(scraper.get_all_ipos, force_refresh=True)
        stats["total_scanned"] = len(ipos)

        tz = pytz.timezone(config.TIMEZONE)
        now = datetime.datetime.now(tz)
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M")

        # Capital Allocation Prioritizer check across active profitable IPOs
        profitable_issues = [
            i for i in ipos 
            if i.gmp_percent >= config.MIN_GMP_PERCENT 
            and i.qib_sub >= config.MIN_QIB_SUBSCRIPTION 
            and config.BUDGET_MIN <= i.total_cost <= (config.BUDGET_MAX + 1000)
        ]
        capital_directive = engine.prioritize_capital_allocation(profitable_issues) if len(profitable_issues) > 1 else ""

        for ipo in ipos:
            trigger_type, alert_msg = engine.evaluate_proactive_triggers(ipo)
            if not trigger_type or not alert_msg:
                continue

            reply_markup = None
            if trigger_type == "GREEN_LIGHT":
                stats["green_light"] += 1
                # 1. ONE-CLICK BROKER DEEP-LINKS
                reply_markup = get_broker_apply_keyboard()
                # 2. CAPITAL ALLOCATION PRIORITIZER
                if capital_directive:
                    alert_msg += f"\n\n{capital_directive}"
            elif "TRAP" in trigger_type or "AVOID" in trigger_type:
                stats["retail_trap"] += 1
            elif "SHAREHOLDER" in trigger_type:
                stats["shareholder_radar"] += 1

            # Check anti-spam memory
            should_send = chat_cleaner.should_dispatch_alert(
                ipo_name=ipo.name,
                trigger_type=trigger_type,
                current_gmp=ipo.gmp_percent,
                current_qib=ipo.qib_sub
            )

            if should_send:
                # Dispatch immediately to subscribers with broker links if green light
                await broadcast_message(app, alert_msg, reply_markup=reply_markup)
                chat_cleaner.record_alert_dispatched(
                    ipo_name=ipo.name,
                    trigger_type=trigger_type,
                    current_gmp=ipo.gmp_percent,
                    current_qib=ipo.qib_sub,
                    current_retail=ipo.retail_sub,
                    current_status=ipo.status
                )
                stats["dispatched"] += 1
                stats["details"].append(f"🟢 [DISPATCHED] {trigger_type} for {ipo.name}")
            else:
                stats["suppressed"] += 1
                stats["details"].append(f"🛡️ [SUPPRESSED] {trigger_type} for {ipo.name}")

        # Trigger D check: Mandate Deadline on Day 3 (approx 3:45 PM IST)
        if "15:40" <= time_str <= "16:15":
            for ipo in ipos:
                if (ipo.current_day == 3 or ipo.status.lower() == "active") and ipo.gmp_percent >= config.MIN_GMP_PERCENT:
                    mandate_key = f"MANDATE_{date_str}"
                    if chat_cleaner.should_dispatch_alert(ipo.name, mandate_key):
                        mandate_msg = engine.generate_proactive_mandate_alert(ipo.name)
                        await broadcast_message(app, mandate_msg)
                        chat_cleaner.record_alert_dispatched(
                            ipo_name=ipo.name,
                            trigger_type=mandate_key,
                            current_gmp=ipo.gmp_percent,
                            current_qib=ipo.qib_sub,
                            current_retail=ipo.retail_sub,
                            current_status=ipo.status
                        )
                        stats["dispatched"] += 1

        # Trigger E check: Refund / Unblock Watchdog (Post-Allotment)
        for ipo in ipos:
            if ipo.status.lower() in ["closed", "listed"]:
                refund_key = f"REFUND_{ipo.name}"
                if chat_cleaner.should_dispatch_alert(ipo.name, refund_key):
                    refund_msg = engine.generate_refund_unblock_alert(ipo.name)
                    await broadcast_message(app, refund_msg)
                    chat_cleaner.record_alert_dispatched(
                        ipo_name=ipo.name,
                        trigger_type=refund_key,
                        current_gmp=ipo.gmp_percent,
                        current_qib=ipo.qib_sub,
                        current_retail=ipo.retail_sub,
                        current_status=ipo.status
                    )
                    stats["dispatched"] += 1
                    stats["details"].append(f"💸 [REFUND WATCHDOG] {ipo.name}")

    except Exception as e:
        logger.error(f"Error during live market scan: {e}", exc_info=True)
        stats["error"] = str(e)

    return stats

async def cmd_pnl(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Personal P&L Tracker for Meet Panchal.
    Displays lifetime realized profits, win count, monthly breakdown,
    and supports: /pnl add <IPO Name> <Amount>
    """
    msg_target = update.message if update.message else update.callback_query.message
    chat_id = update.effective_chat.id
    config.add_subscriber(chat_id)

    args = context.args if context.args else []

    # Handle /pnl add <Name> <Amount>
    if len(args) >= 3 and args[0].lower() == "add":
        try:
            amount_str = args[-1].replace(",", "").replace("+", "").replace("₹", "")
            profit_amount = float(amount_str)
            ipo_name = " ".join(args[1:-1])

            chat_cleaner.record_pnl_entry(ipo_name, profit_amount)
            pnl = chat_cleaner.get_pnl_summary()

            reply = (
                f"🎉 <b>IPO LISTING PROFIT RECORDED!</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"• <b>IPO:</b> <b>{ipo_name}</b>\n"
                f"• <b>Realized Gain:</b> <b>+₹{profit_amount:,.2f}</b>\n"
                f"• <b>New Lifetime Net Profit:</b> <b>₹{pnl['total_profit']:,.2f}</b>\n"
                f"• <b>Total Successful Issues:</b> {pnl['total_trades']}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"Capital protected, gains locked in! Keep building wealth, Meet! 👑"
            )
            await msg_target.reply_text(reply, parse_mode=ParseMode.HTML)
            return
        except ValueError:
            await msg_target.reply_text("⚠️ Invalid amount format. Example: <code>/pnl add Bajaj Housing 18190</code>", parse_mode=ParseMode.HTML)
            return

    # View P&L Summary Dashboard
    pnl = chat_cleaner.get_pnl_summary()
    profit_symbol = "🟢" if pnl["total_profit"] >= 0 else "🔴"
    roi_text = f"{(pnl['total_profit'] / 15000 * 100):+.1f}%" if pnl["total_profit"] != 0 else "0.0%"

    lines = [
        f"💰 <b>MEET PANCHAL'S PERSONAL IPO P&L</b>",
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"• <b>Lifetime Net Profit:</b> {profit_symbol} <b>₹{pnl['total_profit']:,.2f}</b>",
        f"• <b>Allotted & Sold:</b> {pnl['total_trades']} IPOs",
        f"• <b>Win Rate:</b> <b>{pnl['win_rate']:.1f}%</b> ({pnl['total_wins']}/{pnl['total_trades']})",
        f"• <b>Lot Capital Multiplier:</b> {roi_text} (Base: ₹15,000/lot)",
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    ]

    if pnl["monthly_map"]:
        lines.append("📅 <b>Monthly Realized Returns:</b>")
        for month, val in sorted(pnl["monthly_map"].items(), reverse=True)[:6]:
            status_icon = "🟢" if val >= 0 else "🔴"
            if val >= 0:
                lines.append(f"   • {month}: {status_icon} <b>+₹{val:,.2f}</b>")
            else:
                lines.append(f"   • {month}: {status_icon} <b>-₹{abs(val):,.2f}</b>")
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    if pnl["recent_trades"]:
        lines.append("📜 <b>Recent Listing Wins:</b>")
        for trade in pnl["recent_trades"][:5]:
            p_val = trade["profit_amount"]
            p_badge = f"+₹{p_val:,.0f}" if p_val >= 0 else f"-₹{abs(p_val):,.0f}"
            lines.append(f"   • <b>{trade['ipo_name']}</b> ({trade['date_str']}): 🟢 <b>{p_badge}</b>")
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    else:
        lines.append("ℹ️ <i>No trades recorded yet. You can log past listing gains anytime!</i>\n")

    lines.append(
        f"💡 <b>To Log New Listing Profit:</b>\n"
        f"<code>/pnl add &lt;IPO Name&gt; &lt;Profit Amount&gt;</code>\n"
        f"<i>Example: <code>/pnl add Bajaj Housing 18190</code></i>"
    )

    await msg_target.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)

async def cmd_scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manually triggers an on-demand market scan against the Profit-Only Filter."""
    await cmd_force_scan(update, context)

async def cmd_testalert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends a live demonstration of the exact Godfather push alerts."""
    msg_target = update.message if update.message else update.callback_query.message
    chat_id = update.effective_chat.id
    config.add_subscriber(chat_id)

    ipos = scraper.get_all_ipos()
    high_conviction = next((i for i in ipos if i.gmp_percent >= 25 and config.BUDGET_MIN <= i.total_cost <= config.BUDGET_MAX + 1000), ipos[0])
    
    await msg_target.reply_text("🚨 <b>Dispatching Godfather Direct Notification Simulation...</b>", parse_mode=ParseMode.HTML)

    # 1. Direct High-Profit Actionable Notification
    alert1 = engine.generate_high_profit_alert(high_conviction)
    await msg_target.reply_text(alert1, parse_mode=ParseMode.HTML)

    # 2. Mandate Panic Watchdog
    alert2 = engine.generate_mandate_panic_alert(high_conviction.name)
    await msg_target.reply_text(alert2, parse_mode=ParseMode.HTML)

    # 3. Shareholder Quota Advantage
    quota_ipo = next((i for i in ipos if i.shareholder_quota), high_conviction)
    alert3 = engine.generate_new_ipo_alert(quota_ipo)
    await msg_target.reply_text(alert3, parse_mode=ParseMode.HTML)

async def cmd_secretary_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manually triggers the autonomous Personal Financial Secretary briefing for Meet."""
    msg_target = update.message if update.message else update.callback_query.message
    chat_id = update.effective_chat.id
    config.add_subscriber(chat_id)

    await msg_target.reply_text("🎩 <i>MeetBot Personal Financial Secretary is preparing your executive briefing...</i>", parse_mode=ParseMode.HTML)
    ipos = scraper.get_all_ipos(force_refresh=True)
    briefing = engine.generate_secretary_briefing(ipos, session_type="ondemand")
    await msg_target.reply_text(briefing, parse_mode=ParseMode.HTML)

async def cmd_clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Instantly clears unpinned chat history within 1-2 seconds, preserving pinned messages."""
    chat_id = update.effective_chat.id
    trigger_id = update.message.message_id if update.message else (update.callback_query.message.message_id if update.callback_query else None)

    # Fast batch delete
    deleted = await chat_cleaner.clear_chat_instantly(context.bot, chat_id=chat_id, trigger_message_id=trigger_id)
    logger.info(f"Instant clear executed for chat {chat_id} (cleared {deleted} messages).")

    fresh_msg = (
        f"🧹 <b>CHAT CLEARED</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Chat cleared in 1-2 seconds. Pinned messages remain safe.\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )
    await context.bot.send_message(
        chat_id=chat_id,
        text=fresh_msg,
        parse_mode=ParseMode.HTML,
        reply_markup=get_main_keyboard()
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles inline keyboard navigation."""
    query = update.callback_query
    await query.answer()

    data = query.data
    if data == "cmd_force_scan":
        await cmd_force_scan(update, context)
    elif data == "cmd_ipos":
        await cmd_ipos(update, context)
    elif data == "cmd_gmp":
        await cmd_gmp(update, context)
    elif data == "cmd_radar":
        await cmd_radar(update, context)
    elif data == "cmd_pnl":
        await cmd_pnl(update, context)
    elif data == "cmd_scan":
        await cmd_scan(update, context)
    elif data == "cmd_secretary":
        await cmd_secretary_test(update, context)
    elif data == "cmd_clear":
        await cmd_clear(update, context)
    elif data == "cmd_rules":
        await cmd_rules(update, context)
    elif data == "cmd_testalert":
        await cmd_testalert(update, context)

# =======================================================
# SCHEDULED AUTOMATION RUNNERS & PROACTIVE WATCHER
# =======================================================

async def broadcast_message(app: Application, message: str, reply_markup: InlineKeyboardMarkup = None):
    """Broadcasts a notification message to all registered subscribers."""
    subscribers = config.get_subscribers()
    if not subscribers:
        logger.warning("No registered subscribers to broadcast to.")
        return
    for chat_id in subscribers:
        try:
            await app.bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup
            )
            logger.info(f"Broadcast sent successfully to {chat_id}")
        except Exception as e:
            logger.error(f"Failed to send broadcast to {chat_id}: {e}")

async def scheduled_morning_scan_job(app: Application):
    """
    Runs daily at 9:30 AM IST:
    Autonomous Personal Financial Secretary morning market briefing.
    Analyzes market, checks GMP, filters traps, and pushes direct advisory message to Meet.
    """
    logger.info("Executing 9:30 AM IST Morning Secretary Briefing...")
    try:
        ipos = scraper.get_all_ipos(force_refresh=True)
        if not ipos:
            logger.warning("[Morning Briefing] No IPOs detected from scraper feed.")
            return

        briefing = engine.generate_secretary_briefing(ipos, session_type="morning")
        await broadcast_message(app, briefing)
        logger.info("Morning Secretary Briefing successfully pushed to Meet Panchal.")
    except Exception as e:
        logger.error(f"[Morning Briefing Error] Failure during 9:30 AM briefing: {e}", exc_info=True)

async def scheduled_day3_verdict_job(app: Application):
    """
    Runs daily at 1:15 PM IST on Day 3 (Closing Day):
    Autonomous Personal Financial Secretary Day 3 execution briefing.
    Evaluates institutional QIB backing, warns on traps, and issues final call with cut-off price.
    """
    logger.info("Executing 1:15 PM IST Day 3 Closing Briefing...")
    try:
        ipos = scraper.get_all_ipos(force_refresh=True)
        if not ipos:
            logger.warning("[Day 3 Briefing] No IPOs detected from scraper feed.")
            return

        briefing = engine.generate_secretary_briefing(ipos, session_type="day3")
        await broadcast_message(app, briefing)
        logger.info("Day 3 Closing Call Secretary Briefing successfully pushed to Meet Panchal.")
    except Exception as e:
        logger.error(f"[Day 3 Briefing Error] Failure during 1:15 PM briefing: {e}", exc_info=True)

async def scheduled_mandate_panic_job(app: Application):
    """Runs at 3:45 PM IST on Day 3: Mandate Panic Watchdog before 4:30 PM deadline."""
    logger.info("Executing 3:45 PM IST Mandate Panic Watchdog...")
    try:
        ipos = scraper.get_all_ipos()
        active_day3 = [i for i in ipos if (i.current_day == 3 or i.status.lower() == "active") and i.gmp_percent >= config.MIN_GMP_PERCENT]
        if active_day3:
            ipo_name = active_day3[0].name
            msg = engine.generate_proactive_mandate_alert(ipo_name)
            await broadcast_message(app, msg)
        else:
            logger.info("Mandate watchdog skipped: No active high-conviction IPO requiring UPI approval today.")
    except Exception as e:
        logger.error(f"[Mandate Panic Error] {e}", exc_info=True)

async def proactive_market_watcher_loop(app: Application):
    """
    Continuous 24/7 Autonomous Market Watcher.
    Monitors live market data proactively.
    Between 9:15 AM and 4:30 PM IST (Monday - Friday): scans every 2 minutes.
    Outside market hours or weekends: scans every 15 minutes.
    Automatically pushes live alerts directly to Meet's Telegram without waiting for any user action.
    """
    tz = pytz.timezone(config.TIMEZONE)
    logger.info("👑 Godfather 100% Proactive Live Market Watcher loop running 24/7.")

    while True:
        try:
            now = datetime.datetime.now(tz)
            is_weekday = now.weekday() < 5  # Mon-Fri
            current_minute_val = now.hour * 60 + now.minute
            market_start_minute = 9 * 60 + 15   # 9:15 AM
            market_end_minute = 16 * 60 + 30    # 4:30 PM

            is_market_hours = is_weekday and (market_start_minute <= current_minute_val <= market_end_minute)

            logger.info(f"Proactive live market audit executing (Market Hours Active: {is_market_hours})...")
            stats = await execute_live_market_scan(app)
            if stats.get("dispatched", 0) > 0:
                logger.info(f"Proactive scan successfully dispatched {stats['dispatched']} live alerts to Meet!")

            sleep_seconds = 120 if is_market_hours else 900
        except Exception as e:
            logger.error(f"Error in proactive_market_watcher_loop: {e}", exc_info=True)
            sleep_seconds = 60

        await asyncio.sleep(sleep_seconds)

async def scheduler_loop(app: Application):
    """
    Background asynchronous scheduler loop operating continuously in IST (Asia/Kolkata).
    - 09:30 AM IST: Morning Market & GMP Scan (Profit-Only Filter)
    - 01:15 PM IST: Day 3 Closing Day Institutional Audit (QIB & Retail)
    - 03:45 PM IST: UPI Mandate Panic Watchdog
    """
    tz = pytz.timezone(config.TIMEZONE)
    logger.info(f"Godfather background scheduler initialized for timezone {config.TIMEZONE}")

    # Track triggers to avoid multiple firings within the same minute
    triggered_today = set()

    while True:
        try:
            now = datetime.datetime.now(tz)
            date_str = now.strftime("%Y-%m-%d")
            time_str = now.strftime("%H:%M")

            # 1. 09:30 AM IST: Morning Market & GMP Scan
            key_930am = f"{date_str}_09:30"
            if time_str == "09:30" and key_930am not in triggered_today:
                triggered_today.add(key_930am)
                await scheduled_morning_scan_job(app)

            # 2. 01:15 PM IST: Day 3 Closing Day Institutional Audit
            key_115pm = f"{date_str}_13:15"
            if time_str == "13:15" and key_115pm not in triggered_today:
                triggered_today.add(key_115pm)
                await scheduled_day3_verdict_job(app)

            # 3. 03:45 PM IST: Mandate Panic Watchdog
            key_345pm = f"{date_str}_15:45"
            if time_str == "15:45" and key_345pm not in triggered_today:
                triggered_today.add(key_345pm)
                await scheduled_mandate_panic_job(app)

            # Clean up old keys from yesterday
            if len(triggered_today) > 30:
                triggered_today = {k for k in triggered_today if date_str in k}

        except Exception as e:
            logger.error(f"Error in scheduler loop: {e}", exc_info=True)

        # Sleep 30 seconds between checks
        await asyncio.sleep(30)

async def auto_delete_loop(app: Application):
    """Periodically deletes messages older than 24 hours while keeping pinned messages safe."""
    logger.info(
        f"Auto-delete loop active (Lifetime: {config.AUTO_DELETE_HOURS} hours, Interval: {config.CLEANUP_INTERVAL_SECONDS}s)"
    )
    while True:
        try:
            deleted_count = await chat_cleaner.cleanup_expired_messages(app.bot)
            if deleted_count > 0:
                logger.info(f"Auto-delete: cleared {deleted_count} expired messages.")
        except Exception as e:
            logger.error(f"Error in auto_delete_loop: {e}")
        await asyncio.sleep(config.CLEANUP_INTERVAL_SECONDS)

async def post_init(app: Application):
    """Starts background scheduler coroutines and syncs Telegram profile metadata."""
    chat_cleaner.init_db()
    asyncio.create_task(scheduler_loop(app))
    asyncio.create_task(proactive_market_watcher_loop(app))
    asyncio.create_task(auto_delete_loop(app))
    logger.info("MeetBot background scheduler, proactive market watcher, & auto-delete cleaner successfully launched via post_init.")
    try:
        await app.bot.set_my_name(name="MeetBot | IPO Intelligence")
        await app.bot.set_my_short_description(
            short_description="Meet Panchal's AI IPO Intelligence & Allotment Agent. Single-lot mathematical discipline."
        )
        await app.bot.set_my_description(
            description=(
                "MeetBot is Meet Panchal's personal IPO Intelligence Agent.\n\n"
                "• Strict budget: Rs. 14,000 - 16,000 (1 Retail Lot)\n"
                "• Hard filters: GMP >= 25% & Day 3 QIB >= 25x\n"
                "• 100% Proactive Live Market Watcher (24/7 autonomous alerts)\n"
                "• Retail Trap Defense & Shareholder Quota Radar\n"
                "• Auto-disappearing chat after 24 hours (pinned messages stay)"
            )
        )
        # Auto-sync profile photo if present
        avatar_path = Path(__file__).parent / "assets" / "meetbot_avatar.jpg"
        if avatar_path.exists():
            try:
                from telegram import InputProfilePhotoStatic
                with open(avatar_path, "rb") as pf:
                    await app.bot.set_my_profile_photo(photo=InputProfilePhotoStatic(photo=pf))
                logger.info("Telegram profile avatar synced successfully.")
            except Exception as pe:
                logger.debug(f"Profile photo sync note: {pe}")

        logger.info("Telegram profile metadata synced successfully.")
    except Exception as e:
        logger.warning(f"Could not update bot profile metadata: {e}")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error and send a friendly message if update is a Message."""
    logger.error("Exception while handling an update:", exc_info=context.error)

def create_bot_app() -> Application:
    """Builds and configures the Telegram Application instance."""
    app = ApplicationBuilder().bot(TrackedBot(token=config.BOT_TOKEN)).post_init(post_init).build()

    app.add_error_handler(error_handler)
    # Track all incoming messages and pin events before command handlers
    app.add_handler(MessageHandler(filters.ALL, incoming_message_tracker, block=False), group=-1)

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("force_scan", cmd_force_scan))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("secretary_test", cmd_secretary_test))
    app.add_handler(CommandHandler("clear", cmd_clear))
    app.add_handler(CommandHandler("scan", cmd_scan))
    app.add_handler(CommandHandler("ipos", cmd_ipos))
    app.add_handler(CommandHandler("live", cmd_ipos))
    app.add_handler(CommandHandler("gmp", cmd_gmp))
    app.add_handler(CommandHandler("verdict", cmd_verdict))
    app.add_handler(CommandHandler("check", cmd_verdict))
    app.add_handler(CommandHandler("radar", cmd_radar))
    app.add_handler(CommandHandler("pnl", cmd_pnl))
    app.add_handler(CommandHandler("rules", cmd_rules))
    app.add_handler(CommandHandler("testalert", cmd_testalert))
    app.add_handler(CallbackQueryHandler(button_callback))

    return app

import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"status": "ok", "bot": "MeetBot IPO Intelligence Agent"}')

    def log_message(self, format, *args):
        pass

def start_health_server():
    """Starts a lightweight HTTP server on $PORT if specified (required for Render Free Web Services)."""
    port_env = os.environ.get("PORT")
    if port_env:
        try:
            port = int(port_env)
            server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            logger.info(f"Render health-check HTTP server active on port {port}.")
        except Exception as e:
            logger.warning(f"Health-check server note: {e}")

def main():
    """Direct entrypoint for background workers and cloud services."""
    if not config.BOT_TOKEN or "your_bot_token" in config.BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN is missing or invalid! Set it in environment variables.")
        sys.exit(1)

    start_health_server()
    logger.info("Initializing MeetBot Telegram Application...")
    app = create_bot_app()

    logger.info("MeetBot background worker online and polling. 24/7 active.")
    try:
        app.run_polling(drop_pending_updates=False)
    except (KeyboardInterrupt, SystemExit):
        logger.info("MeetBot shut down gracefully.")

if __name__ == "__main__":
    main()


