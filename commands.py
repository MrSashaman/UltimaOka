import asyncio
import random
from datetime import timedelta
from discord import app_commands, ui
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


    @bot.tree.command(name="mrsashaman", description="mrsashaman?")
    async def mrsashaman(interaction: discord.Interaction):
        present = 1                       
        user_id = interaction.user.id

        await asyncio.to_thread(db.ensure_user, user_id)
        await asyncio.to_thread(db.add_balance, user_id, present)
  
        await interaction.response.send_message(f"🤫`Тсс, это секретная команда. Вот тебе подарок от меня:` 🎁*{present}₵*")

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

    LUCKYBET_WIN_CHANCE = 45 
    LUCKYBET_MULTIPLIER = 2 
    SPIN_GIF = "https://tenor.com/n6VvWbS02In.gif"
    WIN_GIF = "https://tenor.com/sgKHCPWX1eH.gif"
    LOSE_GIF = "https://media1.tenor.com/m/EmCutI9qdgYAAAAC/oh-damn-i%E2%80%99m-lost.gif"


    def format_money(amount: int) -> str:
        return f"{amount:,}".replace(",", " ")


    def build_spin_embed(user: discord.User, amount: int, reels: str, stage_text: str) -> discord.Embed:
        embed = discord.Embed(
            title="🎰 LuckyBet",
            description=(
                f"**Игрок:** {user.mention}\n"
                f"**Ставка:** `{format_money(amount)}`\n\n"
                f"## {reels}\n\n"
                f"**{stage_text}**"
            ),
            color=discord.Color.gold()
        )
        embed.set_footer(text="Удача решает всё...")
        if SPIN_GIF:
            embed.set_image(url=SPIN_GIF)
        return embed


    def build_result_embed(user: discord.User, amount: int, won: bool, payout: int = 0, balance: int = 0) -> discord.Embed:
        if won:
            embed = discord.Embed(
                title="🎉 Победа!",
                description=(
                    f"**Игрок:** {user.mention}\n"
                    f"**Ставка:** `{format_money(amount)}`\n"
                    f"**Выигрыш:** `{format_money(payout)}`\n"
                    f"**Новый баланс:** `{format_money(balance)}`\n\n"
                    f"🎰 Автомат остановился на выигрышной комбинации!"
                ),
                color=discord.Color.green()
            )
            if WIN_GIF:
                embed.set_image(url=WIN_GIF)
        else:
            embed = discord.Embed(
                title="💀 Проигрыш",
                description=(
                    f"**Игрок:** {user.mention}\n"
                    f"**Ставка:** `{format_money(amount)}`\n"
                    f"**Потеряно:** `{format_money(amount)}`\n"
                    f"**Новый баланс:** `{format_money(balance)}`\n\n"
                    f"🎰 На этот раз удача была не на твоей стороне."
                ),
                color=discord.Color.red()
            )
            if LOSE_GIF:
                embed.set_image(url=LOSE_GIF)

        embed.set_footer(text="Нажми кнопку ниже, чтобы сыграть ещё раз")
        return embed


    class LuckyBetRepeatView(discord.ui.View):
        def __init__(self, author_id: int):
            super().__init__(timeout=120)
            self.author_id = author_id

        async def interaction_check(self, interaction: discord.Interaction) -> bool:
            if interaction.user.id != self.author_id:
                await interaction.response.send_message(
                    "❌ Эта кнопка доступна только тому, кто сделал ставку.",
                    ephemeral=True
                )
                return False
            return True

        @discord.ui.button(label="Повторить ставку", emoji="🎲", style=discord.ButtonStyle.success)
        async def repeat_bet(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.send_modal(LuckyBetModal())

        async def on_timeout(self):
            for item in self.children:
                item.disabled = True


    class LuckyBetModal(ui.Modal, title="LuckyBet - ставка"):
        amount = ui.TextInput(
            label="Введите сумму ставки",
            placeholder="Например: 500",
            required=True,
            max_length=12
        )

        async def on_submit(self, interaction: discord.Interaction):
            if not self.amount.value.isdigit():
                await interaction.response.send_message(
                    "🚫 Ошибка: введите только числовую сумму.",
                    ephemeral=True
                )
                return

            amount = int(self.amount.value)

            if amount <= 0:
                await interaction.response.send_message(
                    "🚫 Ставка должна быть больше 0.",
                    ephemeral=True
                )
                return

            balance_value = await asyncio.to_thread(db.get_balance, interaction.user.id)

            if amount > balance_value:
                await interaction.response.send_message(
                    f"🚫 Недостаточно денег. Твой баланс: `{format_money(balance_value)}`",
                    ephemeral=True
                )
                return

            await asyncio.to_thread(db.add_balance, interaction.user.id, -amount)

            reels_frames = [
                "🍒 | 💎 | 7️⃣",
                "💎 | 🍒 | 🎲",
                "7️⃣ | 💰 | 🍒",
                "🍀 | 7️⃣ | 💎",
                "💰 | 🍒 | 7️⃣",
            ]

            await interaction.response.send_message(
                embed=build_spin_embed(
                    interaction.user,
                    amount,
                    random.choice(reels_frames),
                    "Барабаны начинают крутиться..."
                )
            )

            msg = await interaction.original_response()

            for stage_text in [
                "Прокрутка...",
                "Скорость растёт...",
                "Ещё немного...",
                "Останавливаем барабаны..."
            ]:
                await asyncio.sleep(0.9)
                await msg.edit(
                    embed=build_spin_embed(
                        interaction.user,
                        amount,
                        random.choice(reels_frames),
                        stage_text
                    )
                )

            await asyncio.sleep(0.8)

            won = random.randint(1, 100) <= LUCKYBET_WIN_CHANCE

            if won:
                payout = amount * LUCKYBET_MULTIPLIER
                await asyncio.to_thread(db.add_balance, interaction.user.id, payout)
                new_balance = await asyncio.to_thread(db.get_balance, interaction.user.id)

                await msg.edit(
                    embed=build_result_embed(
                        interaction.user,
                        amount,
                        won=True,
                        payout=payout,
                        balance=new_balance
                    ),
                    view=LuckyBetRepeatView(interaction.user.id)
                )
            else:
                new_balance = await asyncio.to_thread(db.get_balance, interaction.user.id)

                await msg.edit(
                    embed=build_result_embed(
                        interaction.user,
                        amount,
                        won=False,
                        balance=new_balance
                    ),
                    view=LuckyBetRepeatView(interaction.user.id)
                )


    @bot.tree.command(name="luckybet", description="Сделать ставку")
    async def luckybet(interaction: discord.Interaction):
        await interaction.response.send_modal(LuckyBetModal())

    @bot.tree.command(name="randomfact", description="Рандомный факт")
    async def randomfact(interaction: discord.Interaction):
        randomfactlist = [
            "В 1952 году Эйнштейну предлагали стать президентом Израиля.", 
            "Каждый пятый россиянин, по данным ВОЗ, умирает от алкоголя."
        ]
        rndfact = random.choice(randomfactlist)
        await interaction.response.send_message(f"{rndfact}")


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



#Профиль и прочая хрень


    profile_group = app_commands.Group(name="profile", description="Профиль пользователя")

    def build_profile_embed(member: discord.abc.User, profile: dict) -> discord.Embed:
        gender_map = {
            None: "Не указан",
            "male": "Мужской",
            "female": "Женский",
            "other": "Другое"
        }

        gender_text = gender_map.get(profile["gender"], "Не указан")
        age_text = str(profile["age"]) if profile["age"] is not None else "Не указан"
        about_text = profile["about"] if profile["about"] else "Не указано"
        events_text = "Включены" if profile["event_ping"] else "Выключены"

        embed = discord.Embed(
            title=f"Профиль {member.display_name}",
            color=discord.Color.blurple()
        )
        embed.add_field(name="Пол", value=gender_text, inline=True)
        embed.add_field(name="Возраст", value=age_text, inline=True)
        embed.add_field(name="Ивенты", value=events_text, inline=True)
        embed.add_field(name="О себе", value=about_text, inline=False)
        embed.add_field(name="Баланс", value=f"{profile['balance']}₵", inline=True)

        if hasattr(member, "display_avatar"):
            embed.set_thumbnail(url=member.display_avatar.url)

        return embed


    class ProfileAboutModal(ui.Modal, title="Изменить описание"):
        about = ui.TextInput(
            label="О себе",
            placeholder="Напиши немного о себе",
            style=discord.TextStyle.paragraph,
            required=False,
            max_length=300
        )

        async def on_submit(self, interaction: discord.Interaction):
            text = self.about.value.strip()

            if text == "":
                await asyncio.to_thread(db.clear_about, interaction.user.id)
                await interaction.response.send_message(
                    "✅ Описание профиля очищено.",
                    ephemeral=True
                )
                return

            await asyncio.to_thread(db.set_about, interaction.user.id, text)
            await interaction.response.send_message(
                "✅ Описание профиля обновлено.",
                ephemeral=True
            )


    class ProfileAgeModal(ui.Modal, title="Указать возраст"):
        age = ui.TextInput(
            label="Возраст",
            placeholder="Например: 16",
            required=True,
            max_length=2
        )

        async def on_submit(self, interaction: discord.Interaction):
            value = self.age.value.strip()

            if not value.isdigit():
                await interaction.response.send_message(
                    "❌ Возраст должен быть числом.",
                    ephemeral=True
                )
                return

            age = int(value)

            if age < 10 or age > 99:
                await interaction.response.send_message(
                    "❌ Возраст должен быть от 10 до 99.",
                    ephemeral=True
                )
                return

            await asyncio.to_thread(db.set_age, interaction.user.id, age)
            await interaction.response.send_message(
                f"✅ Возраст обновлён: **{age}**",
                ephemeral=True
            )


    class ProfileGenderSelect(ui.Select):
        def __init__(self):
            options = [
                discord.SelectOption(label="Мужской", value="male"),
                discord.SelectOption(label="Женский", value="female"),
                discord.SelectOption(label="Другое", value="other"),
                discord.SelectOption(label="Очистить", value="clear")
            ]
            super().__init__(
                placeholder="Выбери пол",
                min_values=1,
                max_values=1,
                options=options
            )

        async def callback(self, interaction: discord.Interaction):
            value = self.values[0]

            if value == "clear":
                await asyncio.to_thread(db.clear_gender, interaction.user.id)
                await interaction.response.send_message(
                    "✅ Пол в профиле очищен.",
                    ephemeral=True
                )
                return

            await asyncio.to_thread(db.set_gender, interaction.user.id, value)

            gender_names = {
                "male": "Мужской",
                "female": "Женский",
                "other": "Другое"
            }

            await interaction.response.send_message(
                f"✅ Пол обновлён: **{gender_names[value]}**",
                ephemeral=True
            )


    class ProfileGenderView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=120)
            self.add_item(ProfileGenderSelect())


    class ProfileEditView(discord.ui.View):
        def __init__(self, author_id: int):
            super().__init__(timeout=180)
            self.author_id = author_id

        async def interaction_check(self, interaction: discord.Interaction) -> bool:
            if interaction.user.id != self.author_id:
                await interaction.response.send_message(
                    "❌ Это меню доступно только автору команды.",
                    ephemeral=True
                )
                return False
            return True

        @discord.ui.button(label="Пол", style=discord.ButtonStyle.primary)
        async def set_gender_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.send_message(
                "Выбери пол:",
                view=ProfileGenderView(),
                ephemeral=True
            )

        @discord.ui.button(label="Возраст", style=discord.ButtonStyle.primary)
        async def set_age_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.send_modal(ProfileAgeModal())

        @discord.ui.button(label="О себе", style=discord.ButtonStyle.secondary)
        async def set_about_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.send_modal(ProfileAboutModal())

        @discord.ui.button(label="Ивенты", style=discord.ButtonStyle.success)
        async def toggle_events_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            profile = await asyncio.to_thread(db.get_profile, interaction.user.id)
            new_value = not bool(profile["event_ping"])

            await asyncio.to_thread(db.set_event_ping, interaction.user.id, new_value)

            text = "✅ Уведомления об ивентах включены." if new_value else "✅ Уведомления об ивентах выключены."
            await interaction.response.send_message(text, ephemeral=True)


    @profile_group.command(name="view", description="Посмотреть профиль")
    async def profile_view(interaction: discord.Interaction, member: discord.Member | None = None):
        target = member or interaction.user
        await asyncio.to_thread(db.ensure_user, target.id)
        profile = await asyncio.to_thread(db.get_profile, target.id)

        await interaction.response.send_message(
            embed=build_profile_embed(target, profile)
        )


    @profile_group.command(name="edit", description="Редактировать свой профиль")
    async def profile_edit(interaction: discord.Interaction):
        await asyncio.to_thread(db.ensure_user, interaction.user.id)

        await interaction.response.send_message(
            "Настрой свой профиль:",
            view=ProfileEditView(interaction.user.id),
            ephemeral=True
        )


    @profile_group.command(name="setgender", description="Установить пол")
    @app_commands.describe(gender="male, female, other")
    async def profile_set_gender(interaction: discord.Interaction, gender: str):
        value = gender.lower().strip()

        if value not in ("male", "female", "other"):
            await interaction.response.send_message(
                "❌ Доступные значения: `male`, `female`, `other`",
                ephemeral=True
            )
            return

        await asyncio.to_thread(db.set_gender, interaction.user.id, value)

        gender_names = {
            "male": "Мужской",
            "female": "Женский",
            "other": "Другое"
        }

        await interaction.response.send_message(
            f"✅ Пол обновлён: **{gender_names[value]}**",
            ephemeral=True
        )


    @profile_group.command(name="setage", description="Установить возраст")
    async def profile_set_age(interaction: discord.Interaction, age: app_commands.Range[int, 10, 99]):
        await asyncio.to_thread(db.set_age, interaction.user.id, age)
        await interaction.response.send_message(
            f"✅ Возраст обновлён: **{age}**",
            ephemeral=True
        )


    @profile_group.command(name="setabout", description="Установить описание")
    async def profile_set_about(interaction: discord.Interaction, text: app_commands.Range[str, 1, 300]):
        await asyncio.to_thread(db.set_about, interaction.user.id, text.strip())
        await interaction.response.send_message(
            "✅ Описание профиля обновлено.",
            ephemeral=True
        )


    @profile_group.command(name="events", description="Включить или выключить уведомления об ивентах")
    async def profile_events(interaction: discord.Interaction, enabled: bool):
        await asyncio.to_thread(db.set_event_ping, interaction.user.id, enabled)
        await interaction.response.send_message(
            "✅ Уведомления об ивентах включены." if enabled else "✅ Уведомления об ивентах выключены.",
            ephemeral=True
        )


    @profile_group.command(name="clearabout", description="Очистить описание")
    async def profile_clear_about(interaction: discord.Interaction):
        await asyncio.to_thread(db.clear_about, interaction.user.id)
        await interaction.response.send_message(
            "✅ Описание профиля очищено.",
            ephemeral=True
        )


    @profile_group.command(name="clearage", description="Очистить возраст")
    async def profile_clear_age(interaction: discord.Interaction):
        await asyncio.to_thread(db.clear_age, interaction.user.id)
        await interaction.response.send_message(
            "✅ Возраст очищен.",
            ephemeral=True
        )


    @profile_group.command(name="cleargender", description="Очистить пол")
    async def profile_clear_gender(interaction: discord.Interaction):
        await asyncio.to_thread(db.clear_gender, interaction.user.id)
        await interaction.response.send_message(
            "✅ Пол очищен.",
            ephemeral=True
        )


    bot.tree.add_command(profile_group)


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
