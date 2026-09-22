import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import config
import engine
from scraper import IPODetails
import chat_cleaner

def run_tests():
    print("==================================================")
    print("🧪 TESTING PROACTIVE TRIGGERS & ANTI-SPAM MEMORY")
    print("==================================================")

    # 1. Initialize DB
    chat_cleaner.init_db()
    chat_cleaner.clear_alerts_memory()
    print("✅ Database initialized & alert memory cleared.")

    # 2. Test Trigger A: High Conviction Green Light
    green_ipo = IPODetails(
        name="High Conviction Test Corp",
        symbol="HCTEST",
        price_band="₹100 - ₹100",
        lower_price=100,
        upper_price=100,
        lot_size=150,
        total_cost=15000,
        gmp=40,
        gmp_percent=40.0,
        est_profit=6000,
        qib_sub=35.0,
        retail_sub=5.0,
        current_day=3,
        status="Active"
    )
    trig_a, msg_a = engine.evaluate_proactive_triggers(green_ipo)
    assert trig_a == "GREEN_LIGHT", f"Expected GREEN_LIGHT, got {trig_a}"
    assert "Meet, you should directly apply for this IPO" in msg_a, "Missing exact English wording for Trigger A"
    assert "Open your Groww / Angel One app now" in msg_a, "Missing Groww / Angel One action"
    print("✅ Trigger A (Green Light) passed:")
    print("   Snippet:", msg_a.splitlines()[2])

    # 3. Test Trigger B: Retail Trap & Avoid
    trap_ipo = IPODetails(
        name="Retail Trap Test Corp",
        symbol="TRAPTEST",
        price_band="₹100 - ₹100",
        upper_price=100,
        lot_size=150,
        total_cost=15000,
        gmp=25,
        gmp_percent=25.0,
        qib_sub=1.5,
        retail_sub=18.0,
        current_day=3,
        status="Active"
    )
    trig_b, msg_b = engine.evaluate_proactive_triggers(trap_ipo)
    assert trig_b == "RETAIL_TRAP", f"Expected RETAIL_TRAP, got {trig_b}"
    assert f"Meet, do not invest any money into <b>{trap_ipo.name}</b>" in msg_b, "Missing exact wording for Trigger B"
    assert "STRICT AVOID" in msg_b, "Missing STRICT AVOID"
    print("✅ Trigger B (Retail Trap Avoid) passed:")
    print("   Snippet:", msg_b.splitlines()[2])

    # 4. Test Trigger C: Shareholder Quota Radar
    sh_ipo = IPODetails(
        name="Tata Capital Housing",
        symbol="TATAHOUS",
        price_band="₹100 - ₹100",
        upper_price=100,
        lot_size=150,
        total_cost=15000,
        gmp=20,
        gmp_percent=20.0,
        parent_company="Tata Motors Limited",
        shareholder_quota=True,
        status="Upcoming"
    )
    trig_c, msg_c = engine.evaluate_proactive_triggers(sh_ipo)
    assert trig_c == "SHAREHOLDER_RADAR", f"Expected SHAREHOLDER_RADAR, got {trig_c}"
    assert "buy 1 share" in msg_c, "Missing 1-share buy wording"
    assert "Retail + Shareholder quotas" in msg_c, "Missing double quota wording"
    print("✅ Trigger C (Shareholder Radar) passed:")
    print("   Snippet:", msg_c.splitlines()[2])

    # 5. Test Trigger D: UPI Mandate Deadline
    mandate_msg = engine.generate_proactive_mandate_alert("Bajaj Housing Finance")
    assert "approve the mandate" in mandate_msg, "Missing exact mandate wording"
    assert "before 4:30 PM IST" in mandate_msg, "Missing 4:30 PM approval time"
    print("✅ Trigger D (Mandate Reminder) passed:")
    print("   Snippet:", mandate_msg.splitlines()[0])

    # 6. Test SQLite Anti-Spam Memory
    print("\n🔍 Testing SQLite Anti-Spam Memory Suppression:")
    # Run 1: should send
    s1 = chat_cleaner.should_dispatch_alert("Bajaj Housing", "GREEN_LIGHT", current_gmp=120.0, current_qib=200.0)
    assert s1 is True, "First alert check should be True"
    chat_cleaner.record_alert_dispatched("Bajaj Housing", "GREEN_LIGHT", current_gmp=120.0, current_qib=200.0, current_status="Active")
    print("   • Dispatched initial alert -> Recorded in SQLite.")

    # Run 2: immediately checked again (zero spam suppression)
    s2 = chat_cleaner.should_dispatch_alert("Bajaj Housing", "GREEN_LIGHT", current_gmp=120.0, current_qib=202.0)
    assert s2 is False, "Second alert check without significant surge must be suppressed (False)"
    print("   • Checked again at 202x QIB -> Correctly SUPPRESSED (Zero-Spam Protected!).")

    # Run 3: Massive surge (+25x QIB)
    s3 = chat_cleaner.should_dispatch_alert("Bajaj Housing", "GREEN_LIGHT", current_gmp=120.0, current_qib=225.0)
    assert s3 is True, "Massive QIB surge should allow re-alerting"
    print("   • Checked with massive surge (+25x QIB) -> Correctly RE-ALERTED.")

    # 7. Test Strict Mainline Filter (NO SME IPOs)
    print("\n🛡️ Testing Strict Mainline Filter (NO SME IPOs):")
    import scraper
    sme_ipo_1 = IPODetails(name="Awesome SME Ltd", total_cost=120000.0)
    sme_ipo_2 = IPODetails(name="Tech Innovators (BSE SME)", total_cost=15000.0)
    mainline_ipo = IPODetails(name="Tata Motors Finance", total_cost=14800.0, is_mainline=True)
    assert scraper.is_sme_ipo(sme_ipo_1) is True, "High lot cost (>₹25k) must be flagged as SME"
    assert scraper.is_sme_ipo(sme_ipo_2) is True, "Name with 'SME' must be flagged as SME"
    assert scraper.is_sme_ipo(mainline_ipo) is False, "Mainline lot (~₹14.8k) must NOT be flagged as SME"
    all_ipos = scraper.get_all_ipos()
    for item in all_ipos:
        assert not scraper.is_sme_ipo(item), f"Found SME issue in mainline feed: {item.name}"
    print("   • Strict Mainline Filter verified: Zero SME issues permitted.")

    # 8. Test One-Click Broker Deep-Links
    print("\n🔗 Testing One-Click Broker Deep-Links:")
    import bot
    kb = bot.get_broker_apply_keyboard()
    urls = [btn.url for row in kb.inline_keyboard for btn in row]
    assert "https://groww.in/ipo" in urls, "Missing Groww IPO deep-link"
    assert "https://www.angelone.in/ipo" in urls, "Missing Angel One IPO deep-link"
    print("   • Broker deep-links verified: Groww & Angel One buttons active.")

    # 9. Test Capital Allocation Prioritizer
    print("\n⚖️ Testing Capital Allocation Prioritizer:")
    ipo_top = IPODetails(name="Bajaj Housing Finance", gmp_percent=121.0, qib_sub=220.0, upper_price=70, total_cost=14980)
    ipo_sub = IPODetails(name="Secondary Contender Ltd", gmp_percent=30.0, qib_sub=28.0, upper_price=200, total_cost=15000)
    directive = engine.prioritize_capital_allocation([ipo_top, ipo_sub])
    assert "Pick Bajaj Housing Finance first. Do not split capital into Secondary Contender Ltd." in directive
    print("   • Capital allocation directive verified: Priority #1 strictly mandated.")

    # 10. Test Multi-PAN Allotment Maximizer
    print("\n👥 Testing Multi-PAN Allotment Maximizer:")
    msg_multipan = engine.generate_proactive_green_light_alert(ipo_top)
    assert "Allotment chance maximizer" in msg_multipan, "Missing Multi-PAN prompt for GMP > 40%"
    assert "2 different family PAN accounts" in msg_multipan
    print("   • Multi-PAN maximizer verified for monster conviction issues (GMP > 40%).")

    # 11. Test Refund / Unblock Watchdog
    print("\n💸 Testing Refund / Unblock Watchdog:")
    refund_alert = engine.generate_refund_unblock_alert("Bajaj Housing Finance")
    assert "allotment process" in refund_alert and "Bajaj Housing Finance" in refund_alert
    assert "blocked ₹15,000 has been released" in refund_alert
    print("   • Refund watchdog message verified.")

    # 12. Test Personal P&L Tracker
    print("\n💰 Testing Personal P&L Tracker:")
    chat_cleaner.clear_pnl_records()
    chat_cleaner.record_pnl_entry("Bajaj Housing Finance", 18190.0, gain_percent=121.4)
    chat_cleaner.record_pnl_entry("HDB Financial Services", 5400.0, gain_percent=36.0)
    summary = chat_cleaner.get_pnl_summary()
    assert summary["total_profit"] == 23590.0, f"Expected 23590, got {summary['total_profit']}"
    assert summary["total_trades"] == 2, f"Expected 2 trades, got {summary['total_trades']}"
    assert summary["win_rate"] == 100.0, f"Expected 100% win rate, got {summary['win_rate']}"
    print(f"   • Lifetime P&L recorded: +₹{summary['total_profit']:,.2f} across {summary['total_trades']} issues (Win rate: {summary['win_rate']:.0f}%).")

    print("\n🎉 ALL 12 PROACTIVE, STRATEGIC, & P&L TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    run_tests()
