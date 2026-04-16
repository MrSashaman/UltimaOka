import discord
from discord.ext import commands
from discord import ui

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

ADMIN_ACCESS_ROLE_ID = 1494183239110361119
VERIFIED_ADMIN_ROLE_ID = 1494182462538911774
BLACKLIST_ROLE_ID = 1494187832468836434
ADMIN_PASSWORD = "root"

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
                await interaction.response.send_message(f"✅**Пароль принят**. Роль защиты выдана: `{member}`!", ephemeral=True)
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
            LOG_CHANNEL_ID = 1494191515583381536  
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


@bot.tree.command(name="ping", description="Check ping")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"Pong: `{round(bot.latency * 1000)}ms`")


@bot.tree.command(name="adminsecurity", description="Подтверждение админ-прав")
async def adminsecurity(interaction: discord.Interaction):
    if not interaction.guild or not isinstance(interaction.user, discord.Member):
        await interaction.response.send_message("❌ `Команда доступна только на сервере.`", ephemeral=True)
        return

    has_access_role = any(role.id == ADMIN_ACCESS_ROLE_ID for role in interaction.user.roles)

    if not has_access_role:
        await interaction.response.send_message("❌ `У вас нет доступа к этой команде.`", ephemeral=True)
        return

    await interaction.response.send_modal(AdminAuthModal())

