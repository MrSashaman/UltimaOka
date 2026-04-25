
import sqlite3

ROLE_DB_PATH = "roleshop.db"

def _connect_role():
    return sqlite3.connect(ROLE_DB_PATH)

def init_role_shop():
    conn = _connect_role()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS role_shop (
            guild_id INTEGER,
            role_id INTEGER,
            price INTEGER,
            seller_id INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY(guild_id, role_id)
        )
    """)
    cursor.execute("PRAGMA table_info(role_shop)")
    columns = {row[1] for row in cursor.fetchall()}
    if "created_at" not in columns:
        cursor.execute("ALTER TABLE role_shop ADD COLUMN created_at TIMESTAMP")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS role_shop_listings (
            listing_id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER NOT NULL,
            role_id INTEGER NOT NULL,
            price INTEGER NOT NULL,
            seller_id INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(guild_id, role_id, seller_id)
        )
    """)
    cursor.execute("""
        INSERT OR IGNORE INTO role_shop_listings (guild_id, role_id, price, seller_id, created_at)
        SELECT guild_id, role_id, price, seller_id, COALESCE(created_at, CURRENT_TIMESTAMP)
        FROM role_shop
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_roles (
            user_id INTEGER,
            role_id INTEGER,
            guild_id INTEGER,
            PRIMARY KEY(user_id, role_id, guild_id)
        )
    """)
    conn.commit()
    cursor.close()
    conn.close()

async def add_role_to_shop(guild_id, role_id, price, seller_id=0):
    conn = _connect_role()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO role_shop_listings (guild_id, role_id, price, seller_id, created_at)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(guild_id, role_id, seller_id) DO UPDATE SET
            price = excluded.price,
            created_at = CURRENT_TIMESTAMP
    """, (guild_id, role_id, price, seller_id))
    conn.commit()
    cursor.close()
    conn.close()

async def remove_role_from_shop(guild_id, role_id):
    conn = _connect_role()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM role_shop_listings WHERE guild_id=? AND role_id=?", (guild_id, role_id))
    conn.commit()
    cursor.close()
    conn.close()

async def remove_shop_listing(listing_id):
    conn = _connect_role()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM role_shop_listings WHERE listing_id=?", (listing_id,))
    conn.commit()
    cursor.close()
    conn.close()

async def get_shop_listing(listing_id):
    conn = _connect_role()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT listing_id, guild_id, role_id, price, seller_id FROM role_shop_listings WHERE listing_id=?",
        (listing_id,)
    )
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return row

async def get_shop_role(guild_id, role_id, seller_id=None):
    conn = _connect_role()
    cursor = conn.cursor()
    if seller_id is None:
        cursor.execute(
            "SELECT listing_id, role_id, price, seller_id FROM role_shop_listings WHERE guild_id=? AND role_id=?",
            (guild_id, role_id)
        )
    else:
        cursor.execute(
            """
            SELECT listing_id, role_id, price, seller_id
            FROM role_shop_listings
            WHERE guild_id=? AND role_id=? AND seller_id=?
            """,
            (guild_id, role_id, seller_id)
        )
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return row


async def list_shop_roles(guild_id):
    conn = _connect_role()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT listing_id, role_id, price, seller_id
        FROM role_shop_listings
        WHERE guild_id=?
        ORDER BY created_at DESC
        """,
        (guild_id,)
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows

async def add_role_to_user(user_id, role_id, guild_id):
    conn = _connect_role()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO user_roles (user_id, role_id, guild_id) VALUES (?, ?, ?)",
                   (user_id, role_id, guild_id))
    conn.commit()
    cursor.close()
    conn.close()

async def remove_role_from_user(user_id, role_id, guild_id):
    conn = _connect_role()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM user_roles WHERE user_id=? AND role_id=? AND guild_id=?", (user_id, role_id, guild_id))
    conn.commit()
    cursor.close()
    conn.close()

async def user_has_role(user_id, role_id, guild_id):
    conn = _connect_role()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT 1 FROM user_roles WHERE user_id=? AND role_id=? AND guild_id=?",
        (user_id, role_id, guild_id)
    )
    exists = cursor.fetchone() is not None
    cursor.close()
    conn.close()
    return exists

async def list_user_roles(user_id, guild_id):
    conn = _connect_role()
    cursor = conn.cursor()
    cursor.execute("SELECT role_id FROM user_roles WHERE user_id=? AND guild_id=?", (user_id, guild_id))
    rows = [r[0] for r in cursor.fetchall()]
    cursor.close()
    conn.close()
    return rows
