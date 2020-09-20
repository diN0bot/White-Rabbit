# Built-in
import asyncio
import random
import time
from pathlib import Path
import typing
# 3rd-party
import discord
from discord.ext import commands, tasks
# Local
import gamedata
import manual

class Game(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_command_error(self, ctx, error):
        if isinstance(error, discord.ext.commands.UserInputError):
            await ctx.send("Invalid input")
        else:
            await ctx.send("There was an error")
        print(error)

    @commands.Cog.listener()
    async def on_ready(self):
        self.timer.start()

    @commands.command()
    async def setup(self, ctx):
        """Sends out cards and sets up the game"""
        def send_image(channel, filepath):
            if isinstance(channel, str):
                channel = ctx.text_channels[channel]
            asyncio.create_task(channel.send(
                file=discord.File(filepath)
            ))

        def send_folder(channel, path):
            for image in sorted(path.glob("*")):
                send_image(channel, image)

        if ctx.game.started:
            await ctx.send("Game has already begun!")
            return
        elif ctx.game.setup:
            await ctx.send("Setup already run!")
            return

        await ctx.send("Starting setup")

        # Introduction images
        send_image("player-resources", gamedata.RESOURCE_DIR / 
                    "Alice is Missing - Guide.jpg")
        send_image("player-resources", gamedata.RESOURCE_DIR / 
                    "Alice is Missing - Character Sheet.jpg")
        send_image("player-resources", gamedata.CARD_DIR / "Misc" / "Introduction.png")
        alice = random.choice(list(Path(
                            "Images/Missing Person Posters").glob("*.png")))
        send_image("player-resources", alice)

        # Send characters, suspects, and locations to appropriate channels
        send_folder("character-cards", gamedata.CHARACTER_IMAGE_DIR)
        send_folder("suspect-cards", gamedata.SUSPECT_IMAGE_DIR)
        send_folder("location-cards", gamedata.LOCATION_IMAGE_DIR)

        # Character and motive cards in clues channels
        for first_name, full_name in gamedata.CHARACTERS.items():
            channel = ctx.text_channels[f"{first_name}-clues"]
            send_image(channel, gamedata.CHARACTER_IMAGE_DIR / f"{full_name}.png")
            if ctx.game.automatic:
                send_image(
                    channel,
                    gamedata.CARD_DIR / "Motives" / f"Motive {ctx.game.motives[first_name]}.png"
                )

        channel = ctx.text_channels["charlie-clues"]
        prompts = "\n".join([
            "Read introduction", "Introduce alice from poster",
            "Introduce/pick characters", "Explain character cards",
            "Explain drive cards", "Character introductions (relationships)",
            "Voicemails", "Suspects and locations", "Explain clue cards",
            "Explain searching", "game guide",
            "setup playlist https://www.youtube.com/watch?v=ysOOFIOAy7A",
            "Run !start", "90 min card",
        ])
        asyncio.create_task(channel.send(f"```{prompts}```"))

        ctx.game.setup = True

    @commands.command()
    async def start(self, ctx):
        """Begins the game"""

        if not ctx.game.setup:
            await ctx.send("Can't start before setting up!")
            return

        if ctx.game.started:
            await ctx.send("Game has already begun!")
            return

        if len(ctx.game.char_roles()) < 3:
            await ctx.send("Not enough players!")
            return

        # 90 minute card for Charlie Barnes
        channel = ctx.text_channels["charlie-clues"]
        asyncio.create_task(channel.send(file=discord.File(
            "Images/Cards/Clues/90/90-1.png"
        )))
        first_message = "Hey! Sorry for the big group text, but I just got "\
                        "into town for winter break at my dad's and haven't "\
                        "been able to get ahold of Alice. Just wondering if "\
                        "any of you have spoken to her?"
        asyncio.create_task(channel.send(first_message))

        ctx.game.start_time = time.time()
        ctx.game.started = True
        await ctx.send("Starting the game!")

    @commands.command(name="timer")
    async def show_time(self, ctx):
        """Show/hide bot timer"""

        ctx.game.show_timer = not ctx.game.show_timer
        if ctx.game.show_timer:
            await ctx.send("Showing bot timer!")
        else:
            await ctx.send("Hiding bot timer!")

    @commands.command()
    async def automatic(self, ctx):
        """Enable/disable automatic mode"""

        ctx.game.automatic = not ctx.game.automatic
        await ctx.send(f"{'En' if ctx.game.automatic else 'Dis'}abling automatic card draw")

    @tasks.loop(seconds=gamedata.TIMER_GAP)
    async def timer(self):
        for game in self.bot.games.values():
            # Skip if game has not started
            if not game.started:
                continue
            # Skip if game has ended
            if game.start_time + gamedata.GAME_LENGTH < time.time():
                continue

            remaining_time = (
                game.start_time + gamedata.GAME_LENGTH - time.time()
            )

            if game.show_timer:
                text_channels = {
                    channel.name: channel
                    for channel in game.guild.text_channels
                }
                await text_channels["bot-channel"].send((
                    f"{str(int(remaining_time // 60)).zfill(2)}:{str(int(remaining_time % 60)).zfill(2)}"
                ))

    @commands.command()
    async def search(self, ctx):
        """Draw a searching card"""
        
        if not ctx.game.started:
            await ctx.send("The game hasn't started yet")
        character = self.get_char(ctx.author)
        if not character:
            await ctx.send("You don't have a character role")
            return

        search_card = random.choice((gamedata.CARD_DIR / "Searching").glob("*.png"))
        asyncio.create_task(ctx.text_channels[f"{character}-clues"].send(
            file=discord.File(search_card)
        ))

    @commands.command(name="10")
    async def ten_min_card(self, ctx, 
                    character: typing.Union[discord.Member, discord.Role]):
        """Assign the 10 minute card to another player"""
        
        if isinstance(character, discord.Member):
            character = self.get_char(character)
            if not character:
                await ctx.send("Could not find player!")
        ctx.game.ten_char = character.name.lower()
        # await ctx.text_channels[f"{character.name.lower()}-clues"].send(
        #     file=discord.File(random.choice(list((gamedata.CLUE_DIR / "10").glob("10-*.png")))
        # ))


def setup(bot):
    bot.add_cog(Game(bot))
