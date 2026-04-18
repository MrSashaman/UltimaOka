import discord
from discord.ext import commands

import SI
from database import Database, init_mod_db
from commands import setup_commands
from services import setup_status_tasks


intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)
db = Database()


@bot.event
async def on_ready():
    init_mod_db()

    setup_status_tasks(bot)

    try:
        synced = await bot.tree.sync()
        print(f"Logged in as {bot.user}")
        print(f"Synced {len(synced)} commands")
    except Exception as e:
        print(f"Sync error: {e}")


def main():
    setup_commands(bot, db)
    bot.run(SI.TOKEN)


if __name__ == "__main__":
    main()