import sqlite3
from datetime import datetime, timezone




class Database:
    def __init__(self, db_path="users.db"):
        self.db_path = db_path
        self._create_table()

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _create_table(self):
        conn = self._connect()
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                balance INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        cursor.close()
        conn.close()

    def ensure_user(self, user_id: int):
        conn = self._connect()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR IGNORE INTO users (user_id, balance)
            VALUES (?, ?)
        """, (user_id, 0))

        conn.commit()
        cursor.close()
        conn.close()

    def add_balance(self, user_id: int, amount: int):
        conn = self._connect()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR IGNORE INTO users (user_id, balance)
            VALUES (?, ?)
        """, (user_id, 0))

        cursor.execute("""
            UPDATE users
            SET balance = balance + ?
            WHERE user_id = ?
        """, (amount, user_id))

        conn.commit()
        cursor.close()
        conn.close()

    def get_balance(self, user_id: int) -> int:
        conn = self._connect()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT balance FROM users WHERE user_id = ?
        """, (user_id,))

        row = cursor.fetchone()

        cursor.close()
        conn.close()

        return row[0] if row else 0



MOD_DB_PATH = "moderation.db"


def _connect_mod():
    return sqlite3.connect(MOD_DB_PATH)


def init_mod_db():
    conn = _connect_mod()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mod_cases (
            case_id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            target_user_id INTEGER NOT NULL,
            moderator_id INTEGER NOT NULL,
            reason TEXT NOT NULL,
            duration TEXT,
            created_at TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS warnings (
            warn_id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            moderator_id INTEGER NOT NULL,
            reason TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    conn.commit()
    cursor.close()
    conn.close()


def create_mod_case(
    guild_id: int,
    action: str,
    target_user_id: int,
    moderator_id: int,
    reason: str,
    duration: str | None = None
):
    conn = _connect_mod()
    cursor = conn.cursor()

    created_at = datetime.now(timezone.utc).strftime("%d.%m.%Y %H:%M:%S UTC")

    cursor.execute("""
        INSERT INTO mod_cases (guild_id, action, target_user_id, moderator_id, reason, duration, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (guild_id, action, target_user_id, moderator_id, reason, duration, created_at))

    case_id = cursor.lastrowid

    conn.commit()
    cursor.close()
    conn.close()

    return case_id, created_at


def add_warning_db(
    guild_id: int,
    user_id: int,
    moderator_id: int,
    reason: str
):
    conn = _connect_mod()
    cursor = conn.cursor()

    created_at = datetime.now(timezone.utc).strftime("%d.%m.%Y %H:%M:%S UTC")

    cursor.execute("""
        INSERT INTO warnings (guild_id, user_id, moderator_id, reason, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (guild_id, user_id, moderator_id, reason, created_at))

    warn_id = cursor.lastrowid

    conn.commit()
    cursor.close()
    conn.close()

    return warn_id, created_at


def get_user_warnings(guild_id: int, user_id: int):
    conn = _connect_mod()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT warn_id, moderator_id, reason, created_at
        FROM warnings
        WHERE guild_id = ? AND user_id = ?
        ORDER BY warn_id DESC
    """, (guild_id, user_id))

    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    return rows