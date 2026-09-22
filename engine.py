import logging
from typing import Dict, Any, Tuple
from scraper import IPODetails
import config

logger = logging.getLogger("GodfatherEngine")

class DecisionVerdict:
    APPLY_HIGH_CONVICTION = "🟢 APPLY - HIGH CHANCE"
    AVOID_RETAIL_TRAP = "🔴 AVOID - RETAIL TRAP"
    AVOID_HIGH_RISK = "🔴 AVOID - HIGH RISK"
    WATCHLIST = "🟡 WATCHLIST - AWAITING QIB SURGE"

def evaluate_ipo(ipo: IPODetails) -> Tuple[str, str, Dict[str, Any]]:
    """
    Executes The Godfather Decision Matrix against mathematical criteria.
    Returns:
      verdict_badge: formatted verdict string
      verdict_summary: explanation of the decision
      analysis_data: breakdown of checks
    """
    gmp_pct = ipo.gmp_percent
    qib = ipo.qib_sub
    retail = ipo.retail_sub
    cost = ipo.total_cost

    checks = {
        "budget_pass": config.BUDGET_MIN <= cost <= (config.BUDGET_MAX + 1000), # flexible window ~14k - 17k
        "gmp_strong": gmp_pct >= config.MIN_GMP_PERCENT,
        "gmp_avoid": gmp_pct < config.AVOID_GMP_PERCENT,
        "retail_trap": (retail >= config.RETAIL_TRAP_RETAIL and qib < config.RETAIL_TRAP_QIB),
        "qib_strong": qib >= config.MIN_QIB_SUBSCRIPTION,
    }

    # 1. Check for Immediate Red Light: Retail Trap
    if checks["retail_trap"]:
        verdict = DecisionVerdict.AVOID_RETAIL_TRAP
        reason = (
            f"RETAIL TRAP DETECTED! Retail is oversubscribed at {retail}x while smart institutional "
            f"money (QIB) is completely absent at {qib}x. Extreme dump risk on listing."
        )
        return verdict, reason, checks

    # 2. Check for Immediate Red Light: Low / Negative GMP
    if checks["gmp_avoid"]:
        verdict = DecisionVerdict.AVOID_HIGH_RISK
        reason = (
            f"CAPITAL AT RISK! GMP is only {gmp_pct:.1f}% (Threshold: >= {config.MIN_GMP_PERCENT}%). "
            f"Margin of safety is non-existent. Strict Avoid."
        )
        return verdict, reason, checks

    # 3. Check for Green Light: High Conviction
    # (GMP >= 25% AND QIB >= 25x AND within budget)
    if checks["gmp_strong"] and checks["qib_strong"]:
        verdict = DecisionVerdict.APPLY_HIGH_CONVICTION
        reason = (
            f"HIGH CONVICTION! Monster QIB institutional backing ({qib}x) combined with strong GMP "
            f"({gmp_pct:.1f}%). Listing gains mathematically favored. Capital fully protected."
        )
        return verdict, reason, checks

    # 4. Watchlist / Pending QIB on Day 1 or Day 2
    if checks["gmp_strong"] and qib < config.MIN_QIB_SUBSCRIPTION:
        verdict = DecisionVerdict.WATCHLIST
        reason = (
            f"STRONG GMP ({gmp_pct:.1f}%), but waiting for institutional QIB rush on Day 3 by 1:30 PM. "
            f"Current QIB: {qib}x. Do NOT apply early."
        )
        return verdict, reason, checks

    # Fallback to Avoid if sub-par
    verdict = DecisionVerdict.AVOID_HIGH_RISK
    reason = f"Does not meet minimum Godfather risk/reward criteria (GMP: {gmp_pct:.1f}%, QIB: {qib}x)."
    return verdict, reason, checks


