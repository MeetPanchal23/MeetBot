import time
import datetime
import sqlite3
import logging
from typing import List, Tuple, Dict
from collections import defaultdict

import config

logger = logging.getLogger("ChatCleaner")

def get_connection() -> sqlite3.Connection:
    """Returns a SQLite connection with timeout and row factory."""
    conn = sqlite3.connect(str(config.DB_FILE), timeout=15)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes SQLite tables and indexes for tracking messages."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                message_id INTEGER NOT NULL,
                sent_at REAL NOT NULL,
                is_pinned INTEGER NOT NULL DEFAULT 0,
                UNIQUE(chat_id, message_id)
            );
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_lookup 
            ON messages (chat_id, message_id);
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_expiry 
            ON messages (sent_at, is_pinned);
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alerts_sent (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ipo_name TEXT NOT NULL,
                trigger_type TEXT NOT NULL,
                last_gmp REAL DEFAULT 0,
                last_qib REAL DEFAULT 0,
                last_retail REAL DEFAULT 0,
                last_status TEXT DEFAULT '',
                sent_at REAL NOT NULL,
                UNIQUE(ipo_name, trigger_type)
            );
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pnl_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ipo_name TEXT NOT NULL,
                profit_amount REAL NOT NULL,
                gain_percent REAL DEFAULT 0.0,
                recorded_at REAL NOT NULL,
                date_str TEXT NOT NULL
            );
        """)
        conn.commit()
    finally:
        conn.close()
    logger.info("Chat cleaner database initialized with alerts_sent & pnl_records tracking.")

def record_message(chat_id: int, message_id: int, sent_at: float = None, is_pinned: bool = False):
    """
    Records a message into the tracking database.
    If already exists, preserves pinned status if previously pinned.
    """
    if sent_at is None:
        sent_at = time.time()
    pinned_val = 1 if is_pinned else 0

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO messages (chat_id, message_id, sent_at, is_pinned)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(chat_id, message_id) DO UPDATE SET
                is_pinned = MAX(messages.is_pinned, excluded.is_pinned);
        """, (chat_id, message_id, sent_at, pinned_val))
        conn.commit()
    except Exception as e:
        logger.error(f"Error recording message {message_id} in chat {chat_id}: {e}")
    finally:
        conn.close()

def mark_message_pinned(chat_id: int, message_id: int, is_pinned: bool = True):
    """
    Flags a message as pinned or unpinned.
    Pinned messages are completely exempted from automatic deletion.
    """
    pinned_val = 1 if is_pinned else 0
    now = time.time()
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO messages (chat_id, message_id, sent_at, is_pinned)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(chat_id, message_id) DO UPDATE SET
                is_pinned = ?;
        """, (chat_id, message_id, now, pinned_val, pinned_val))
        conn.commit()
        logger.info(f"Message {message_id} in chat {chat_id} pinned status updated to: {is_pinned}")
    except Exception as e:
        logger.error(f"Error updating pinned status for message {message_id} in chat {chat_id}: {e}")
    finally:
        conn.close()

def is_message_pinned(chat_id: int, message_id: int) -> bool:
    """Checks whether a message is marked as pinned."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT is_pinned FROM messages
            WHERE chat_id = ? AND message_id = ?;
        """, (chat_id, message_id))
        row = cursor.fetchone()
        if row:
            return bool(row["is_pinned"])
    except Exception as e:
        logger.error(f"Error checking pinned status for {message_id}: {e}")
    finally:
        conn.close()
    return False

def get_expired_unpinned_messages(max_age_seconds: float, limit: int = 200) -> List[Tuple[int, int]]:
    """
    Retrieves unpinned messages older than max_age_seconds.
    Returns list of (chat_id, message_id).
    """
    cutoff = time.time() - max_age_seconds
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT chat_id, message_id FROM messages
            WHERE is_pinned = 0 AND sent_at <= ?
            ORDER BY sent_at ASC
            LIMIT ?;
        """, (cutoff, limit))
        rows = cursor.fetchall()
        return [(r["chat_id"], r["message_id"]) for r in rows]
    except Exception as e:
        logger.error(f"Error querying expired messages: {e}")
        return []
    finally:
        conn.close()

