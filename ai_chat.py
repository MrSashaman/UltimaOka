import asyncio
import sqlite3
import sys
from collections import defaultdict, deque
from datetime import datetime, timezone

import discord


AI_CHAT_DB_PATH = "ai_chat.db"
AI_MODEL = "gpt-4o-mini"
MAX_HISTORY_MESSAGES = 12
MAX_DISCORD_MESSAGE_LENGTH = 1900

_channel_history: dict[tuple[int, int], deque[dict[str, str]]] = defaultdict(
    lambda: deque(maxlen=MAX_HISTORY_MESSAGES)
)


def _connect():
    return sqlite3.connect(AI_CHAT_DB_PATH)


def init_ai_chat_db():
    conn = _connect()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ai_chat_channels (
            guild_id INTEGER NOT NULL,
            channel_id INTEGER NOT NULL,
            created_by INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY (guild_id, channel_id)
        )
    """)

    conn.commit()
    cursor.close()
    conn.close()


def add_ai_chat_channel(guild_id: int, channel_id: int, created_by: int):
    init_ai_chat_db()
    conn = _connect()
    cursor = conn.cursor()

    created_at = datetime.now(timezone.utc).strftime("%d.%m.%Y %H:%M:%S UTC")
    cursor.execute("""
        INSERT OR REPLACE INTO ai_chat_channels (guild_id, channel_id, created_by, created_at)
        VALUES (?, ?, ?, ?)
    """, (guild_id, channel_id, created_by, created_at))

    conn.commit()
    cursor.close()
    conn.close()


def remove_ai_chat_channel(guild_id: int, channel_id: int) -> bool:
    init_ai_chat_db()
    conn = _connect()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM ai_chat_channels WHERE guild_id = ? AND channel_id = ?",
        (guild_id, channel_id),
    )
    deleted = cursor.rowcount > 0

    conn.commit()
    cursor.close()
    conn.close()
    clear_ai_chat_history(guild_id, channel_id)
    return deleted


def list_ai_chat_channels(guild_id: int) -> list[int]:
    init_ai_chat_db()
    conn = _connect()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT channel_id FROM ai_chat_channels WHERE guild_id = ? ORDER BY created_at",
        (guild_id,),
    )
    channels = [row[0] for row in cursor.fetchall()]

    cursor.close()
    conn.close()
    return channels


def is_ai_chat_channel(guild_id: int, channel_id: int) -> bool:
    init_ai_chat_db()
    conn = _connect()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT 1 FROM ai_chat_channels WHERE guild_id = ? AND channel_id = ?",
        (guild_id, channel_id),
    )
    exists = cursor.fetchone() is not None

    cursor.close()
    conn.close()
    return exists


def clear_ai_chat_history(guild_id: int, channel_id: int | None = None):
    if channel_id is not None:
        _channel_history.pop((guild_id, channel_id), None)
        return

    for key in list(_channel_history):
        if key[0] == guild_id:
            _channel_history.pop(key, None)


def _build_messages(message: discord.Message) -> list[dict[str, str]]:
    history_key = (message.guild.id, message.channel.id)
    history = _channel_history[history_key]

    messages = [
        {
            "role": "system",
            "content": (
                "Ты дружелюбный Discord AI-чат бота UltimaOka. "
                "Отвечай на русском, если пользователь не просит другой язык. "
                "Пиши кратко, полезно и без лишнего оформления. "
                "Не упоминай, что ты работаешь через g4f."
            ),
        }
    ]
    messages.extend(history)
    messages.append(
        {
            "role": "user",
            "content": f"{message.author.display_name}: {message.clean_content.strip()}",
        }
    )
    return messages


def _remember_reply(message: discord.Message, reply: str):
    history_key = (message.guild.id, message.channel.id)
    history = _channel_history[history_key]
    history.append(
        {
            "role": "user",
            "content": f"{message.author.display_name}: {message.clean_content.strip()}",
        }
    )
    history.append({"role": "assistant", "content": reply})


def _trim_discord_message(text: str) -> str:
    cleaned = text.strip()
    if len(cleaned) <= MAX_DISCORD_MESSAGE_LENGTH:
        return cleaned
    return cleaned[:MAX_DISCORD_MESSAGE_LENGTH - 3].rstrip() + "..."


async def generate_ai_reply(message: discord.Message) -> str:
    try:
        from g4f.client import AsyncClient
    except ImportError as exc:
        raise RuntimeError(
            "Библиотека g4f не установлена в Python, которым запущен бот. "
            f"Установи её так: \"{sys.executable}\" -m pip install -U \"g4f[all]\""
        ) from exc

    client = AsyncClient()
    response = await asyncio.wait_for(
        client.chat.completions.create(
            model=AI_MODEL,
            messages=_build_messages(message),
            web_search=False,
        ),
        timeout=60,
    )

    reply = response.choices[0].message.content
    if not reply:
        raise RuntimeError("Нейросеть вернула пустой ответ.")

    trimmed_reply = _trim_discord_message(reply)
    _remember_reply(message, trimmed_reply)
    return trimmed_reply


async def run_ai_chat(bot: discord.Client, message: discord.Message) -> bool:
    if message.guild is None or message.author.bot:
        return False

    if not message.content or not message.content.strip():
        return False

    if message.content.startswith("!"):
        return False

    enabled = await asyncio.to_thread(is_ai_chat_channel, message.guild.id, message.channel.id)
    if not enabled:
        return False

    async with message.channel.typing():
        try:
            reply = await generate_ai_reply(message)
        except Exception as exc:
            await message.reply(f"Не смог получить ответ нейросети: {exc}", mention_author=False)
            return True

    await message.reply(reply, mention_author=False)
    return True
