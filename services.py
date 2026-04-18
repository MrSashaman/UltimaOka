import random
from datetime import datetime, timedelta, timezone

import SI
import botstatus
import discord
from discord.ext import tasks
from discord import ui


custom_text = None
_change_status_started = False


def format_duration(days: int = 0, hours: int = 0, minutes: int = 0) -> str:
    parts = []
    if days > 0:
        parts.append(f"{days}д")
    if hours > 0:
        parts.append(f"{hours}ч")
    if minutes > 0:
        parts.append(f"{minutes}м")
    return " ".join(parts) if parts else "Не указано"


def parse_timeout_delta(days: int = 0, hours: int = 0, minutes: int = 0) -> timedelta:
    return timedelta(days=days, hours=hours, minutes=minutes)


def get_custom_status() -> str | None:
    return custom_text


async def set_custom_status(bot: discord.Client, text: str | None) -> None:
    global custom_text
    custom_text = text

    if custom_text:
        await bot.change_presence(
            status=discord.Status.online,
            activity=discord.Game(name=custom_text)
        )


async def reset_custom_status() -> None:
    global custom_text
    custom_text = None


async def send_mod_log(
    guild: discord.Guild,
    action: str,
    moderator: discord.Member | discord.User,
    target: discord.Member | discord.User,
    reason: str,
    case_id: int,
    created_at: str,
    duration: str | None = None
) -> None:
    log_channel = guild.get_channel(SI.LOG_CHANNEL_ID)
    if log_channel is None:
        return

    colors = {
        "BAN": discord.Color.red(),
        "MUTE": discord.Color.orange(),
        "UNMUTE": discord.Color.green(),
        "WARN": discord.Color.gold(),
        "TIMEOUT": discord.Color.dark_orange(),
        "UNBAN": discord.Color.green(),
    }

    embed = discord.Embed(
        title=f"Модерация | {action}",
        color=colors.get(action.upper(), discord.Color.blurple()),
        timestamp=datetime.now(timezone.utc)
    )

    embed.add_field(name="Модератор", value=f"{moderator}\n`{moderator.id}`", inline=False)
    embed.add_field(name="Пользователь", value=f"{target}\n`{target.id}`", inline=False)
    embed.add_field(name="Причина", value=reason, inline=False)
    embed.add_field(name="ID наказания", value=f"`{case_id}`", inline=True)
    embed.add_field(name="ID пользователя", value=f"`{target.id}`", inline=True)
    embed.add_field(name="ID модератора", value=f"`{moderator.id}`", inline=True)

    if duration:
        embed.add_field(name="Время", value=duration, inline=False)

    embed.set_footer(text=f"Создано: {created_at}")

    await log_channel.send(embed=embed)


async def can_moderate(interaction: discord.Interaction, target: discord.Member) -> bool:
    if interaction.guild is None or not isinstance(interaction.user, discord.Member):
        await interaction.response.send_message(
            "❌ Команда доступна только на сервере.",
            ephemeral=True
        )
        return False

    if target == interaction.user:
        await interaction.response.send_message(
            "❌ Нельзя использовать эту команду на себе.",
            ephemeral=True
        )
        return False

    if target == interaction.guild.owner:
        await interaction.response.send_message(
            "❌ Нельзя наказать владельца сервера.",
            ephemeral=True
        )
        return False

    if target.top_role >= interaction.user.top_role and interaction.user != interaction.guild.owner:
        await interaction.response.send_message(
            "❌ Этот пользователь выше или равен вам по роли.",
            ephemeral=True
        )
        return False

    if interaction.guild.me and target.top_role >= interaction.guild.me.top_role:
        await interaction.response.send_message(
            "❌ Роль пользователя выше или равна роли бота.",
            ephemeral=True
        )
        return False

    return True


