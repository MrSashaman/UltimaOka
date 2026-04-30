import asyncio
import re
import sqlite3
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import timedelta
from time import monotonic

import discord

from database import add_warning_db, create_mod_case, get_user_warnings
from services import send_mod_log


AUTOMOD_DB_PATH = "automod.db"

DEFAULT_WORDS = [
    "хуй",
    "пизда",
    "член",
    "dick",
    "трахать",
    "трахнул",
    "fuck",
    "пидор",
    "pidor",
    "еблан",
    "shit",
    "ебать",
    "lox",
]

INVITE_RE = re.compile(
    r"(?:https?://)?(?:www\.)?(?:discord\.gg|discord(?:app)?\.com/invite)/[a-z0-9-]+",
    re.IGNORECASE,
)
LINK_RE = re.compile(r"(?:https?://|www\.)\S+", re.IGNORECASE)
WORD_CHARS_RE = re.compile(r"[a-zа-яё0-9_]", re.IGNORECASE)

_message_times: dict[tuple[int, int], deque[float]] = defaultdict(deque)
_last_messages: dict[tuple[int, int], deque[str]] = defaultdict(lambda: deque(maxlen=4))


@dataclass(slots=True)
class AutoModSettings:
    guild_id: int
    enabled: bool
    delete_messages: bool
    warn_users: bool
    block_invites: bool
    block_links: bool
    max_mentions: int
    caps_min_length: int
    caps_percent: int
    spam_max_messages: int
    spam_window_seconds: int
    timeout_after_warns: int
    timeout_minutes: int


@dataclass(slots=True)
class AutoModViolation:
    rule: str
    reason: str
    detail: str | None = None


def _connect():
    return sqlite3.connect(AUTOMOD_DB_PATH)


def init_automod_db():
    conn = _connect()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS automod_settings (
            guild_id INTEGER PRIMARY KEY,
            enabled INTEGER NOT NULL DEFAULT 1,
            delete_messages INTEGER NOT NULL DEFAULT 1,
            warn_users INTEGER NOT NULL DEFAULT 1,
            block_invites INTEGER NOT NULL DEFAULT 1,
            block_links INTEGER NOT NULL DEFAULT 0,
            max_mentions INTEGER NOT NULL DEFAULT 5,
            caps_min_length INTEGER NOT NULL DEFAULT 12,
            caps_percent INTEGER NOT NULL DEFAULT 80,
            spam_max_messages INTEGER NOT NULL DEFAULT 5,
            spam_window_seconds INTEGER NOT NULL DEFAULT 8,
            timeout_after_warns INTEGER NOT NULL DEFAULT 3,
            timeout_minutes INTEGER NOT NULL DEFAULT 10
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS automod_words (
            guild_id INTEGER NOT NULL,
            word TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (guild_id, word)
        )
    """)

    conn.commit()
    cursor.close()
    conn.close()


def ensure_guild_settings(guild_id: int):
    conn = _connect()
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO automod_settings (guild_id) VALUES (?)", (guild_id,))
    cursor.executemany(
        "INSERT OR IGNORE INTO automod_words (guild_id, word) VALUES (?, ?)",
        [(guild_id, word) for word in DEFAULT_WORDS],
    )
    conn.commit()
    cursor.close()
    conn.close()


def get_automod_settings(guild_id: int) -> AutoModSettings:
    ensure_guild_settings(guild_id)

    conn = _connect()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            guild_id,
            enabled,
            delete_messages,
            warn_users,
            block_invites,
            block_links,
            max_mentions,
            caps_min_length,
            caps_percent,
            spam_max_messages,
            spam_window_seconds,
            timeout_after_warns,
            timeout_minutes
        FROM automod_settings
        WHERE guild_id = ?
    """, (guild_id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()

    return AutoModSettings(
        guild_id=row[0],
        enabled=bool(row[1]),
        delete_messages=bool(row[2]),
        warn_users=bool(row[3]),
        block_invites=bool(row[4]),
        block_links=bool(row[5]),
        max_mentions=row[6],
        caps_min_length=row[7],
        caps_percent=row[8],
        spam_max_messages=row[9],
        spam_window_seconds=row[10],
        timeout_after_warns=row[11],
        timeout_minutes=row[12],
    )


def update_automod_settings(guild_id: int, **values):
    ensure_guild_settings(guild_id)

    allowed_columns = {
        "enabled",
        "delete_messages",
        "warn_users",
        "block_invites",
        "block_links",
        "max_mentions",
        "caps_min_length",
        "caps_percent",
        "spam_max_messages",
        "spam_window_seconds",
        "timeout_after_warns",
        "timeout_minutes",
    }
    updates = {key: value for key, value in values.items() if key in allowed_columns and value is not None}

    if not updates:
        return

    normalized = {
        key: int(value) if isinstance(value, bool) else value
        for key, value in updates.items()
    }
    assignments = ", ".join(f"{column} = ?" for column in normalized)

    conn = _connect()
    cursor = conn.cursor()
    cursor.execute(
        f"UPDATE automod_settings SET {assignments} WHERE guild_id = ?",
        (*normalized.values(), guild_id),
    )
    conn.commit()
    cursor.close()
    conn.close()


def add_automod_word(guild_id: int, word: str):
    ensure_guild_settings(guild_id)
    cleaned_word = word.lower().strip()

    conn = _connect()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR IGNORE INTO automod_words (guild_id, word) VALUES (?, ?)",
        (guild_id, cleaned_word),
    )
    conn.commit()
    cursor.close()
    conn.close()


def remove_automod_word(guild_id: int, word: str) -> bool:
    ensure_guild_settings(guild_id)

    conn = _connect()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM automod_words WHERE guild_id = ? AND word = ?",
        (guild_id, word.lower().strip()),
    )
    deleted = cursor.rowcount > 0
    conn.commit()
    cursor.close()
    conn.close()
    return deleted


