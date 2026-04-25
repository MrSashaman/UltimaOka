import asyncio
import random
from datetime import timedelta
from discord import app_commands, ui
import SI
import discord
from discord import app_commands
from role_shop import (
    init_role_shop,
    add_role_to_shop,
    remove_role_from_shop,
    remove_shop_listing,
    get_shop_listing,
    get_shop_role,
    list_shop_roles,
    add_role_to_user,
    remove_role_from_user,
    user_has_role,
    list_user_roles,
)

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

botversion = "0.2.1"

init_role_shop()
def setup_commands(bot, db):


    @bot.event
    async def on_message(message):
        if message.author.bot:
            return
        if bot.user.mentioned_in(message):
            await message.channel.send(f'# 👋Привет, {message.author.mention}! Я мультифункциональный дискорд бот.\n'
                                       f'{message.author.mention}, Если нужна помощь по командам пропиши /help')

        if message.guild is None:
            await bot.process_commands(message)
            return

        forbidden_words = ["хуй", "пизда", "член", "dick", "трахать", "трахнул", "fuck", "пидор", "pidor", "еблан"]

        msg_content = message.content.lower()
        matched_word = next((word for word in forbidden_words if word in msg_content), None)

        if matched_word:
            reason = "Запрещённые слова"

            try:
                await message.delete()
            except (discord.Forbidden, discord.NotFound):
                pass

            warn_id, created_at = await asyncio.to_thread(
                add_warning_db,
                message.guild.id,
                message.author.id,
                bot.user.id,
                reason
            )
            case_id, _ = await asyncio.to_thread(
                create_mod_case,
                message.guild.id,
                "WARN",
                message.author.id,
                bot.user.id,
                reason
            )

            await message.channel.send(
                f"{message.author.mention}, сообщение удалено из-за запрещённых слов. "
                f"Выдано предупреждение `#{warn_id}`.",
                delete_after=10
            )

            await send_mod_log(
                message.guild,
                "WARN",
                bot.user,
                message.author,
                reason,
                case_id,
                created_at
            )
            return

        await bot.process_commands(message)

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

    @bot.tree.command(name="help", description="Посмотреть команды")
    async def help(interaction: discord.Interaction):
        help_categories = {
            "economy": {
                "label": "Экономика",
                "emoji": "💶",
                "color": discord.Color.gold(),
                "commands": [
                    ("💳 /balance", "Посмотреть свой или чужой баланс."),
                    ("🪙 /bonus", "Получить бонус раз в час."),
                    ("👷 /work", "Выбрать работу и попытаться получить зарплату."),
                    ("🎲 /luckybet", "Сделать ставку."),
                    ("🛒 /roleshop view", "Открыть магазин ролей сервера."),
                    ("🎒 /roleshop inventory", "Открыть инвентарь купленных ролей."),
                ]
            },
            "admin": {
                "label": "Админские",
                "emoji": "🛡️",
                "color": discord.Color.red(),
                "commands": [
                    ("🛡️ /ban", "Забанить пользователя."),
                    ("🔓 /unban", "Разбанить пользователя по ID."),
                    ("🔇 /mute", "Выдать мут пользователю."),
                    ("🔊 /unmute", "Снять мут с пользователя."),
                    ("⚠️ /warn", "Выдать предупреждение."),
                    ("📋 /warnings", "Посмотреть предупреждения пользователя."),
                    ("⏳ /timeout", "Выдать таймаут пользователю."),
                    ("🛒 /roleshop add", "Добавить роль в магазин сервера."),
                    ("🗑️ /roleshop remove", "Убрать роль из магазина сервера."),
                    ("🧪 /debug_info", "Показать debug-информацию сервера."),
                ]
            },
            "fun": {
                "label": "Фан",
                "emoji": "🎉",
                "color": discord.Color.purple(),
                "commands": [
                    ("🎬 /gif", "Случайная гифка."),
                    ("🎲 /roll", "Случайное число."),
                    ("🗾 /randomfact", "Случайный факт."),
                    ("🤫 /mrsashaman", "Секретная команда."),
                ]
            },
            "other": {
                "label": "Прочее",
                "emoji": "📦",
                "color": discord.Color.blurple(),
                "commands": [
                    ("💻 /ping", "Проверить задержку бота."),
                    ("🖼️ /getuseravatar", "Получить аватар пользователя."),
                    ("📦 /adminsecurity", "Подтвердить админ-права."),
                    ("📘 /profile view", "Посмотреть профиль."),
                    ("✏️ /profile edit", "Редактировать профиль."),
                    ("⚙️ /setcustomstatus", "Установить кастомный статус бота."),
                ]
            },
        }

        def build_help_embed(category_id: str) -> discord.Embed:
            category = help_categories[category_id]
            embed = discord.Embed(
                title=f"{category['emoji']} {category['label']}",
                description="Выбери раздел в списке ниже.",
                color=category["color"]
            )
            for command_name, description in category["commands"]:
                embed.add_field(name=command_name, value=description, inline=False)
            embed.set_footer(text=f"Поддержка: mrsashaman | Версия бота: {botversion}")
            return embed

        class HelpCategorySelect(ui.Select):
            def __init__(self):
                options = [
                    discord.SelectOption(
                        label=category["label"],
                        value=category_id,
                        emoji=category["emoji"]
                    )
                    for category_id, category in help_categories.items()
                ]
                super().__init__(
                    placeholder="Выбери раздел команд",
                    min_values=1,
                    max_values=1,
                    options=options
                )

            async def callback(self, select_interaction: discord.Interaction):
                await select_interaction.response.edit_message(
                    embed=build_help_embed(self.values[0]),
                    view=self.view
                )

        class HelpView(ui.View):
            def __init__(self, author_id: int):
                super().__init__(timeout=180)
                self.author_id = author_id
                self.add_item(HelpCategorySelect())

            async def interaction_check(self, select_interaction: discord.Interaction):
                if select_interaction.user.id != self.author_id:
                    await select_interaction.response.send_message(
                        "Это меню доступно только тому, кто вызвал /help.",
                        ephemeral=True
                    )
                    return False
                return True

        await interaction.response.send_message(
            embed=build_help_embed("economy"),
            view=HelpView(interaction.user.id),
            ephemeral=True
        )

    @bot.tree.command(name="mrsashaman", description="mrsashaman?")
    async def mrsashaman(interaction: discord.Interaction):
        present = random.randint(0, 90)                       
        user_id = interaction.user.id

        await asyncio.to_thread(db.ensure_user, user_id)
        await asyncio.to_thread(db.add_balance, user_id, present)

        if present <= 90:
            await interaction.response.send_message(f"`☹️Упс, mrSashaman не захотел давать тебе денег!`")
        else:
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



    def can_bot_manage_role(guild: discord.Guild, role: discord.Role) -> tuple[bool, str]:
        bot_member = guild.me or guild.get_member(bot.user.id)
        if role == guild.default_role:
            return False, "Нельзя продавать роль @everyone."
        if role.managed:
            return False, "Этой ролью управляет интеграция Discord."
        if bot_member and role >= bot_member.top_role:
            return False, "Роль должна быть ниже роли бота в списке ролей сервера."
        return True, ""

    def build_shop_embed(guild: discord.Guild, rows: list[tuple[int, int, int, int]]) -> discord.Embed:
        embed = discord.Embed(
            title="Магазин ролей",
            description="Выбери роль в меню ниже, чтобы купить её.",
            color=discord.Color.green()
        )
        if not rows:
            embed.description = "Магазин ролей пока пустой."
            return embed

        for _listing_id, role_id, price, seller_id in rows[:25]:
            role = guild.get_role(role_id)
            if not role:
                continue
            seller = "Сервер"
            if seller_id:
                member = guild.get_member(seller_id)
                seller = member.display_name if member else f"<@{seller_id}>"
            embed.add_field(
                name=f"{role.name} - {price}₵",
                value=f"Продавец: {seller}",
                inline=False
            )
        if not embed.fields:
            embed.description = "Магазин ролей пока пустой."
        return embed

    def build_inventory_embed(member: discord.Member, roles: list[discord.Role]) -> discord.Embed:
        embed = discord.Embed(
            title="Инвентарь ролей",
            description="Выбери роль в меню ниже, чтобы экипировать, убрать или продать её.",
            color=discord.Color.blurple()
        )
        if not roles:
            embed.description = "В инвентаре пока нет купленных ролей."
            return embed

        for role in roles[:25]:
            equipped = "экипирована" if role in member.roles else "убрана"
            embed.add_field(name=role.name, value=equipped, inline=False)
        return embed

    class SellRoleModal(ui.Modal, title="Продать роль"):
        price = ui.TextInput(
            label="Цена роли",
            placeholder="Введите цену в ₵",
            required=True,
            max_length=8
        )

        def __init__(self, role: discord.Role, guild_id: int, user: discord.Member):
            super().__init__()
            self.role = role
            self.guild_id = guild_id
            self.user = user

        async def on_submit(self, interaction: discord.Interaction):
            if not self.price.value.isdigit():
                await interaction.response.send_message("Введите цену числом.", ephemeral=True)
                return

            price = int(self.price.value)
            if price <= 0:
                await interaction.response.send_message("Цена должна быть больше нуля.", ephemeral=True)
                return

            existing_listing = await get_shop_role(self.guild_id, self.role.id, self.user.id)
            if existing_listing:
                await interaction.response.send_message("Ты уже выставил эту роль в магазин.", ephemeral=True)
                return

            try:
                if self.role in self.user.roles:
                    await self.user.remove_roles(self.role, reason="Role shop sale")
            except discord.Forbidden:
                await interaction.response.send_message("Не могу снять эту роль. Проверь права и иерархию ролей.", ephemeral=True)
                return

            await remove_role_from_user(self.user.id, self.role.id, self.guild_id)
            await add_role_to_shop(self.guild_id, self.role.id, price, self.user.id)
            await interaction.response.send_message(
                f"Роль **{self.role.name}** выставлена на продажу за {price}₵.",
                ephemeral=True
            )

    class RoleShopSelect(ui.Select):
        def __init__(self, guild: discord.Guild, rows: list[tuple[int, int, int, int]]):
            options = []
            for listing_id, role_id, price, seller_id in rows[:25]:
                role = guild.get_role(role_id)
                if not role:
                    continue
                seller = "Сервер" if not seller_id else f"Продавец: {seller_id}"
                options.append(discord.SelectOption(
                    label=role.name[:100],
                    value=str(listing_id),
                    description=f"{price}₵ | {seller}"[:100]
                ))
            super().__init__(placeholder="Выбери роль для покупки", options=options)

        async def callback(self, interaction: discord.Interaction):
            guild = interaction.guild
            if guild is None or not isinstance(interaction.user, discord.Member):
                await interaction.response.send_message("Команда доступна только на сервере.", ephemeral=True)
                return

            listing_id = int(self.values[0])
            listing = await get_shop_listing(listing_id)
            if not listing:
                await interaction.response.send_message("Эта роль уже не продаётся.", ephemeral=True)
                return

            _, listing_guild_id, role_id, price, seller_id = listing
            if listing_guild_id != guild.id:
                await interaction.response.send_message("Это объявление относится к другому серверу.", ephemeral=True)
                return

            role = guild.get_role(role_id)
            if not role:
                await remove_shop_listing(listing_id)
                await interaction.response.send_message("Роль не найдена и удалена из магазина.", ephemeral=True)
                return

            allowed, reason = can_bot_manage_role(guild, role)
            if not allowed:
                await interaction.response.send_message(reason, ephemeral=True)
                return

            if seller_id == interaction.user.id:
                await interaction.response.send_message("Нельзя купить свою же роль.", ephemeral=True)
                return

            if await user_has_role(interaction.user.id, role_id, guild.id):
                await interaction.response.send_message("Эта роль уже есть в твоём инвентаре.", ephemeral=True)
                return

            balance = await asyncio.to_thread(db.get_balance, interaction.user.id)
            if balance < price:
                await interaction.response.send_message(f"Недостаточно денег. Баланс: {balance}₵.", ephemeral=True)
                return

            try:
                await interaction.user.add_roles(role, reason="Role shop purchase")
            except discord.Forbidden:
                await interaction.response.send_message("Не могу выдать эту роль. Проверь права и иерархию ролей.", ephemeral=True)
                return

            await asyncio.to_thread(db.add_balance, interaction.user.id, -price)
            if seller_id:
                await asyncio.to_thread(db.add_balance, seller_id, price)
                await remove_shop_listing(listing_id)
            await add_role_to_user(interaction.user.id, role_id, guild.id)

            seller_text = f" Деньги получил <@{seller_id}>." if seller_id else ""
            await interaction.response.send_message(
                f"Куплена роль **{role.name}** за {price}₵.{seller_text}",
                ephemeral=True
            )

    class RoleShopView(ui.View):
        def __init__(self, guild: discord.Guild, user: discord.Member, rows: list[tuple[int, int, int, int]]):
            super().__init__(timeout=180)
            self.user = user
            valid_rows = [row for row in rows if guild.get_role(row[1])]
            if valid_rows:
                self.add_item(RoleShopSelect(guild, valid_rows))

        async def interaction_check(self, interaction: discord.Interaction):
            if interaction.user.id != self.user.id:
                await interaction.response.send_message("Эта панель доступна только тебе.", ephemeral=True)
                return False
            return True

    class InventoryRoleSelect(ui.Select):
        def __init__(self, roles: list[discord.Role]):
            options = [
                discord.SelectOption(label=role.name[:100], value=str(role.id))
                for role in roles[:25]
            ]
            super().__init__(placeholder="Выбери роль из инвентаря", options=options)

        async def callback(self, interaction: discord.Interaction):
            view: InventoryView = self.view
            view.selected_role_id = int(self.values[0])
            for item in view.children:
                if isinstance(item, ui.Button):
                    item.disabled = False
            await interaction.response.edit_message(view=view)

    class InventoryView(ui.View):
        def __init__(self, guild: discord.Guild, user: discord.Member, roles: list[discord.Role]):
            super().__init__(timeout=180)
            self.guild = guild
            self.user = user
            self.selected_role_id: int | None = None
            if roles:
                self.add_item(InventoryRoleSelect(roles))

        async def interaction_check(self, interaction: discord.Interaction):
            if interaction.user.id != self.user.id:
                await interaction.response.send_message("Этот инвентарь доступен только тебе.", ephemeral=True)
                return False
            return True

        def selected_role(self) -> discord.Role | None:
            if self.selected_role_id is None:
                return None
            return self.guild.get_role(self.selected_role_id)

        @ui.button(label="Экипировать", style=discord.ButtonStyle.success, disabled=True)
        async def equip_role(self, interaction: discord.Interaction, button: ui.Button):
            role = self.selected_role()
            if not role:
                await interaction.response.send_message("Роль не найдена.", ephemeral=True)
                return
            try:
                await self.user.add_roles(role, reason="Role shop inventory equip")
            except discord.Forbidden:
                await interaction.response.send_message("Не могу выдать эту роль. Проверь права и иерархию ролей.", ephemeral=True)
                return
            await interaction.response.send_message(f"Роль **{role.name}** экипирована.", ephemeral=True)

        @ui.button(label="Убрать", style=discord.ButtonStyle.secondary, disabled=True)
        async def unequip_role(self, interaction: discord.Interaction, button: ui.Button):
            role = self.selected_role()
            if not role:
                await interaction.response.send_message("Роль не найдена.", ephemeral=True)
                return
            try:
                if role in self.user.roles:
                    await self.user.remove_roles(role, reason="Role shop inventory unequip")
            except discord.Forbidden:
                await interaction.response.send_message("Не могу снять эту роль. Проверь права и иерархию ролей.", ephemeral=True)
                return
            await interaction.response.send_message(f"Роль **{role.name}** убрана.", ephemeral=True)

        @ui.button(label="Продать", style=discord.ButtonStyle.danger, disabled=True)
        async def sell_role(self, interaction: discord.Interaction, button: ui.Button):
            role = self.selected_role()
            if not role:
                await interaction.response.send_message("Роль не найдена.", ephemeral=True)
                return
            await interaction.response.send_modal(SellRoleModal(role, self.guild.id, self.user))

    roleshop_group = app_commands.Group(name="roleshop", description="Магазин ролей")

    @roleshop_group.command(name="view", description="Открыть магазин ролей")
    async def roleshop_view(interaction: discord.Interaction):
        if interaction.guild is None or not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message("Команда доступна только на сервере.", ephemeral=True)
            return

        rows = await list_shop_roles(interaction.guild.id)
        embed = build_shop_embed(interaction.guild, rows)
        view = RoleShopView(interaction.guild, interaction.user, rows)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @roleshop_group.command(name="inventory", description="Открыть инвентарь купленных ролей")
    async def roleshop_inventory(interaction: discord.Interaction):
        if interaction.guild is None or not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message("Команда доступна только на сервере.", ephemeral=True)
            return

        role_ids = await list_user_roles(interaction.user.id, interaction.guild.id)
        roles = [role for role_id in role_ids if (role := interaction.guild.get_role(role_id))]
        embed = build_inventory_embed(interaction.user, roles)
        view = InventoryView(interaction.guild, interaction.user, roles)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @roleshop_group.command(name="add", description="Добавить роль в магазин сервера")
    @app_commands.checks.has_permissions(administrator=True)
    async def roleshop_add(
        interaction: discord.Interaction,
        role: discord.Role,
        price: app_commands.Range[int, 1, 99999999]
    ):
        if interaction.guild is None:
            await interaction.response.send_message("Команда доступна только на сервере.", ephemeral=True)
            return

        allowed, reason = can_bot_manage_role(interaction.guild, role)
        if not allowed:
            await interaction.response.send_message(reason, ephemeral=True)
            return

        await add_role_to_shop(interaction.guild.id, role.id, price, 0)
        await interaction.response.send_message(
            f"Роль **{role.name}** добавлена в магазин за {price}₵.",
            ephemeral=True
        )

    @roleshop_group.command(name="remove", description="Убрать роль из магазина сервера")
    @app_commands.checks.has_permissions(administrator=True)
    async def roleshop_remove(interaction: discord.Interaction, role: discord.Role):
        if interaction.guild is None:
            await interaction.response.send_message("Команда доступна только на сервере.", ephemeral=True)
            return

        await remove_role_from_shop(interaction.guild.id, role.id)
        await interaction.response.send_message(f"Роль **{role.name}** убрана из магазина.", ephemeral=True)

    @roleshop_add.error
    @roleshop_remove.error
    async def roleshop_admin_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("Нужны права администратора.", ephemeral=True)
            return
        raise error

    bot.tree.add_command(roleshop_group)


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

    @bot.tree.command(name="work", description="Выбрать работу и попытаться получить зарплату")
    @app_commands.checks.cooldown(1, 3600)
    async def work(interaction: discord.Interaction):
        jobs = {
            "cook": {
                "name": "Повар",
                "emoji": "🍳",
                "salary": (60, 140),
                "success_chance": 90,
                "success": "Смена прошла спокойно, гости сыты, касса довольна.",
                "fail": "Заказов было слишком много, смена сорвалась."
            },
            "guard": {
                "name": "Охранник",
                "emoji": "🛡️",
                "salary": (80, 170),
                "success_chance": 82,
                "success": "Ты отстоял смену без происшествий.",
                "fail": "Ты уснул на посту, премию не дали."
            },
            "programmer": {
                "name": "Программист",
                "emoji": "💻",
                "salary": (120, 260),
                "success_chance": 72,
                "success": "Код собрался, заказчик оплатил работу.",
                "fail": "Баг оказался хитрее дедлайна, оплаты сегодня нет."
            },
            "firefighter": {
                "name": "Пожарный",
                "emoji": "🚒",
                "salary": (140, 300),
                "success_chance": 64,
                "success": "Вызов закрыт, город спасён, зарплата начислена.",
                "fail": "Смена была тяжёлой, но оплачиваемого вызова не досталось."
            },
            "stalker": {
                "name": "Сталкер",
                "emoji": "☢️",
                "salary": (220, 520),
                "success_chance": 42,
                "success": "Ты вернулся с редкой находкой и выгодно её продал.",
                "fail": "Добычи нет, зато есть история, которую лучше не рассказывать."
            },
            "cosmonaut": {
                "name": "Космонавт",
                "emoji": "🚀",
                "salary": (300, 700),
                "success_chance": 30,
                "success": "Миссия прошла успешно, гонорар внушительный.",
                "fail": "Запуск перенесли, выплаты тоже."
            },
            "europeanunionleader": {
                "name": "Глава ЕС",
                "emoji": "🌍",
                "salary": (1, 1000),
                "success_chance": 15,
                "success": "Ода к радости ведёт!",
                "fail": "Ода к радости ведёт!"
            },
            
        }

        def build_work_embed() -> discord.Embed:
            embed = discord.Embed(
                title="👷 Выбор работы",
                description="Выбери работу снизу. Чем выше награда, тем больше шанс ничего не получить.",
                color=discord.Color.orange()
            )
            for job in jobs.values():
                min_salary, max_salary = job["salary"]
                embed.add_field(
                    name=f"{job['emoji']} {job['name']}",
                    value=f"Зарплата: `{min_salary}-{max_salary}₵`\nШанс успеха: `{job['success_chance']}%`",
                    inline=True
                )
            return embed

        class WorkSelect(ui.Select):
            def __init__(self):
                options = []
                for job_id, job in jobs.items():
                    min_salary, max_salary = job["salary"]
                    options.append(discord.SelectOption(
                        label=job["name"],
                        value=job_id,
                        emoji=job["emoji"],
                        description=f"{min_salary}-{max_salary}₵ | шанс {job['success_chance']}%"
                    ))
                super().__init__(
                    placeholder="Выбери работу",
                    min_values=1,
                    max_values=1,
                    options=options
                )

            async def callback(self, select_interaction: discord.Interaction):
                view: WorkView = self.view
                if view.completed:
                    await select_interaction.response.send_message(
                        "Эта смена уже завершена.",
                        ephemeral=True
                    )
                    return

                view.completed = True
                job = jobs[self.values[0]]
                min_salary, max_salary = job["salary"]
                success = random.randint(1, 100) <= job["success_chance"]

                self.disabled = True
                if success:
                    salary = random.randint(min_salary, max_salary)
                    await asyncio.to_thread(db.add_balance, select_interaction.user.id, salary)
                    embed = discord.Embed(
                        title=f"{job['emoji']} Работа выполнена",
                        description=f"{job['success']}\n\nПолучено: `{salary}₵`",
                        color=discord.Color.green()
                    )
                else:
                    embed = discord.Embed(
                        title=f"{job['emoji']} Работа провалена",
                        description=f"{job['fail']}\n\nПолучено: `0₵`",
                        color=discord.Color.red()
                    )

                await select_interaction.response.edit_message(embed=embed, view=view)

        class WorkView(ui.View):
            def __init__(self, author_id: int):
                super().__init__(timeout=120)
                self.author_id = author_id
                self.completed = False
                self.add_item(WorkSelect())

            async def interaction_check(self, select_interaction: discord.Interaction):
                if select_interaction.user.id != self.author_id:
                    await select_interaction.response.send_message(
                        "Это меню работы доступно только тому, кто вызвал команду.",
                        ephemeral=True
                    )
                    return False
                return True

        await interaction.response.send_message(
            embed=build_work_embed(),
            view=WorkView(interaction.user.id),
            ephemeral=True
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