def delete_recorded_messages(chat_id: int, message_ids: List[int]):
    """Removes message records from the tracking database."""
    if not message_ids:
        return
    conn = get_connection()
    try:
        cursor = conn.cursor()
        placeholders = ",".join("?" for _ in message_ids)
        cursor.execute(f"""
            DELETE FROM messages
            WHERE chat_id = ? AND message_id IN ({placeholders});
        """, [chat_id] + list(message_ids))
        conn.commit()
    except Exception as e:
        logger.error(f"Error deleting records for chat {chat_id}: {e}")
    finally:
        conn.close()

async def cleanup_expired_messages(bot, max_age_seconds: float = None) -> int:
    """
    Deletes messages older than max_age_seconds (default: AUTO_DELETE_HOURS).
    Guarantees that pinned messages are never deleted.
    Returns the count of successfully deleted messages.
    """
    if max_age_seconds is None:
        max_age_seconds = config.AUTO_DELETE_HOURS * 3600

    expired = get_expired_unpinned_messages(max_age_seconds=max_age_seconds, limit=200)
    if not expired:
        return 0

    # Group messages by chat_id
    chats_map: Dict[int, List[int]] = defaultdict(list)
    for chat_id, msg_id in expired:
        chats_map[chat_id].append(msg_id)

    total_deleted = 0

    for chat_id, msg_ids in chats_map.items():
        # Double check currently pinned message from Telegram ChatFullInfo
        try:
            chat_info = await bot.get_chat(chat_id=chat_id)
            if chat_info and chat_info.pinned_message:
                pinned_id = chat_info.pinned_message.message_id
                mark_message_pinned(chat_id, pinned_id, is_pinned=True)
                if pinned_id in msg_ids:
                    msg_ids.remove(pinned_id)
        except Exception as e:
            logger.debug(f"Could not verify chat pinned message for {chat_id}: {e}")

        if not msg_ids:
            continue

        # Attempt batch deletion (chunks of up to 100)
        chunk_size = 100
        for i in range(0, len(msg_ids), chunk_size):
            chunk = msg_ids[i:i + chunk_size]
            deleted_in_chunk = []
            try:
                # Telegram Bot API delete_messages
                await bot.delete_messages(chat_id=chat_id, message_ids=chunk)
                deleted_in_chunk = chunk
                total_deleted += len(chunk)
                logger.info(f"Batch deleted {len(chunk)} messages in chat {chat_id}")
            except Exception as batch_err:
                logger.debug(f"Batch deletion failed for chat {chat_id} ({batch_err}), falling back to individual: {batch_err}")
                for msg_id in chunk:
                    try:
                        await bot.delete_message(chat_id=chat_id, message_id=msg_id)
                        deleted_in_chunk.append(msg_id)
                        total_deleted += 1
                    except Exception as single_err:
                        # Message might already be deleted by user or expired
                        err_str = str(single_err).lower()
                        if "message to delete not found" in err_str or "message can't be deleted" in err_str:
                            deleted_in_chunk.append(msg_id)
                        else:
                            logger.debug(f"Single deletion error for msg {msg_id} in chat {chat_id}: {single_err}")
                            # Clean up from DB to prevent infinite retry loop
                            deleted_in_chunk.append(msg_id)

            if deleted_in_chunk:
                delete_recorded_messages(chat_id, deleted_in_chunk)

    return total_deleted


def get_all_unpinned_messages(chat_id: int) -> List[int]:
    """Retrieves all tracked unpinned message IDs for a chat."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT message_id FROM messages
            WHERE chat_id = ? AND is_pinned = 0
            ORDER BY sent_at DESC;
        """, (chat_id,))
        rows = cursor.fetchall()
        return [r["message_id"] for r in rows]
    except Exception as e:
        logger.error(f"Error querying all unpinned messages for chat {chat_id}: {e}")
        return []
    finally:
        conn.close()


