import sqlite3

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