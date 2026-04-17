import os
import random
import asyncio
import discord
from discord.ext import commands
from discord import ui, app_commands
from database import Database

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

ADMIN_ACCESS_ROLE_ID = 1494183239110361119
VERIFIED_ADMIN_ROLE_ID = 1494182462538911774
BLACKLIST_ROLE_ID = 1494187832468836434
LOG_CHANNEL_ID = 1494191515583381536
ADMIN_PASSWORD = "root"

db = Database()
bot = commands.Bot(command_prefix="!", intents=intents)


class AdminAuthModal(ui.Modal, title="Подтверждение админ-прав."):
    password_input = ui.TextInput(
        label="Введите пароль",
        placeholder="Пароль...",
        min_length=4,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message("❌ Команда доступна только на сервере.", ephemeral=True)
            return

        member = interaction.user
        guild = interaction.guild
        bot_member = guild.me

        verified_role = guild.get_role(VERIFIED_ADMIN_ROLE_ID)
        blacklist_role = guild.get_role(BLACKLIST_ROLE_ID)

        if self.password_input.value == ADMIN_PASSWORD:
            if verified_role is None:
                await interaction.response.send_message("❌ Роль верификации не найдена.", ephemeral=True)
                return

            if verified_role >= bot_member.top_role:
                await interaction.response.send_message("❌ Бот не может выдать роль верификации. Подними роль бота выше.", ephemeral=True)
                return

            try:
                await member.add_roles(verified_role, reason="Успешная admin security верификация")
                await interaction.response.send_message(f"✅ **Пароль принят**. Роль защиты выдана: `{member}`!", ephemeral=True)
            except discord.Forbidden:
                await interaction.response.send_message("❌ Бот не может выдать роль. Проверь права и иерархию ролей.", ephemeral=True)
            except Exception as e:
                await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)
            return

        removable_roles = [
            role for role in member.roles
            if role != guild.default_role
            and role != blacklist_role
            and role < bot_member.top_role
        ]

        try:
            if removable_roles:
                await member.remove_roles(*removable_roles, reason="Неверный пароль admin security")

            log_channel = guild.get_channel(LOG_CHANNEL_ID)

            if log_channel:
                embed = discord.Embed(
                    title="🚨 Нарушение безопасности",
                    description=f"Пользователь {member.mention} ввел **неверный пароль**.",
                    color=discord.Color.red()
                )
                embed.add_field(name="Действие", value="Сняты все доступные роли и выдан ЧС.")
                embed.set_footer(text=f"ID: {member.id}")
                await log_channel.send(embed=embed)

            if blacklist_role is None:
                await interaction.response.send_message("❌ ЧС-роль не найдена. Роли сняты, но ЧС-роль не выдана.", ephemeral=True)
                return

            if blacklist_role >= bot_member.top_role:
                await interaction.response.send_message("❌ Бот не может выдать ЧС-роль. Подними роль бота выше.", ephemeral=True)
                return

            await member.add_roles(blacklist_role, reason="Неверный пароль admin security")
            await interaction.response.send_message("❌ Неверный пароль. Роли сняты, выдана ЧС-роль.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ Бот не может управлять ролями. Проверь права и иерархию ролей.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)


@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"Logged in as {bot.user}")
        print(f"Synced {len(synced)} commands")
    except Exception as e:
        print(f"Sync error: {e}")


@bot.tree.command(name="getuseravatar", description="Получить аватар пользователя")
async def getavatar(interaction: discord.Interaction, member: discord.Member):
    embed = discord.Embed(title=f"Аватар {member.name}", color=discord.Color.blue())
    embed.set_image(url=member.display_avatar.url)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="luckybet", description="Сделать ставку")
async def luckybet(interaction: discord.Interaction):
    balance_value = await asyncio.to_thread(db.get_balance, interaction.user.id)
    
    await interaction.response.send_message(f"`[🎩]` Введите сумму ставки:")

    def check(m):
        return m.author == interaction.user and m.channel == interaction.channel

    try:
        msg = await bot.wait_for('message', check=check, timeout=30.0)
        
        if not msg.content.isdigit():
            return await interaction.followup.send("[🚫] Ошибка: введите числовое значение.")
        
        amount = int(msg.content)

        if amount > balance_value:
            return await interaction.followup.send("[🚫] Недостаточно денег.")
        
        if amount <= 0:
            return await interaction.followup.send("[🚫] Ставка должна быть больше 0.")

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

@bot.tree.command(name="ping", description="Check ping")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"Pong: `{round(bot.latency * 1000)}ms`")


@bot.tree.command(name="adminsecurity", description="Подтверждение админ-прав")
async def adminsecurity(interaction: discord.Interaction):
    if not interaction.guild or not isinstance(interaction.user, discord.Member):
        await interaction.response.send_message("❌ Команда доступна только на сервере.", ephemeral=True)
        return

    has_access_role = any(role.id == ADMIN_ACCESS_ROLE_ID for role in interaction.user.roles)

    if not has_access_role:
        await interaction.response.send_message("❌ У вас нет доступа к этой команде.", ephemeral=True)
        return

    await interaction.response.send_modal(AdminAuthModal())


@bot.tree.command(name="roll", description="Random Number!")
async def randomnum(interaction: discord.Interaction):
    rnum = random.randint(1, 90)
    await interaction.response.send_message(f"**Твоё рандомное число:** {rnum}")


@bot.tree.command(name="debug_info", description="DEBUG INFO ABOUT SERVER..")
@app_commands.checks.has_permissions(administrator=True)
async def debuginfo(interaction: discord.Interaction):
    guild = interaction.guild

    if guild is None:
        await interaction.response.send_message("❌ Команда доступна только на сервере.", ephemeral=True)
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
            await interaction.followup.send("❌ У вас недостаточно прав для этой команды!", ephemeral=True)
        else:
            await interaction.response.send_message("❌ У вас недостаточно прав для этой команды!", ephemeral=True)


@bot.tree.command(name="work", description="Выйти на работу и получить зарплату")
@app_commands.checks.cooldown(1, 3600)
async def work(interaction: discord.Interaction):
    salary = random.randint(50, 250)
    jobs = ["Поваром", "Пожарным", "Программистом", "Охранником", "Президентом", "Гражданином Чехословакии", "Главой Евро-Коммисии"]
    job = random.choice(jobs)

    await asyncio.to_thread(db.add_balance, interaction.user.id, salary)
    balance_value = await asyncio.to_thread(db.get_balance, interaction.user.id)

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
    user_balance = await asyncio.to_thread(db.get_balance, user_id)
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

bot.run("token")