def is_profitable_for_meet(ipo: IPODetails, is_day3: bool = False) -> Tuple[bool, str]:
    """
    Evaluates whether an IPO strictly meets Meet's profit criteria:
    1. Fits within ₹14,000 - ₹16,000 budget for 1 Retail Lot (buffer up to ₹17,000).
    2. Expected Profit (GMP) is >= 25% - 30% listing gain.
    3. Day 3: Institutional backing (QIB) is healthy; no retail trap.
    """
    # 1. Budget check: Strictly 1 Retail Lot
    if not (config.BUDGET_MIN <= ipo.total_cost <= (config.BUDGET_MAX + 1000)):
        return False, f"Lot cost ₹{ipo.total_cost:,.0f} outside budget range (₹{config.BUDGET_MIN:,} - ₹{config.BUDGET_MAX:,})"

    # 2. GMP profit check: >= 25%
    if ipo.gmp_percent < config.MIN_GMP_PERCENT:
        return False, f"GMP {ipo.gmp_percent:.1f}% below profit threshold ({config.MIN_GMP_PERCENT}%)"

    # 3. Retail trap / QIB institutional health check on Day 3
    if is_day3 or ipo.current_day == 3:
        if ipo.retail_sub >= config.RETAIL_TRAP_RETAIL and ipo.qib_sub < config.RETAIL_TRAP_QIB:
            return False, f"Retail trap risk: Retail {ipo.retail_sub:.1f}x with Cold QIB {ipo.qib_sub:.1f}x"
        if ipo.qib_sub > 0 and ipo.qib_sub < config.MIN_QIB_SUBSCRIPTION:
            return False, f"Day 3 QIB {ipo.qib_sub:.1f}x below minimum threshold ({config.MIN_QIB_SUBSCRIPTION}x)"

    return True, "Passed all profit filters"


