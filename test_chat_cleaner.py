import asyncio
import time
import unittest
from unittest.mock import AsyncMock, MagicMock
from pathlib import Path

import config
# Redirect DB to a temporary test DB
TEST_DB = Path(__file__).parent / "test_chat_history.db"
config.DB_FILE = TEST_DB

import chat_cleaner

import gc

class TestChatCleaner(unittest.TestCase):
    def setUp(self):
        gc.collect()
        if TEST_DB.exists():
            try:
                TEST_DB.unlink()
            except Exception:
                pass
        chat_cleaner.init_db()

    def tearDown(self):
        gc.collect()
        if TEST_DB.exists():
            try:
                TEST_DB.unlink()
            except Exception:
                pass

    def test_record_and_pin_message(self):
        chat_id = 123456
        msg_id = 101

        # Record normal message
        chat_cleaner.record_message(chat_id, msg_id, sent_at=time.time(), is_pinned=False)
        self.assertFalse(chat_cleaner.is_message_pinned(chat_id, msg_id))

        # Mark message as pinned
        chat_cleaner.mark_message_pinned(chat_id, msg_id, is_pinned=True)
        self.assertTrue(chat_cleaner.is_message_pinned(chat_id, msg_id))

        # Subsequent recording does not unpin the message
        chat_cleaner.record_message(chat_id, msg_id, sent_at=time.time(), is_pinned=False)
        self.assertTrue(chat_cleaner.is_message_pinned(chat_id, msg_id))

    def test_expired_unpinned_filtering(self):
        chat_id = 123456
        now = time.time()
        one_day_ago = now - 90000  # > 24 hours ago
        recent = now - 1800        # 30 mins ago

        # Message 1: Expired and unpinned -> should be returned for deletion
        chat_cleaner.record_message(chat_id, 1, sent_at=one_day_ago, is_pinned=False)

        # Message 2: Expired BUT pinned -> MUST STAY (never deleted)
        chat_cleaner.record_message(chat_id, 2, sent_at=one_day_ago, is_pinned=True)

        # Message 3: Recent and unpinned -> should not be expired yet
        chat_cleaner.record_message(chat_id, 3, sent_at=recent, is_pinned=False)

        expired = chat_cleaner.get_expired_unpinned_messages(max_age_seconds=86400)
        self.assertEqual(len(expired), 1)
        self.assertEqual(expired[0], (chat_id, 1))

    def test_cleanup_expired_messages_with_mock_bot(self):
        async def run_async():
            chat_id = 123456
            one_day_ago = time.time() - 90000

            # Add two expired messages: msg 10 and msg 20
            chat_cleaner.record_message(chat_id, 10, sent_at=one_day_ago, is_pinned=False)
            chat_cleaner.record_message(chat_id, 20, sent_at=one_day_ago, is_pinned=False)

            # Mock bot
            bot = MagicMock()
            chat_full_info = MagicMock()
            # Simulate that msg 20 is currently pinned in Telegram!
            chat_full_info.pinned_message = MagicMock(message_id=20)
            bot.get_chat = AsyncMock(return_value=chat_full_info)
            bot.delete_messages = AsyncMock(return_value=True)

            deleted_count = await chat_cleaner.cleanup_expired_messages(bot, max_age_seconds=86400)

            # Only msg 10 should be deleted because msg 20 is pinned
            self.assertEqual(deleted_count, 1)
            bot.delete_messages.assert_called_once_with(chat_id=chat_id, message_ids=[10])

            # Ensure msg 20 was marked pinned in DB
            self.assertTrue(chat_cleaner.is_message_pinned(chat_id, 20))

            # Database should no longer contain msg 10
            expired_after = chat_cleaner.get_expired_unpinned_messages(max_age_seconds=86400)
            self.assertEqual(len(expired_after), 0)

        asyncio.run(run_async())

    def test_cleanup_fallback_to_single_deletion(self):
        async def run_async():
            chat_id = 999
            one_day_ago = time.time() - 90000
            chat_cleaner.record_message(chat_id, 55, sent_at=one_day_ago, is_pinned=False)

            bot = MagicMock()
            bot.get_chat = AsyncMock(return_value=MagicMock(pinned_message=None))
            # Batch delete raises exception
            bot.delete_messages = AsyncMock(side_effect=Exception("Batch deletion not supported"))
            bot.delete_message = AsyncMock(return_value=True)

            deleted_count = await chat_cleaner.cleanup_expired_messages(bot, max_age_seconds=86400)
            self.assertEqual(deleted_count, 1)
            bot.delete_message.assert_called_once_with(chat_id=chat_id, message_id=55)

        asyncio.run(run_async())

    def test_incoming_message_tracker(self):
        import bot
        async def run_async():
            chat_id = 777
            update = MagicMock()
            update.effective_chat = MagicMock(id=chat_id)
            msg = MagicMock(message_id=300, date=None)
            # Simulate a message that contains a pinned_message status update
            pinned_target = MagicMock(message_id=250)
            msg.pinned_message = pinned_target
            update.effective_message = msg

            await bot.incoming_message_tracker(update, MagicMock())

            # Message 300 should be recorded
            self.assertFalse(chat_cleaner.is_message_pinned(chat_id, 300))
            # Target message 250 should be recorded as pinned!
            self.assertTrue(chat_cleaner.is_message_pinned(chat_id, 250))

        asyncio.run(run_async())