async def clear_chat_instantly(bot, chat_id: int, trigger_message_id: int = None) -> int:
    """
    Clears all unpinned messages in a chat within 1-2 seconds using batch deletion.
    Guarantees pinned messages remain untouched and protected.
    """
    # 1. Double check current pinned message from Telegram API to protect it
    try:
        chat_info = await bot.get_chat(chat_id=chat_id)
        if chat_info and chat_info.pinned_message:
            pinned_id = chat_info.pinned_message.message_id
            mark_message_pinned(chat_id, pinned_id, is_pinned=True)
    except Exception as e:
        logger.debug(f"Could not verify pinned message for {chat_id}: {e}")

    # 2. Collect all unpinned message IDs
    msg_ids = get_all_unpinned_messages(chat_id)
    if trigger_message_id and trigger_message_id not in msg_ids:
        if not is_message_pinned(chat_id, trigger_message_id):
            msg_ids.insert(0, trigger_message_id)

    if not msg_ids:
        return 0

    total_deleted = 0
    chunk_size = 100
    for i in range(0, len(msg_ids), chunk_size):
        chunk = msg_ids[i:i + chunk_size]
        deleted_in_chunk = []
        try:
            await bot.delete_messages(chat_id=chat_id, message_ids=chunk)
            deleted_in_chunk = chunk
            total_deleted += len(chunk)
            logger.info(f"Instant clear: deleted {len(chunk)} messages in chat {chat_id}")
        except Exception as batch_err:
            logger.debug(f"Batch clear failed for {chat_id} ({batch_err}), falling back to single delete: {batch_err}")
            for msg_id in chunk:
                try:
                    await bot.delete_message(chat_id=chat_id, message_id=msg_id)
                    deleted_in_chunk.append(msg_id)
                    total_deleted += 1
                except Exception as single_err:
                    err_str = str(single_err).lower()
                    if "not found" in err_str or "can't be deleted" in err_str:
                        deleted_in_chunk.append(msg_id)
                    else:
                        deleted_in_chunk.append(msg_id)

        if deleted_in_chunk:
            delete_recorded_messages(chat_id, deleted_in_chunk)

    return total_deleted


# =======================================================
# PROACTIVE ALERT STATE MANAGEMENT (ANTI-SPAM MEMORY)
# =======================================================

def should_dispatch_alert(
    ipo_name: str,
    trigger_type: str,
    current_gmp: float = 0.0,
    current_qib: float = 0.0
) -> bool:
    """
    Determines whether a proactive alert should be dispatched.
    Guarantees zero-spam by remembering previous notifications in SQLite:
    - Never sent before -> Send (True).
    - For one-time alerts (Mandate, Shareholder Radar) -> Suppress if already dispatched.
    - For metric-driven alerts (Green Light, Trap) -> Suppress unless significant delta occurs.
    """
    clean_name = ipo_name.strip()
    clean_type = trigger_type.strip()
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT last_gmp, last_qib, sent_at FROM alerts_sent
            WHERE ipo_name = ? AND trigger_type = ?;
        """, (clean_name, clean_type))
        row = cursor.fetchone()
        if not row:
            return True

        # One-shot reminders should fire only once
        if "MANDATE" in clean_type or "SHAREHOLDER" in clean_type:
            return False

        last_gmp = float(row["last_gmp"])
        last_qib = float(row["last_qib"])

        # Green light re-triggers only on massive positive subscription jump (+15x)
        if clean_type == "GREEN_LIGHT":
            if current_qib >= (last_qib + 15.0) and current_qib >= config.MIN_QIB_SUBSCRIPTION:
                return True
            return False

        # Retail trap or avoid alerts are sent once to prevent repeating negative messages
        if "AVOID" in clean_type or "TRAP" in clean_type or "RISK" in clean_type:
            return False

        return False
    except Exception as e:
        logger.error(f"Error checking alert dispatch status for {clean_name}: {e}")
        return True
    finally:
        conn.close()

def record_alert_dispatched(
    ipo_name: str,
    trigger_type: str,
    current_gmp: float = 0.0,
    current_qib: float = 0.0,
    current_retail: float = 0.0,
    current_status: str = ""
):
    """Saves alert dispatch record into SQLite memory."""
    clean_name = ipo_name.strip()
    clean_type = trigger_type.strip()
    now = time.time()
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO alerts_sent (ipo_name, trigger_type, last_gmp, last_qib, last_retail, last_status, sent_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(ipo_name, trigger_type) DO UPDATE SET
                last_gmp = excluded.last_gmp,
                last_qib = excluded.last_qib,
                last_retail = excluded.last_retail,
                last_status = excluded.last_status,
                sent_at = excluded.sent_at;
        """, (clean_name, clean_type, current_gmp, current_qib, current_retail, current_status, now))
        conn.commit()
        logger.info(f"Recorded alert memory: [{clean_type}] for '{clean_name}'.")
    except Exception as e:
        logger.error(f"Error recording alert memory for {clean_name}: {e}")
    finally:
        conn.close()