class AdminAuthModal(ui.Modal, title="Подтверждение админ-прав."):
    password_input = ui.TextInput(
        label="Введите пароль",
        placeholder="Пароль...",
        min_length=4,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message(
                "❌ Команда доступна только на сервере.",
                ephemeral=True
            )
            return

        member = interaction.user
        guild = interaction.guild
        bot_member = guild.me

        verified_role = guild.get_role(SI.VERIFIED_ADMIN_ROLE_ID)
        blacklist_role = guild.get_role(SI.BLACKLIST_ROLE_ID)

        if self.password_input.value == SI.ADMIN_PASSWORD:
            if verified_role is None:
                await interaction.response.send_message(
                    "❌ Роль верификации не найдена.",
                    ephemeral=True
                )
                return

            if bot_member is None:
                await interaction.response.send_message(
                    "❌ Не удалось получить объект бота на сервере.",
                    ephemeral=True
                )
                return

            if verified_role >= bot_member.top_role:
                await interaction.response.send_message(
                    "❌ Бот не может выдать роль верификации. Подними роль бота выше.",
                    ephemeral=True
                )
                return

            try:
                await member.add_roles(
                    verified_role,
                    reason="Успешная admin security верификация"
                )
                await interaction.response.send_message(
                    f"✅ **Пароль принят**. Роль защиты выдана: `{member}`!",
                    ephemeral=True
                )
            except discord.Forbidden:
                await interaction.response.send_message(
                    "❌ Бот не может выдать роль. Проверь права и иерархию ролей.",
                    ephemeral=True
                )
            except Exception as e:
                await interaction.response.send_message(
                    f"❌ Ошибка: {e}",
                    ephemeral=True
                )
            return

        if bot_member is None:
            await interaction.response.send_message(
                "❌ Не удалось получить объект бота на сервере.",
                ephemeral=True
            )
            return

        removable_roles = [
            role for role in member.roles
            if role != guild.default_role
            and role != blacklist_role
            and role < bot_member.top_role
        ]

        try:
            if removable_roles:
                await member.remove_roles(
                    *removable_roles,
                    reason="Неверный пароль admin security"
                )

            log_channel = guild.get_channel(SI.LOG_CHANNEL_ID) 

            if log_channel:
                embed = discord.Embed(
                    title="🚨 Нарушение безопасности",
                    description=f"Пользователь {member.mention} ввел **неверный пароль**.",
                    color=discord.Color.red()
                )
                embed.add_field(
                    name="Действие",
                    value="Сняты все доступные роли и выдан ЧС."
                )
                embed.set_footer(text=f"ID: {member.id}")
                await log_channel.send(embed=embed)

            if blacklist_role is None:
                await interaction.response.send_message(
                    "❌ ЧС-роль не найдена. Роли сняты, но ЧС-роль не выдана.",
                    ephemeral=True
                )
                return

            if blacklist_role >= bot_member.top_role:
                await interaction.response.send_message(
                    "❌ Бот не может выдать ЧС-роль. Подними роль бота выше.",
                    ephemeral=True
                )
                return

            await member.add_roles(
                blacklist_role,
                reason="Неверный пароль admin security"
            )
            await interaction.response.send_message(
                "❌ Неверный пароль. Роли сняты, выдана ЧС-роль.",
                ephemeral=True
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Бот не может управлять ролями. Проверь права и иерархию ролей.",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Ошибка: {e}",
                ephemeral=True
            )


@tasks.loop(seconds=20)
async def change_status():
    global custom_text

    try:
        if custom_text:
            await change_status.bot.change_presence(
                status=discord.Status.online,
                activity=discord.Game(name=custom_text)
            )
            return

        statuses = getattr(botstatus, "botstatuses", None)
        if not statuses or not isinstance(statuses, (list, tuple)):
            print("[STATUS] Список статусов пустой или неверный.")
            return

        await change_status.bot.change_presence(
            status=discord.Status.online,
            activity=discord.Game(name=random.choice(statuses))
        )

    except Exception as e:
        print(f"[STATUS ERROR] {e}")


@change_status.before_loop
async def before_change_status():
    await change_status.bot.wait_until_ready()


@change_status.error
async def change_status_error(error):
    print(f"[STATUS LOOP FATAL ERROR] {error}")


def setup_status_tasks(bot: discord.Client) -> None:
    global _change_status_started

    change_status.bot = bot

    if not _change_status_started and not change_status.is_running():
        change_status.start()
        _change_status_started = True