class TestProfitFilterAndAlerts(unittest.TestCase):
    def test_profit_filter_budget_and_gmp(self):
        import engine
        from scraper import IPODetails

        # Profitable IPO: ₹15,000 cost, 35% GMP
        good_ipo = IPODetails(
            name="Alpha Corp",
            sector="Tech",
            upper_price=500.0,
            lot_size=30,
            total_cost=15000.0,
            gmp=175.0,
            gmp_percent=35.0,
            est_profit=5250.0,
            qib_sub=30.0,
            retail_sub=8.0,
            status="Active"
        )
        is_prof, reason = engine.is_profitable_for_meet(good_ipo)
        self.assertTrue(is_prof)

        # Low GMP IPO: 10% GMP -> should be filtered out
        low_gmp_ipo = IPODetails(
            name="Beta Corp",
            sector="Retail",
            upper_price=300.0,
            lot_size=50,
            total_cost=15000.0,
            gmp=30.0,
            gmp_percent=10.0,
            est_profit=1500.0,
            qib_sub=5.0,
            retail_sub=2.0,
            status="Active"
        )
        is_prof, reason = engine.is_profitable_for_meet(low_gmp_ipo)
        self.assertFalse(is_prof)
        self.assertIn("below profit threshold", reason)

        # Over-budget IPO: ₹25,000 cost -> should be filtered out
        expensive_ipo = IPODetails(
            name="Gamma Corp",
            sector="Finance",
            upper_price=1000.0,
            lot_size=25,
            total_cost=25000.0,
            gmp=400.0,
            gmp_percent=40.0,
            est_profit=10000.0,
            status="Active"
        )
        is_prof, reason = engine.is_profitable_for_meet(expensive_ipo)
        self.assertFalse(is_prof)
        self.assertIn("outside budget range", reason)

        # Day 3 Retail Trap: Retail 15x, QIB 2x -> should be filtered out
        trap_ipo = IPODetails(
            name="Trap Corp",
            sector="Infra",
            upper_price=150.0,
            lot_size=100,
            total_cost=15000.0,
            gmp=45.0,
            gmp_percent=30.0,
            est_profit=4500.0,
            qib_sub=2.0,
            retail_sub=15.0,
            current_day=3,
            status="Active"
        )
        is_prof, reason = engine.is_profitable_for_meet(trap_ipo, is_day3=True)
        self.assertFalse(is_prof)
        self.assertIn("Retail trap", reason)

    def test_alert_formatting(self):
        import engine
        from scraper import IPODetails

        ipo = IPODetails(
            name="Tata Tech",
            sector="Automotive",
            upper_price=500.0,
            lot_size=30,
            total_cost=15000.0,
            gmp=200.0,
            gmp_percent=40.0,
            est_profit=6000.0,
            qib_sub=42.5,
            retail_sub=12.0
        )
        alert = engine.generate_high_profit_alert(ipo)
        self.assertIn("MEET PANCHAL ALERT | HIGH-PROFIT IPO DETECTED!", alert)
        self.assertIn("Hey Meet Panchal", alert)
        self.assertIn("Tata Tech", alert)
        self.assertIn("₹15,000", alert)
        self.assertIn("+₹6,000", alert)
        self.assertIn("+40.0%", alert)
        self.assertIn("QIB 42.5x", alert)
        self.assertIn("Submit before 3:30 PM IST", alert)
        self.assertIn("Approve your UPI mandate before 4:30 PM IST sharp!", alert)

if __name__ == "__main__":
    unittest.main()