def list_automod_words(guild_id: int) -> list[str]:
    ensure_guild_settings(guild_id)

    conn = _connect()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT word FROM automod_words WHERE guild_id = ? ORDER BY word",
        (guild_id,),
    )
    words = [row[0] for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return words


def _is_word_boundary(content: str, start: int, end: int) -> bool:
    before = start == 0 or WORD_CHARS_RE.fullmatch(content[start - 1]) is None
    after = end == len(content) or WORD_CHARS_RE.fullmatch(content[end]) is None
    return before and after


def _find_bad_word(content: str, words: list[str]) -> str | None:
    normalized = content.lower()

    for word in words:
        cleaned_word = word.lower().strip()
        if not cleaned_word:
            continue

        search_from = 0
        while True:
            index = normalized.find(cleaned_word, search_from)
            if index == -1:
                break

            end = index + len(cleaned_word)
            if _is_word_boundary(normalized, index, end):
                return cleaned_word

            search_from = end

    return None


def _detect_caps(content: str, settings: AutoModSettings) -> AutoModViolation | None:
    letters = [char for char in content if char.isalpha()]
    if len(letters) < settings.caps_min_length:
        return None

    upper_count = sum(1 for char in letters if char.isupper())
    percent = int((upper_count / len(letters)) * 100)

    if percent >= settings.caps_percent:
        return AutoModViolation(
            "CAPS",
            "Слишком много капса",
            f"{percent}% заглавных букв",
        )

    return None


def _detect_mentions(message: discord.Message, settings: AutoModSettings) -> AutoModViolation | None:
    mention_count = len(message.mentions) + len(message.role_mentions) + len(message.channel_mentions)

    if mention_count > settings.max_mentions:
        return AutoModViolation(
            "MENTIONS",
            "Слишком много упоминаний",
            f"{mention_count} упоминаний",
        )

    return None


def _detect_spam(message: discord.Message, settings: AutoModSettings) -> AutoModViolation | None:
    key = (message.guild.id, message.author.id)
    now = monotonic()
    window = _message_times[key]

    while window and now - window[0] > settings.spam_window_seconds:
        window.popleft()

    window.append(now)

    if len(window) > settings.spam_max_messages:
        return AutoModViolation(
            "SPAM",
            "Слишком много сообщений подряд",
            f"{len(window)} сообщений за {settings.spam_window_seconds} сек.",
        )

    normalized = " ".join(message.content.lower().split())
    if normalized:
        recent_messages = _last_messages[key]
        recent_messages.append(normalized)

        if len(recent_messages) >= 3 and len(set(recent_messages)) == 1:
            return AutoModViolation("SPAM", "Повтор одинаковых сообщений", "3 одинаковых сообщения подряд")

    return None


def _detect_violation(message: discord.Message, settings: AutoModSettings, words: list[str]) -> AutoModViolation | None:
    content = message.content or ""

    bad_word = _find_bad_word(content, words)
    if bad_word:
        return AutoModViolation("WORDS", "Запрещённые слова", f"слово: {bad_word}")

    if settings.block_invites and INVITE_RE.search(content):
        return AutoModViolation("INVITE", "Discord invite-ссылка", "invite")

    if settings.block_links and LINK_RE.search(content):
        return AutoModViolation("LINK", "Ссылки запрещены", "link")

    return (
        _detect_mentions(message, settings)
        or _detect_caps(content, settings)
        or _detect_spam(message, settings)
    )


def _should_ignore(message: discord.Message) -> bool:
    author = message.author
    if not isinstance(author, discord.Member):
        return True

    permissions = author.guild_permissions
    return permissions.administrator or permissions.manage_messages or permissions.moderate_members


async def _try_timeout(bot: discord.Client, message: discord.Message, minutes: int, reason: str) -> bool:
    if not isinstance(message.author, discord.Member):
        return False

    guild = message.guild
    bot_member = guild.me or guild.get_member(bot.user.id)
    if bot_member is None:
        return False

    if message.author == guild.owner or message.author.top_role >= bot_member.top_role:
        return False

    if not bot_member.guild_permissions.moderate_members:
        return False

    try:
        until = discord.utils.utcnow() + timedelta(minutes=minutes)
        await message.author.timeout(until, reason=reason)
        return True
    except discord.Forbidden:
        return False


async def run_automod(bot: discord.Client, message: discord.Message) -> bool:
    if message.guild is None or message.author.bot:
        return False

    settings = await asyncio.to_thread(get_automod_settings, message.guild.id)
    if not settings.enabled or _should_ignore(message):
        return False

    words = await asyncio.to_thread(list_automod_words, message.guild.id)
    violation = _detect_violation(message, settings, words)
    if violation is None:
        return False

    reason = violation.reason
    if violation.detail:
        reason = f"{reason} ({violation.detail})"

    if settings.delete_messages:
        try:
            await message.delete()
        except (discord.Forbidden, discord.NotFound):
            pass

    warn_id = None
    case_id = None
    created_at = None

    if settings.warn_users:
        warn_id, created_at = await asyncio.to_thread(
            add_warning_db,
            message.guild.id,
            message.author.id,
            bot.user.id,
            f"AutoMod: {reason}",
        )
        case_id, _ = await asyncio.to_thread(
            create_mod_case,
            message.guild.id,
            "WARN",
            message.author.id,
            bot.user.id,
            f"AutoMod: {reason}",
        )

    notice = f"{message.author.mention}, сообщение нарушает AutoMod: **{reason}**."
    if warn_id:
        notice += f" Выдано предупреждение `#{warn_id}`."

    try:
        await message.channel.send(notice, delete_after=10)
    except discord.Forbidden:
        pass

    if settings.warn_users and case_id and created_at:
        await send_mod_log(
            message.guild,
            "WARN",
            bot.user,
            message.author,
            f"AutoMod: {reason}",
            case_id,
            created_at,
        )

    if settings.warn_users and settings.timeout_after_warns > 0:
        warnings_count = len(await asyncio.to_thread(get_user_warnings, message.guild.id, message.author.id))

        if warnings_count >= settings.timeout_after_warns:
            timeout_reason = f"AutoMod: {warnings_count} предупреждений"
            timed_out = await _try_timeout(bot, message, settings.timeout_minutes, timeout_reason)

            if timed_out:
                duration_text = f"{settings.timeout_minutes} мин."
                timeout_case_id, timeout_created_at = await asyncio.to_thread(
                    create_mod_case,
                    message.guild.id,
                    "TIMEOUT",
                    message.author.id,
                    bot.user.id,
                    timeout_reason,
                    duration_text,
                )
                await send_mod_log(
                    message.guild,
                    "TIMEOUT",
                    bot.user,
                    message.author,
                    timeout_reason,
                    timeout_case_id,
                    timeout_created_at,
                    duration_text,
                )

    return True