def get_dispatched_alerts_count() -> int:
    """Returns count of recorded alerts in anti-spam memory."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM alerts_sent;")
        row = cursor.fetchone()
        return row[0] if row else 0
    except Exception:
        return 0
    finally:
        conn.close()

def clear_alerts_memory():
    """Wipes all alert history (primarily for manual test resets)."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM alerts_sent;")
        conn.commit()
    finally:
        conn.close()


# =======================================================
# PERSONAL P&L TRACKER STATE (REALIZED LISTING PROFITS)
# =======================================================

def record_pnl_entry(ipo_name: str, profit_amount: float, gain_percent: float = 0.0) -> int:
    """Records a realized IPO profit or loss entry."""
    now = time.time()
    date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO pnl_records (ipo_name, profit_amount, gain_percent, recorded_at, date_str)
            VALUES (?, ?, ?, ?, ?);
        """, (ipo_name.strip(), profit_amount, gain_percent, now, date_str))
        conn.commit()
        logger.info(f"Recorded P&L: {ipo_name} -> ₹{profit_amount:,.2f}")
        return cursor.lastrowid
    except Exception as e:
        logger.error(f"Error recording P&L entry for {ipo_name}: {e}")
        return 0
    finally:
        conn.close()

def get_pnl_summary() -> dict:
    """Retrieves Meet's lifetime, monthly, and trade-by-trade IPO profit summary."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT ipo_name, profit_amount, gain_percent, date_str FROM pnl_records ORDER BY recorded_at DESC;")
        rows = cursor.fetchall()

        total_profit = 0.0
        total_wins = 0
        total_trades = len(rows)
        monthly_map = defaultdict(float)
        recent_trades = []

        for r in rows:
            p = float(r["profit_amount"])
            total_profit += p
            if p > 0:
                total_wins += 1
            month_key = r["date_str"][:7] if len(r["date_str"]) >= 7 else "Recent"
            monthly_map[month_key] += p
            recent_trades.append({
                "ipo_name": r["ipo_name"],
                "profit_amount": p,
                "gain_percent": float(r["gain_percent"]),
                "date_str": r["date_str"]
            })

        win_rate = (total_wins / total_trades * 100.0) if total_trades > 0 else 0.0
        return {
            "total_profit": total_profit,
            "total_trades": total_trades,
            "total_wins": total_wins,
            "win_rate": win_rate,
            "monthly_map": dict(monthly_map),
            "recent_trades": recent_trades
        }
    except Exception as e:
        logger.error(f"Error fetching P&L summary: {e}")
        return {
            "total_profit": 0.0,
            "total_trades": 0,
            "total_wins": 0,
            "win_rate": 0.0,
            "monthly_map": {},
            "recent_trades": []
        }
    finally:
        conn.close()

def clear_pnl_records():
    """Wipes all P&L records (for testing)."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM pnl_records;")
        conn.commit()
    finally:
        conn.close()



