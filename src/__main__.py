import asyncio

import discord
from discord.ext import commands

import gamedata
import utils

bot = commands.Bot(command_prefix="!")
bot.games = {}


@bot.event
async def on_ready():
    # Set custom status
    await bot.change_presence(activity=discord.Game("Alice is Missing"))


@bot.check
def check_channel(ctx):
    """Only allow commands in #bot-channel"""
    return ctx.channel.name == "bot-channel"


@bot.check
def not_spectator(ctx):
    """Don't let spectators run commands"""
    return "spectator" not in [role.name.lower() for role in ctx.author.roles]


@bot.before_invoke
async def before_invoke(ctx):
    """Attaches stuff to ctx for convenience"""
    # that guild's game
    ctx.game = bot.games.setdefault(ctx.guild.id, gamedata.Data(ctx.guild))

    # access text channels by name
    ctx.text_channels = {
        channel.name: channel
        for channel in ctx.guild.text_channels
    }

    # Character that the author is
    ctx.character = None
    for role in ctx.author.roles:
        if role.name.lower() in gamedata.CHARACTERS:
            ctx.character = role.name.lower()


@bot.event
async def on_command_error(ctx, error):
    """Default error catcher"""
    bot_channel = utils.get_text_channels(ctx.guild)["bot-channel"]

    # bad input
    if isinstance(error, commands.errors.UserInputError):
        asyncio.create_task(ctx.send("Can't understand input!"))

    # cant find command
    elif isinstance(error, commands.errors.CommandNotFound):
        asyncio.create_task(ctx.send("Command not found!"))

    # failed a check
    elif isinstance(error, commands.errors.CheckFailure):
        if ctx.channel.name != "bot-channel":
            asyncio.create_task(ctx.send(f"You can only use commands in {bot_channel.mention}"))
            return

        if ctx.game.automatic:
            asyncio.create_task(ctx.send("Can't do that, are you running a manual command in automatic mode?"))
            return
        asyncio.create_task(ctx.send("You can't do that!"))

    # other stuff
    else:
        asyncio.create_task(ctx.send("Unknown error: check console!"))
        raise error

# Load all extensions
PLUGINS = ["admin", "debug", "export", "game", "manual", "players", "settings"]
for plugin in PLUGINS:
    bot.load_extension(plugin)

# Import bot token
with open(utils.WHITE_RABBIT_DIR / "token.txt") as token_file:
    token = token_file.read()
bot.run(token)