def generate_high_profit_alert(ipo: IPODetails) -> str:
    """
    Generates the direct actionable push notification for Meet Panchal matching the exact specification:
    ---------------------------------------------------
    👑 MEET PANCHAL ALERT | HIGH-PROFIT IPO DETECTED!
    ---------------------------------------------------
    Hey Meet Panchal, a profitable IPO is live and recommended for you:

    📌 IPO Name: [Company Name] ([Sector])
    💰 Investment Required: ₹[Lot Cost] (1 Retail Lot)
    📈 Expected Profit: +₹[Estimated Profit] ([% Gain])

    💡 WHY MEET SHOULD APPLY:
    • Strong listing gains expected based on [GMP]% GMP.
    • High institutional demand (QIB [Xx]), keeping your ₹15k safe.
    • Perfect match for your risk-reward profile.

    🎯 WHAT YOU NEED TO DO RIGHT NOW:
    1. Open your Groww / Angel One app.
    2. Apply for 1 Lot and check "Cut-off Price" (₹[Max Price]).
    3. Submit before 3:30 PM IST.
    4. Approve your UPI mandate before 4:30 PM IST sharp!
    ---------------------------------------------------
    """
    qib_str = f"{ipo.qib_sub:.1f}x" if ipo.qib_sub > 0 else "Strong"
    sector_str = ipo.sector if ipo.sector else "Mainline"
    gmp_display = f"{ipo.gmp_percent:.0f}"

    msg = (
        f"👑 <b>MEET PANCHAL ALERT | HIGH-PROFIT IPO DETECTED!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Hey Meet Panchal, a profitable IPO is live and recommended for you:\n\n"
        f"📌 <b>IPO Name:</b> {ipo.name} ({sector_str})\n"
        f"💰 <b>Investment Required:</b> ₹{ipo.total_cost:,.0f} (1 Retail Lot)\n"
        f"📈 <b>Expected Profit:</b> +₹{ipo.est_profit:,.0f} ({ipo.gmp_percent:+.1f}%)\n\n"
        f"💡 <b>WHY MEET SHOULD APPLY:</b>\n"
        f"• Strong listing gains expected based on {gmp_display}% GMP.\n"
        f"• High institutional demand (QIB {qib_str}), keeping your ₹15k safe.\n"
        f"• Perfect match for your risk-reward profile.\n\n"
        f"🎯 <b>WHAT YOU NEED TO DO RIGHT NOW:</b>\n"
        f"1. Open your Groww / Angel One app.\n"
        f"2. Apply for 1 Lot and check \"Cut-off Price\" (₹{int(ipo.upper_price):,}).\n"
        f"3. Submit before 3:30 PM IST.\n"
        f"4. Approve your UPI mandate before 4:30 PM IST sharp!\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )
    return msg


def generate_blueprint_alert(ipo: IPODetails) -> str:
    """
    Generates standard Telegram notification matching the exact requested blueprint:
    ---------------------------------------------------
    👑 GODFATHER IPO ALERT | MEET PANCHAL
    ---------------------------------------------------
    📌 Company: [Company Name] ([Sector])
    💵 Lot Cost: ₹[Total Cost] (1 Lot strictly)
    📈 Current GMP: ₹[GMP] (Est. Profit: +₹[Profit per lot] | [% Gain])

    📊 Subscription Status (Day 3):
    • QIB: [Xx] | Retail: [Xx] | Overall: [Xx]

    ⚖️ VERDICT: [🟢 APPLY - HIGH CHANCE / 🔴 AVOID - TRAP]

    📝 MEET'S ACTION CHECKLIST:
    1. Select Category: Retail (1 Lot)
    2. Check Box: "Cut-off Price" (₹[Max Price])
    3. Bid Window: Submit today before 3:30 PM IST
    4. Approve UPI Mandate before 4:30 PM IST sharp!
    ---------------------------------------------------
    """
    verdict, _, _ = evaluate_ipo(ipo)
    
    # Format subscription strings
    qib_str = f"{ipo.qib_sub:.2f}x" if ipo.qib_sub > 0 else "--x"
    retail_str = f"{ipo.retail_sub:.2f}x" if ipo.retail_sub > 0 else "--x"
    overall_str = f"{ipo.total_sub:.2f}x" if ipo.total_sub > 0 else "--x"
    
    # Check if budget fits
    budget_fit = "Within ₹14k-₹16k budget" if (config.BUDGET_MIN <= ipo.total_cost <= config.BUDGET_MAX + 1000) else "Exceeds standard budget"

    checklist = (
        f"1. Select Category: Retail (1 Lot strictly - SEBI lottery)\n"
        f"2. Check Box: 'Cut-off Price' (₹{int(ipo.upper_price)})\n"
        f"3. Bid Window: Submit today between 1:00 PM and 3:30 PM IST\n"
        f"4. Approve UPI Mandate before 4:30 PM IST sharp!"
    )

    if verdict != DecisionVerdict.APPLY_HIGH_CONVICTION:
        checklist = (
            f"1. 🚫 DO NOT SUBMIT BID: Capital preservation rule active.\n"
            f"2. Reason: Under-performing institutional demand or low GMP.\n"
            f"3. Keep capital reserved for high-conviction opportunities."
        )

    quota_banner = ""
    if ipo.shareholder_quota and ipo.parent_company:
        quota_banner = f"\n🏢 Shareholder Quota: Available via {ipo.parent_company}!\n"

    msg = (
        f"👑 <b>MEETBOT IPO ALERT | {config.TARGET_USER.upper()}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 <b>Company:</b> {ipo.name} ({ipo.sector})\n"
        f"💵 <b>Lot Cost:</b> ₹{ipo.total_cost:,.0f} (1 Lot strictly | {budget_fit})\n"
        f"📈 <b>Current GMP:</b> ₹{ipo.gmp:,.0f} (Est. Profit: +₹{ipo.est_profit:,.0f} | {ipo.gmp_percent:+.1f}%)\n"
        f"{quota_banner}"
        f"\n📊 <b>Subscription Status (Day {ipo.current_day}):</b>\n"
        f"• QIB: <b>{qib_str}</b> | Retail: <b>{retail_str}</b> | Overall: <b>{overall_str}</b>\n\n"
        f"⚖️ <b>VERDICT:</b> {verdict}\n\n"
        f"📝 <b>MEET'S ACTION CHECKLIST:</b>\n"
        f"{checklist}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )
    return msg


def generate_new_ipo_alert(ipo: IPODetails) -> str:
    """Alert triggered when a new IPO is announced."""
    parent_msg = ""
    if ipo.shareholder_quota and ipo.parent_company:
        parent_msg = (
            f"\n🎯 <b>DOUBLE QUOTA ADVANTAGE DETECTED!</b>\n"
            f"Parent company is publicly listed: <b>{ipo.parent_company}</b>\n"
            f"⚡ <b>URGENT ACTION FOR MEET:</b> Buy 1 share of <b>{ipo.parent_company}</b> before the "
            f"record date to unlock the exclusive Shareholder Quota + Retail Quota dual-application edge!"
        )
    else:
        parent_msg = "\n🏢 Shareholder Quota: None (Standard Retail Quota only)"

    msg = (
        f"🚨 <b>NEW IPO ANNOUNCEMENT | {config.TARGET_USER.upper()}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 <b>Issue:</b> {ipo.name}\n"
        f"🏷️ <b>Price Band:</b> {ipo.price_band}\n"
        f"📦 <b>Lot Size:</b> {ipo.lot_size} shares (Total: ₹{ipo.total_cost:,.0f})\n"
        f"📅 <b>Bidding Dates:</b> {ipo.open_date} to {ipo.close_date}\n"
        f"📈 <b>Opening GMP:</b> ₹{ipo.gmp:,.0f} ({ipo.gmp_percent:.1f}%)\n"
        f"{parent_msg}\n\n"
        f"🛡️ <i>MeetBot is tracking this IPO. Final verdict will be issued at 1:15 PM on Day 3.</i>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )
    return msg


def generate_day3_verdict_alert(ipo: IPODetails) -> str:
    """Alert triggered at 1:15 PM IST on Day 3 with final numbers."""
    return generate_blueprint_alert(ipo)


def generate_mandate_panic_alert(ipo_name: str = "Active IPO") -> str:
    """Alert triggered at 3:45 PM IST on Day 3 for mandate approval."""
    msg = (
        f"🚨🚨 <b>URGENT MANDATE PANIC WATCHDOG | {config.TARGET_USER.upper()}</b> 🚨🚨\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⏰ <b>CURRENT TIME: 3:45 PM IST</b>\n"
        f"⚠️ <b>MANDATE DEADLINE APPROACHING: 4:30 PM IST</b>\n\n"
        f"Meet, execute this immediately:\n"
        f"1. Open your UPI App (Google Pay / PhonePe / Paytm / BHIM) or Bank ASBA portal.\n"
        f"2. Go to <b>Pending Mandates / Autopay Requests</b>.\n"
        f"3. <b>APPROVE & ENTER UPI PIN</b> to block ~₹15,000.\n\n"
        f"⚠️ <i>WARNING: If the mandate is not authorized before 4:30 PM IST, the exchange will "
        f"instantly CANCEL your application and your allotment chance is lost!</i>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )
    return msg


def generate_listing_strategy_alert(ipo: IPODetails, current_price: float) -> str:
    """Alert triggered at 9:15 AM on Listing Day."""
    gain = current_price - ipo.upper_price
    gain_pct = (gain / ipo.upper_price) * 100 if ipo.upper_price > 0 else 0.0
    profit = gain * ipo.lot_size

    if gain_pct >= 25.0:
        advice = (
            f"🎯 <b>MEETBOT'S EXECUTION: 100% PROFIT BOOKING</b>\n"
            f"• Mission Accomplished! The listing popped at <b>+{gain_pct:.1f}%</b>.\n"
            f"• Action: Sell all {ipo.lot_size} shares in pre-open / market open.\n"
            f"• Lock in your net profit of <b>+₹{profit:,.0f}</b> and protect capital."
        )
    else:
        advice = (
            f"⚠️ <b>MEETBOT'S EXECUTION: DEFENSIVE STOP-LOSS</b>\n"
            f"• Subdued opening at <b>{gain_pct:+.1f}%</b>.\n"
            f"• Action: Place a strict stop-loss at ₹{int(ipo.upper_price * 0.97)} (3% below issue price) to prevent capital erosion."
        )

    msg = (
        f"🔔 <b>LISTING DAY STRATEGY | {config.TARGET_USER.upper()}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 <b>Stock:</b> {ipo.name}\n"
        f"💵 <b>Issue Price:</b> ₹{ipo.upper_price:,.0f}\n"
        f"🚀 <b>Listing / Current Price:</b> ₹{current_price:,.0f} ({gain_pct:+.1f}%)\n"
        f"💰 <b>Net Realized / Open P&L:</b> ₹{profit:+,.0f} per lot\n\n"
        f"{advice}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )
    return msg


def generate_secretary_briefing(ipos: List[IPODetails], session_type: str = "morning") -> str:
    """
    Generates a proactive, personalized financial secretary briefing for Meet Panchal.
    Classifies IPOs into:
    - TOP PICK: High conviction, GMP >= 25%, fits ~₹15,000 budget.
    - AVOID: GMP < 20% or high retail with cold QIB (Retail trap).
    - PARENT COMPANY BENEFIT: Listed parent shareholder quota advantage.
    - ACTION DIRECTIVE: Clear, actionable execution instruction.
    """
    profitable = []
    risky = []
    shareholder_ipos = []

    for ipo in ipos:
        # Check shareholder advantage
        if ipo.shareholder_quota and ipo.parent_company:
            shareholder_ipos.append(ipo)

        # Check profitable & safe
        is_prof, _ = is_profitable_for_meet(ipo, is_day3=(session_type == "day3"))
        if is_prof:
            profitable.append(ipo)
        else:
            # Check if avoid/risky
            if ipo.gmp_percent < 20.0 or (ipo.retail_sub >= 10.0 and ipo.qib_sub < 5.0):
                risky.append(ipo)

    profitable.sort(key=lambda x: (x.gmp_percent, x.est_profit), reverse=True)
    risky.sort(key=lambda x: x.gmp_percent)

    # Greeting based on session
    if session_type == "morning":
        header = (
            f"🎩 <b>MEETBOT PERSONAL FINANCIAL SECRETARY</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Good morning {config.TARGET_USER}! Here is your autonomous IPO market briefing:\n"
        )
    elif session_type == "day3":
        header = (
            f"🎩 <b>MEETBOT PERSONAL FINANCIAL SECRETARY | CLOSING CALL</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Good afternoon {config.TARGET_USER}! It's Closing Day (Day 3). Here is your institutional execution directive:\n"
        )
    else:
        header = (
            f"🎩 <b>MEETBOT PERSONAL FINANCIAL SECRETARY | LIVE BRIEFING</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Hello {config.TARGET_USER}! Here is your on-demand executive IPO briefing:\n"
        )

    sections = [header]

    # 1. Top Pick Section
    if profitable:
        top = profitable[0]
        qib_info = f"Institutional demand: QIB {top.qib_sub:.1f}x." if top.qib_sub > 0 else "Strong demand profile."
        top_sec = (
            f"🟢 <b>TOP PICK: {top.name} ({top.sector})</b>\n"
            f"• Estimated Profit: <b>+₹{top.est_profit:,.0f} per lot ({top.gmp_percent:+.1f}%)</b>\n"
            f"• Required Capital: ₹{top.total_cost:,.0f} (Safe for your ₹15k capital)\n"
            f"• Why Apply: High listing gain margin ({top.gmp_percent:.0f}% GMP). {qib_info}\n"
        )
        if len(profitable) > 1:
            second = profitable[1]
            top_sec += f"• Secondary Contender: <b>{second.name}</b> (+₹{second.est_profit:,.0f} | GMP {second.gmp_percent:+.1f}%)\n"
        sections.append(top_sec)
    else:
        sections.append(
            f"🟢 <b>TOP PICK: NONE TODAY</b>\n"
            f"• Zero issues currently pass your strict capital preservation filters.\n"
            f"• Capital remains 100% safe in your bank account.\n"
        )

    # 2. Avoid Section
    if risky:
        avoid = risky[0]
        reason = f"GMP is too low ({avoid.gmp_percent:+.1f}%), high risk of listing discount." if avoid.gmp_percent < 20 else f"Retail trap risk ({avoid.retail_sub:.1f}x retail, cold QIB)."
        avoid_sec = (
            f"🔴 <b>AVOID / SKIP: {avoid.name}</b>\n"
            f"• Reason: {reason} Skip this issue completely to avoid loss.\n"
        )
        sections.append(avoid_sec)

    # 3. Shareholder Advantage Section
    if shareholder_ipos:
        sh = shareholder_ipos[0]
        sh_sec = (
            f"🏢 <b>PARENT COMPANY BENEFIT:</b>\n"
            f"• <b>{sh.name}</b>: Listed parent is <b>{sh.parent_company}</b>.\n"
            f"• Action: Buy <b>1 share</b> before record date to double your application quota!\n"
        )
        sections.append(sh_sec)

    # 4. Directive Section
    if profitable:
        top = profitable[0]
        if session_type == "day3":
            action_sec = (
                f"🎯 <b>WHAT YOU NEED TO DO RIGHT NOW (CLOSING WINDOW):</b>\n"
                f"1. Open your Groww / Angel One app.\n"
                f"2. Apply for 1 Lot of <b>{top.name}</b> and check 'Cut-off Price' (₹{int(top.upper_price):,}).\n"
                f"3. Submit before 3:30 PM IST.\n"
                f"4. Approve your UPI mandate before 4:30 PM IST sharp!"
            )
        else:
            action_sec = (
                f"👉 <b>ACTION FOR MEET:</b>\n"
                f"• You only need to apply for <b>{top.name}</b>.\n"
                f"• I will monitor institutional subscription live and remind you at 1:15 PM on closing day with the exact cut-off bid details.\n"
                f"• Mandate approval deadline: 4:30 PM IST."
            )
        sections.append(action_sec)
    else:
        sections.append(
            f"👉 <b>ACTION FOR MEET:</b>\n"
            f"• No action required today. Relax and keep your ₹15,000 capital safe for high-conviction opportunities."
        )

    sections.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    return "\n".join(sections)


# =======================================================
# 100% PROACTIVE LIVE MARKET TRIGGER GENERATORS
# =======================================================

def generate_proactive_green_light_alert(ipo: IPODetails, capital_priority_note: str = "") -> str:
    """
    Trigger A: High-Conviction Opportunity (🟢 GREEN LIGHT)
    When GMP >= 25% and Day 3 QIB >= 25x within budget (~₹15k).
    Includes Multi-PAN Allotment Maximizer for GMP > 40%.
    """
    multi_pan_note = ""
    if ipo.gmp_percent > 40.0:
        multi_pan_note = (
            f"\n\n👥 <b>Allotment chance maximizer:</b> "
            f"GMP is monster ({ipo.gmp_percent:+.1f}% &gt; 40%)! "
            f"Consider applying 1 lot each from 2 different family PAN accounts to mathematically double your allotment probability!"
        )

    priority_section = f"\n\n{capital_priority_note}" if capital_priority_note else ""

    return (
        f"👑 <b>GODFATHER ALERT: ACTION REQUIRED, MEET!</b>\n\n"
        f"Meet, you should directly apply for this IPO: <b>{ipo.name}</b>!\n\n"
        f"• <b>Expected Profit:</b> +₹{ipo.est_profit:,.0f} ({ipo.gmp_percent:+.1f}%)\n"
        f"• <b>Safety Check:</b> QIB quota is subscribed <b>{ipo.qib_sub:.1f}x</b>, institutional support is strong.\n"
        f"• <b>Action:</b> Open your Groww / Angel One app now, select Cut-off price (₹{int(ipo.upper_price):,}), bid 1 Lot strictly. Complete before 3:30 PM!\n"
        f"{multi_pan_note}"
        f"{priority_section}"
    )

def calculate_conviction_score(ipo: IPODetails) -> float:
    """Computes mathematical composite conviction score: (GMP% * 0.6) + (QIB * 0.4)."""
    return (ipo.gmp_percent * 0.6) + (ipo.qib_sub * 0.4)

def prioritize_capital_allocation(profitable_ipos: List[IPODetails]) -> Optional[str]:
    """
    Ranks overlapping profitable IPOs by mathematical conviction score.
    Strictly tells Meet: "Pick [IPO 1] first. Do not split capital into [IPO 2]."
    """
    if len(profitable_ipos) < 2:
        return None

    ranked = sorted(profitable_ipos, key=calculate_conviction_score, reverse=True)
    top_1 = ranked[0]
    top_2 = ranked[1]

    msg = (
        f"⚖️ <b>CAPITAL ALLOCATION DIRECTIVE FOR MEET:</b>\n"
        f"Multiple profitable IPOs are active! Based on institutional QIB demand:\n"
        f"👉 <b>Pick {top_1.name} first. Do not split capital into {top_2.name}.</b>\n"
        f"• <i>Priority #1 ({top_1.name}):</i> GMP {top_1.gmp_percent:+.1f}% | Day 3 QIB {top_1.qib_sub:.1f}x (Profit: +₹{top_1.est_profit:,.0f})\n"
        f"• <i>Standby #2 ({top_2.name}):</i> GMP {top_2.gmp_percent:+.1f}% | Day 3 QIB {top_2.qib_sub:.1f}x\n"
        f"• <i>Directive:</i> Concentrate Meet's ₹15,000 capital entirely on the #1 ranked issue. Zero dilution."
    )
    return msg

def generate_refund_unblock_alert(ipo_name: str) -> str:
    """
    Trigger E: Refund / Unblock Watchdog (24h post-allotment date).
    """
    return (
        f"💸 <b>REFUND / UNBLOCK WATCHDOG:</b>\n\n"
        f"Meet, the allotment process for <b>{ipo_name}</b> has completed!\n\n"
        f"Check your bank balance/UPI app to confirm your blocked ₹15,000 has been released for the next IPO."
    )

def generate_proactive_avoid_alert(ipo: IPODetails, reason_override: str = "") -> str:
    """
    Trigger B: Retail Trap Warning (🔴 RED LIGHT / AVOID)
    When Retail is > 10x but QIB is cold (< 5x) OR GMP falls below 20%.
    """
    if reason_override:
        risk_factor = reason_override
    elif ipo.retail_sub >= config.RETAIL_TRAP_RETAIL and ipo.qib_sub < config.RETAIL_TRAP_QIB:
        risk_factor = f"Retail trap detected (Retail subscribed {ipo.retail_sub:.1f}x but QIB is silent at {ipo.qib_sub:.1f}x)"
    elif ipo.gmp_percent < config.AVOID_GMP_PERCENT:
        risk_factor = f"GMP crashed to {ipo.gmp_percent:+.1f}%"
    else:
        risk_factor = f"Capital at risk (GMP: {ipo.gmp_percent:+.1f}%)"

    return (
        f"⚠️ <b>GODFATHER RISK WARNING: AVOID THIS IPO, MEET!</b>\n\n"
        f"Meet, do not invest any money into <b>{ipo.name}</b>.\n\n"
        f"• <b>Risk Factor:</b> {risk_factor}.\n"
        f"• <b>Decision:</b> <b>STRICT AVOID</b>. Protect your capital, zero entry."
    )

def generate_proactive_shareholder_alert(parent_company: str, upcoming_ipo: str) -> str:
    """
    Trigger C: Shareholder Quota Radar (🏢 ADVANCE HACK)
    When a parent company IPO is filed or detected on radar.
    """
    return (
        f"💡 <b>GODFATHER STRATEGY ALERT FOR MEET:</b>\n\n"
        f"Meet, buy 1 share of <b>{parent_company}</b> right now. "
        f"<b>{upcoming_ipo}</b> is coming soon, and with this strategy you can apply in both Retail + Shareholder quotas to double your allotment chances!"
    )

def generate_proactive_mandate_alert(ipo_name: str) -> str:
    """
    Trigger D: UPI Mandate Deadline (⏰ 3:45 PM IST on Day 3)
    """
    return (
        f"🚨 <b>MANDATE REMINDER:</b> Meet, please open your UPI app / bank and approve the mandate for "
        f"<b>{ipo_name}</b> before 4:30 PM IST, otherwise your application will be cancelled!"
    )

def evaluate_proactive_triggers(ipo: IPODetails) -> Tuple[Optional[str], Optional[str]]:
    """
    Evaluates live IPO metrics against the Godfather Proactive Triggers.
    Returns:
       (trigger_type, alert_message) or (None, None)
    """
    cost = ipo.total_cost
    gmp_pct = ipo.gmp_percent
    qib = ipo.qib_sub
    retail = ipo.retail_sub
    within_budget = config.BUDGET_MIN <= cost <= (config.BUDGET_MAX + 1000)

    # 1. Trigger A: High-Conviction Opportunity (🟢 GREEN LIGHT)
    # When GMP >= 25% and Day 3 QIB >= 25x within budget (~₹15k)
    if within_budget and gmp_pct >= config.MIN_GMP_PERCENT and qib >= config.MIN_QIB_SUBSCRIPTION:
        msg = generate_proactive_green_light_alert(ipo)
        return "GREEN_LIGHT", msg

    # 2. Trigger B: Retail Trap Warning (🔴 RED LIGHT / AVOID)
    # High retail with cold QIB
    if (retail >= config.RETAIL_TRAP_RETAIL and qib < config.RETAIL_TRAP_QIB):
        reason = f"Retail trap detected (Retail subscribed {retail:.1f}x but QIB is silent at {qib:.1f}x)"
        msg = generate_proactive_avoid_alert(ipo, reason_override=reason)
        return "RETAIL_TRAP", msg

    # GMP crash / low margin of safety
    if gmp_pct < config.AVOID_GMP_PERCENT and (ipo.status.lower() == "active" or ipo.current_day >= 1):
        reason = f"GMP crashed to {gmp_pct:+.1f}%"
        msg = generate_proactive_avoid_alert(ipo, reason_override=reason)
        return "AVOID_LOW_GMP", msg

    # 3. Trigger C: Shareholder Quota Radar
    if ipo.shareholder_quota and ipo.parent_company:
        msg = generate_proactive_shareholder_alert(ipo.parent_company, ipo.name)
        return "SHAREHOLDER_RADAR", msg

    return None, None


