import asyncio
import random
from datetime import timedelta

import SI
import discord
from discord import app_commands

from database import (
    create_mod_case,
    add_warning_db,
    get_user_warnings,
)
from services import (
    AdminAuthModal,
    can_moderate,
    send_mod_log,
    set_custom_status,
    reset_custom_status,
)


def setup_commands(bot, db):


    @bot.tree.command(name="setcustomstatus", description="Установить кастомный статус бота")
    @app_commands.checks.has_permissions(administrator=True)
    async def customstatusbot(interaction: discord.Interaction, text: str):
        if text.lower() == "сброс":
            await reset_custom_status()
            await interaction.response.send_message(
                "✅ Кастомный статус сброшен. Возвращаюсь к рандомным статусам.",
                ephemeral=True
            )
            return

        await set_custom_status(bot, text)
        await interaction.response.send_message(
            f"✅ Статус изменен на: **{text}**",
            ephemeral=True
        )

    @customstatusbot.error
    async def customstatusbot_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            if interaction.response.is_done():
                await interaction.followup.send("❌ У вас недостаточно прав!", ephemeral=True)
            else:
                await interaction.response.send_message("❌ У вас недостаточно прав!", ephemeral=True)

    @bot.tree.command(name="adminsecurity", description="Подтверждение админ-прав")
    async def adminsecurity(interaction: discord.Interaction):
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message(
                "❌ Команда доступна только на сервере.",
                ephemeral=True
            )
            return

        has_access_role = any(role.id == SI.ADMIN_ACCESS_ROLE_ID for role in interaction.user.roles)

        if not has_access_role:
            await interaction.response.send_message(
                "[❌] У вас нет доступа к этой команде.",
                ephemeral=True
            )
            return

        await interaction.response.send_modal(AdminAuthModal())

    gif_list = ["https://media0.giphy.com/media/a5viI92PAF89q/giphy.gif", "https://tenor.com/ecUoBs2k3YQ.gif", "https://tenor.com/bTTKG.gif"]

    @bot.tree.command(name="gif", description="random gif")
    async def rgif(interaction: discord.Interaction):
        await interaction.response.send_message(random.choice(gif_list))
        
    @bot.tree.command(name="ping", description="Check ping")
    async def ping(interaction: discord.Interaction):
        await interaction.response.send_message(f"Pong: `{round(bot.latency * 1000)}ms`")

    @bot.tree.command(name="getuseravatar", description="Получить аватар пользователя")
    async def getavatar(interaction: discord.Interaction, member: discord.Member):
        embed = discord.Embed(
            title=f"Аватар {member.name}",
            color=discord.Color.blue()
        )
        embed.set_image(url=member.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    @bot.tree.command(name="roll", description="Random Number!")
    async def randomnum(interaction: discord.Interaction):
        rnum = random.randint(1, 90)
        await interaction.response.send_message(f"** Твоё рандомное число:** {rnum}")

    @bot.tree.command(name="debug_info", description="DEBUG INFO ABOUT SERVER..")
    @app_commands.checks.has_permissions(administrator=True)
    async def debuginfo(interaction: discord.Interaction):
        guild = interaction.guild

        if guild is None:
            await interaction.response.send_message(
                "❌ Команда доступна только на сервере.",
                ephemeral=True
            )
            return

        bot_count = sum(1 for member in guild.members if member.bot)
        human_count = guild.member_count - bot_count

        await interaction.response.send_message(
            f"`[🛠️]` **DEBUG PANEL** `[🛠️]`\n"
            f"👑 **Владелец:** {guild.owner}\n"
            f"👥 **Всего участников:** {guild.member_count}\n"
            f"👤 **Людей:** {human_count}\n"
            f"🤖 **Ботов:** {bot_count}\n"
            f"📅 **Дата создания:** {guild.created_at.strftime('%d.%m.%Y')}\n"
            f"🆔 **ID сервера:** {guild.id}"
        )

    @debuginfo.error
    async def debuginfo_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            if interaction.response.is_done():
                await interaction.followup.send(
                    "❌ У вас недостаточно прав для этой команды!",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    "❌ У вас недостаточно прав для этой команды!",
                    ephemeral=True
                )



    @bot.tree.command(name="balance", description="Посмотреть баланс")
    async def balance(interaction: discord.Interaction, member: discord.Member | None = None):
        target = member or interaction.user
        await asyncio.to_thread(db.ensure_user, target.id)
        user_balance = await asyncio.to_thread(db.get_balance, target.id)

        await interaction.response.send_message(
            f"💳 Баланс пользователя **{target.display_name}**: `{user_balance}`₵"
        )

    @bot.tree.command(name="bonus", description="Бонус")
    @app_commands.checks.cooldown(1, 3600)
    async def freebonus(interaction: discord.Interaction):
        user_id = interaction.user.id
        bonus = 100

        await asyncio.to_thread(db.ensure_user, user_id)
        await asyncio.to_thread(db.add_balance, user_id, bonus)

        await interaction.response.send_message(
            f"🏆 {interaction.user.mention}, вы получили бонус в размере: {bonus} ₵"
        )

    @freebonus.error
    async def freebonus_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CommandOnCooldown):
            minutes = round(error.retry_after / 60)

            if interaction.response.is_done():
                await interaction.followup.send(
                    f"⏳ Ты уже получал свой бонус! Приходи через **{minutes} мин.**",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    f"⏳ Ты уже получал свой бонус! Приходи через **{minutes} мин.**",
                    ephemeral=True
                )

    @bot.tree.command(name="work", description="Выйти на работу и получить зарплату")
    @app_commands.checks.cooldown(1, 3600)
    async def work(interaction: discord.Interaction):
        salary = random.randint(50, 250)
        jobs = [
            "Поваром",
            "Пожарным",
            "Программистом",
            "Охранником",
            "Президентом",
            "Гражданином Чехословакии",
            "Главой Евро-Коммисии"
        ]
        job = random.choice(jobs)

        await asyncio.to_thread(db.add_balance, interaction.user.id, salary)

        await interaction.response.send_message(
            f"👷 Ты поработал **{job}** и получил: `{salary}`₵\n"
        )

    @work.error
    async def work_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CommandOnCooldown):
            minutes = round(error.retry_after / 60)

            if interaction.response.is_done():
                await interaction.followup.send(
                    f"⏳ Ты слишком устал! Приходи через **{minutes} мин.**",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    f"⏳ Ты слишком устал! Приходи через **{minutes} мин.**",
                    ephemeral=True
                )

    @bot.tree.command(name="luckybet", description="Сделать ставку")
    async def luckybet(interaction: discord.Interaction):
        balance_value = await asyncio.to_thread(db.get_balance, interaction.user.id)

        await interaction.response.send_message("`[🎩]` Введите сумму ставки:")

        def check(m: discord.Message):
            return m.author == interaction.user and m.channel == interaction.channel

        try:
            msg = await bot.wait_for("message", check=check, timeout=30.0)

            if not msg.content.isdigit():
                await interaction.followup.send("[🚫] Ошибка: введите числовое значение.")
                return

            amount = int(msg.content)

            if amount > balance_value:
                await interaction.followup.send("[🚫] Недостаточно денег.")
                return

            if amount <= 0:
                await interaction.followup.send("[🚫] Ставка должна быть больше 0.")
                return

            await asyncio.to_thread(db.add_balance, interaction.user.id, -amount)

            random_chance = random.randint(40, 100)

            if random_chance <= 60:
                await interaction.followup.send(f"❌ Ты проиграл свои **{amount}**!")
            else:
                win_amount = amount * 2
                await asyncio.to_thread(db.add_balance, interaction.user.id, win_amount)
                await interaction.followup.send(f"🍷 Ты победил! Получаешь **{win_amount}**!")

        except asyncio.TimeoutError:
            await interaction.followup.send("`[⏰]` Время вышло.")



    @bot.tree.command(name="ban", description="Забанить пользователя")
    @app_commands.checks.has_permissions(ban_members=True)
    async def ban_user(
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = "Причина не указана"
    ):
        if interaction.guild is None:
            await interaction.response.send_message(
                "❌ Команда доступна только на сервере.",
                ephemeral=True
            )
            return

        if not await can_moderate(interaction, member):
            return

        try:
            case_id, created_at = create_mod_case(
                interaction.guild.id,
                "BAN",
                member.id,
                interaction.user.id,
                reason
            )

            await member.ban(
                reason=f"{reason} | Модератор: {interaction.user} | Case ID: {case_id}"
            )

            await interaction.response.send_message(
                f"✅ Пользователь **{member}** забанен.\n"
                f"Причина: **{reason}**\n"
                f"ID наказания: `{case_id}`"
            )

            await send_mod_log(
                interaction.guild,
                "BAN",
                interaction.user,
                member,
                reason,
                case_id,
                created_at
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Бот не может забанить этого пользователя.",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)

    @bot.tree.command(name="unban", description="Разбанить пользователя по ID")
    @app_commands.checks.has_permissions(ban_members=True)
    async def unban_user(
        interaction: discord.Interaction,
        user_id: str,
        reason: str = "Причина не указана"
    ):
        if interaction.guild is None:
            await interaction.response.send_message(
                "❌ Команда доступна только на сервере.",
                ephemeral=True
            )
            return

        try:
            user_id_int = int(user_id)
            user = await bot.fetch_user(user_id_int)

            case_id, created_at = create_mod_case(
                interaction.guild.id,
                "UNBAN",
                user.id,
                interaction.user.id,
                reason
            )

            await interaction.guild.unban(
                user,
                reason=f"{reason} | Модератор: {interaction.user} | Case ID: {case_id}"
            )

            await interaction.response.send_message(
                f"✅ Пользователь **{user}** разбанен.\n"
                f"Причина: **{reason}**\n"
                f"ID наказания: `{case_id}`"
            )

            await send_mod_log(
                interaction.guild,
                "UNBAN",
                interaction.user,
                user,
                reason,
                case_id,
                created_at
            )

        except ValueError:
            await interaction.response.send_message(
                "❌ ID пользователя должен быть числом.",
                ephemeral=True
            )
        except discord.NotFound:
            await interaction.response.send_message(
                "❌ Пользователь не найден в бан-листе.",
                ephemeral=True
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Бот не может разбанить пользователя.",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)

    @bot.tree.command(name="mute", description="Выдать мут пользователю")
    @app_commands.checks.has_permissions(manage_roles=True)
    async def mute_user(
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = "Причина не указана"
    ):
        if interaction.guild is None:
            await interaction.response.send_message(
                "❌ Команда доступна только на сервере.",
                ephemeral=True
            )
            return

        if not await can_moderate(interaction, member):
            return

        mute_role = interaction.guild.get_role(SI.MUTE_ROLE_ID)
        if mute_role is None:
            await interaction.response.send_message(
                "❌ MUTE_ROLE_ID указан неверно или роль не найдена.",
                ephemeral=True
            )
            return

        bot_member = interaction.guild.me
        if bot_member and mute_role >= bot_member.top_role:
            await interaction.response.send_message(
                "❌ Роль мута выше или равна роли бота.",
                ephemeral=True
            )
            return

        try:
            case_id, created_at = create_mod_case(
                interaction.guild.id,
                "MUTE",
                member.id,
                interaction.user.id,
                reason
            )

            await member.add_roles(
                mute_role,
                reason=f"{reason} | Модератор: {interaction.user} | Case ID: {case_id}"
            )

            await interaction.response.send_message(
                f"✅ Пользователь **{member}** получил мут.\n"
                f"Причина: **{reason}**\n"
                f"ID наказания: `{case_id}`"
            )

            await send_mod_log(
                interaction.guild,
                "MUTE",
                interaction.user,
                member,
                reason,
                case_id,
                created_at
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Бот не может выдать мут.",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)

    @bot.tree.command(name="unmute", description="Снять мут с пользователя")
    @app_commands.checks.has_permissions(manage_roles=True)
    async def unmute_user(
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = "Причина не указана"
    ):
        if interaction.guild is None:
            await interaction.response.send_message(
                "❌ Команда доступна только на сервере.",
                ephemeral=True
            )
            return

        mute_role = interaction.guild.get_role(SI.MUTE_ROLE_ID)
        if mute_role is None:
            await interaction.response.send_message(
                "❌ MUTE_ROLE_ID указан неверно или роль не найдена.",
                ephemeral=True
            )
            return

        try:
            case_id, created_at = create_mod_case(
                interaction.guild.id,
                "UNMUTE",
                member.id,
                interaction.user.id,
                reason
            )

            await member.remove_roles(
                mute_role,
                reason=f"{reason} | Модератор: {interaction.user} | Case ID: {case_id}"
            )

            await interaction.response.send_message(
                f"✅ С пользователя **{member}** снят мут.\n"
                f"Причина: **{reason}**\n"
                f"ID наказания: `{case_id}`"
            )

            await send_mod_log(
                interaction.guild,
                "UNMUTE",
                interaction.user,
                member,
                reason,
                case_id,
                created_at
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Бот не может снять мут.",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)

    @bot.tree.command(name="warn", description="Выдать предупреждение")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def warn_user(
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = "Причина не указана"
    ):
        if interaction.guild is None:
            await interaction.response.send_message(
                "❌ Команда доступна только на сервере.",
                ephemeral=True
            )
            return

        if not await can_moderate(interaction, member):
            return

        try:
            warn_id, created_at = add_warning_db(
                interaction.guild.id,
                member.id,
                interaction.user.id,
                reason
            )

            case_id, _ = create_mod_case(
                interaction.guild.id,
                "WARN",
                member.id,
                interaction.user.id,
                reason
            )

            warnings_count = len(get_user_warnings(interaction.guild.id, member.id))

            await interaction.response.send_message(
                f"✅ Пользователь **{member}** получил предупреждение.\n"
                f"Причина: **{reason}**\n"
                f"Всего предупреждений: **{warnings_count}**\n"
                f"ID наказания: `{case_id}`\n"
                f"ID предупреждения: `{warn_id}`"
            )

            await send_mod_log(
                interaction.guild,
                "WARN",
                interaction.user,
                member,
                reason,
                case_id,
                created_at
            )

        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)


    @bot.tree.command(name="warnings", description="Посмотреть предупреждения пользователя")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def warnings_user(
        interaction: discord.Interaction,
        member: discord.Member
    ):
        if interaction.guild is None:
            await interaction.response.send_message(
                "❌ Команда доступна только на сервере.",
                ephemeral=True
            )
            return

        warns = get_user_warnings(interaction.guild.id, member.id)

        if not warns:
            await interaction.response.send_message(
                f"У пользователя **{member}** нет предупреждений.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title=f"Предупреждения | {member}",
            color=discord.Color.gold()
        )

        for warn_id, moderator_id, reason, created_at in warns[:10]:
            embed.add_field(
                name=f"Warn ID: {warn_id}",
                value=(
                    f"**Модератор ID:** `{moderator_id}`\n"
                    f"**Причина:** {reason}\n"
                    f"**Дата:** {created_at}"
                ),
                inline=False
            )

        embed.set_footer(text=f"Всего предупреждений: {len(warns)}")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @bot.tree.command(name="timeout", description="Выдать таймаут пользователю")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def timeout_user(
        interaction: discord.Interaction,
        member: discord.Member,
        minutes: app_commands.Range[int, 1, 40320],
        reason: str = "Причина не указана"
    ):
        if interaction.guild is None:
            await interaction.response.send_message(
                "❌ Команда доступна только на сервере.",
                ephemeral=True
            )
            return

        if not await can_moderate(interaction, member):
            return

        try:
            until = discord.utils.utcnow() + timedelta(minutes=minutes)
            duration_text = f"{minutes} мин."

            case_id, created_at = create_mod_case(
                interaction.guild.id,
                "TIMEOUT",
                member.id,
                interaction.user.id,
                reason,
                duration_text
            )

            await member.timeout(
                until,
                reason=f"{reason} | Модератор: {interaction.user} | Case ID: {case_id}"
            )

            await interaction.response.send_message(
                f"✅ Пользователь **{member}** получил таймаут на **{minutes} мин.**\n"
                f"Причина: **{reason}**\n"
                f"ID наказания: `{case_id}`"
            )

            await send_mod_log(
                interaction.guild,
                "TIMEOUT",
                interaction.user,
                member,
                reason,
                case_id,
                created_at,
                duration_text
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Бот не может выдать таймаут.",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)

    @ban_user.error
    @unban_user.error
    @mute_user.error
    @unmute_user.error
    @warn_user.error
    @warnings_user.error
    @timeout_user.error
    async def mod_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            text = "❌ У вас недостаточно прав для этой команды."
        else:
            text = f"❌ Ошибка команды: {error}"

        if interaction.response.is_done():
            await interaction.followup.send(text, ephemeral=True)
        else:
            await interaction.response.send_message(text, ephemeral=True)