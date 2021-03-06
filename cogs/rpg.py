import asyncio
import os
import random
import re
from concurrent import futures
from typing import List, Sequence, Tuple

import discord
from discord.ext import commands
from discord.ext.commands import Cog

from bot import BeattieBot
from context import BContext
from utils.genesys import die_names, genesysroller

RollArg = Tuple[int, int, int, int, int, int]


class RPG(Cog):
    def __init__(self, bot: BeattieBot):
        self.loop = bot.loop
        self.tarot_url = "https://www.trustedtarot.com/cards/{}/"

    @commands.command()
    async def choose(self, ctx: BContext, *options: commands.clean_content) -> None:
        """Choose between some options. Use quotes if they have spaces."""
        choice = random.choice(options)
        await ctx.send(f"I choose:\n{choice}")

    @commands.command()
    async def tarot(self, ctx: BContext, *suits: str) -> None:
        """Get a random tarot card.

        You can specify the suits from which to pull, options are:
        minor:
            cups
            swords
            wands
            pentacles
        major"""
        async with ctx.typing():
            cards = []
            if not suits:
                suits = ("cups", "swords", "wands", "pentacles", "major")
            if "minor" in suits:
                suits = suits + ("cups", "swords", "wands", "pentacles")
            suit_set = set(suit.lower() for suit in suits)
            for root, dirs, files in os.walk("data/tarot"):
                if any(suit in root for suit in suit_set):
                    cards += [f"{root}/{card}" for card in files]
            try:
                card = random.choice(cards).replace("\\", "/")
            except IndexError:
                await ctx.send("Please specify a valid suit, or no suit.")
                return
            match = re.match(r"(?:\w+/)+[IVX0_]*([\w_]+)\.jpg", card)
            assert match is not None
            name = match.groups()[0].replace("_", " ")
            url = self.tarot_url.format(name.lower().replace(" ", "-"))
            embed = discord.Embed()
            embed.title = name
            embed.url = url
            filename = card.replace("_", "").rpartition("/")[-1]
            embed.set_image(url=f"attachment://{filename}")
            await ctx.send(file=discord.File(f"{card}", filename), embed=embed)

    @commands.command(aliases=["r"])
    async def roll(self, ctx: BContext, *, inp: str = "1d20") -> None:
        """Roll some dice!

        Can roll multiple dice of any size, with modifiers.
        Format: XdY([+-^v]Z)(xN)(s)(t)
        X is the number of dice
        Y is the number of sides
        + adds Z to the result
        - subtracts Z from the result
        ^ drops the Z highest dice
        v drops the Z lowest dice
        x repeats the roll N times
        s sorts the results
        t totals each roll
        You can join rolls with commas
        """
        if inp == "stats":
            inp = "4d6v1x6t"
        inp = "".join(inp.split()).lower()
        expr = r"^([\d]*d?\d+([+\-^v]\d+)?(x\d+)?([ts]{1,2})?,?)+(?<!,)$"
        if re.match(expr, inp) is None:
            raise commands.BadArgument

        rolls = inp.split(",")
        args_batch: List[RollArg] = []
        for roll in rolls:
            if "d" not in roll:
                roll = f"1d{roll}"
            elif roll[0] == "d":
                roll = f"1{roll}"
            args = tuple(int(arg) for arg in re.findall(r"\d+", roll))

            num = args[0]
            sides = args[1]
            if sides == 0:
                raise commands.BadArgument

            hi_drop = 0
            lo_drop = 0
            mod = 0

            if "^" in inp:
                hi_drop = args[2]
            elif "v" in inp:
                lo_drop = args[2]
            elif "+" in inp:
                mod = args[2]
            elif "-" in inp:
                mod = -args[2]

            if "x" in inp:
                times = args[-1]
            else:
                times = 1

            args = (num, sides, lo_drop, hi_drop, mod, times)
            args_batch.append(args)

        future = self.loop.run_in_executor(None, self.roll_helper, *args_batch)
        async with ctx.typing():
            results = await asyncio.wait_for(future, 10, loop=self.loop)

        out = []
        for roll, result in zip(rolls, results):
            if "d" not in roll:
                roll = f"1d{roll}"
            elif roll[0] == "d":
                roll = f"1{roll}"
            total = "t" in roll
            if total:
                result = [[sum(roll_)] for roll_ in result]
            if "s" in inp:
                for roll_ in result:
                    roll_.sort()
                result.sort()
            if total or len(result[0]) == 1:
                result = [roll_[0] for roll_ in result]
            if "x" not in inp:
                result = result[0]
            out.append(f"{roll}: {result}")
        await ctx.reply("\n".join(out))

    def roll_helper(self, *rolls: RollArg) -> List[List[List[int]]]:
        return [roller(*roll) for roll in rolls]

    @roll.error
    async def roll_error(self, ctx: BContext, e: Exception) -> None:
        e = getattr(e, "original", e)
        if isinstance(e, (commands.MissingRequiredArgument, commands.BadArgument)):
            await ctx.send(
                "Invalid input. Valid input examples:"
                "\n1d20+3"
                "\n1d6"
                "\n2d8-4"
                "\n2d20^1"
                "\n4d6v1x6t"
            )
        elif isinstance(e, asyncio.TimeoutError):
            await ctx.reply("Your execution took too long. Roll fewer dice.")
        elif isinstance(e, discord.HTTPException):
            await ctx.reply("Your results were too long. Maybe sum them?")
        else:
            await ctx.bot.handle_error(ctx, e)

    @commands.command(aliases=["shadroll", "sr"])
    async def shadowroll(self, ctx: BContext, *, inp: str) -> None:
        """Roll some dice - for Shadowrun!

        Format: N[e]
        Roll N six-sided dice and return the number of dice that rolled 5 or 6.
        If you put "e" after the number, 6s are counted and then rerolled."""
        inp = inp.strip()
        expr = r"^\d+e?$"
        if not re.match(expr, inp):
            raise commands.BadArgument

        edge = "e" in inp
        num = int(inp.rstrip("e"))

        args = (num, edge)
        future = self.loop.run_in_executor(None, shadowroller, *args)
        async with ctx.typing():
            result = await asyncio.wait_for(future, 10, loop=self.loop)

        await ctx.reply(result)

    @shadowroll.error
    async def shadowroll_error(self, ctx: BContext, e: Exception) -> None:
        e = getattr(e, "original", e)
        if isinstance(e, (commands.MissingRequiredArgument, commands.BadArgument)):
            await ctx.send("Invalid input. Valid input examples:" "\n6" "\n13e")
        elif isinstance(e, futures.TimeoutError):
            await ctx.reply("Your execution took too long. Roll fewer dice.")
        else:
            await ctx.bot.handle_error(ctx, e)

    @commands.command(aliases=["gr"])
    async def genesysroll(self, ctx: BContext, *, inp: str) -> None:
        """Roll some dice - for Fantasy Flight Genesys!

        Available dice:
        b[oost]
        a[bility]
        p[roficiency]
        s[etback]
        d[ifficulty]
        c[hallenge]
        f[orce]

        Input examples:
        4a3d
        3a2p1b4d1c
        2f"""
        inp = inp.lower()
        expr = r"^(?:\d+[a-z])+$"
        match = re.match(expr, inp)
        if not match:
            raise commands.BadArgument
        expr = r"\d+[a-z]"
        matches = re.finditer(expr, inp)
        dice = {}
        for match in matches:
            roll = match.group(0)
            num = int(roll[:-1])
            die_code = roll[-1]
            try:
                die = die_names[die_code]
            except KeyError:
                await ctx.send(f'Die "{die_code}" does not exist.')
                return
            dice[die] = num

        future = self.loop.run_in_executor(None, lambda: genesysroller(**dice))
        async with ctx.typing():
            try:
                result = await asyncio.wait_for(future, 10, loop=self.loop)
            except ValueError:
                await ctx.send("Force dice cannot be used with other dice.")
            else:
                await ctx.reply(str(result))

    @genesysroll.error
    async def genesysroll_error(self, ctx: BContext, e: Exception) -> None:
        e = getattr(e, "original", e)
        if isinstance(e, futures.TimeoutError):
            await ctx.reply("Your execution took too long. Roll fewer dice.")
        else:
            await ctx.bot.handle_error(ctx, e)


def roller(
    num: int = 1,
    sides: int = 20,
    lo_drop: int = 0,
    hi_drop: int = 0,
    mod: int = 0,
    times: int = 1,
) -> List[List[int]]:
    rolls = []
    for _ in range(times):
        pool = [random.randint(1, sides) for _ in range(num)]
        if lo_drop or hi_drop:
            sorted_pool = sorted(pool)
            dropped_vals = sorted_pool[:lo_drop] + sorted_pool[num - hi_drop :]
            for val in dropped_vals:
                pool.remove(val)
        if mod:
            pool = [sum(pool) + mod]
        rolls.append(pool)
    return rolls


def shadowroller(num: int, edge: bool = False) -> str:
    rolls = hits = count1 = 0
    while True:
        count6 = 0
        rolls += num
        for _ in range(num):
            roll = random.randint(1, 6)
            if roll > 4:
                hits += 1
                if roll == 6:
                    count6 += 1
            elif roll == 1:
                count1 += 1
        if not (count6 > 0 and edge):
            break
        num = count6
    s = "s" if hits != 1 else ""
    if count1 < rolls / 2:
        result = f"{hits} hit{s}."
    elif hits == 0:
        result = "Critical glitch."
    else:
        result = f"Glitch with {hits} hit{s}."

    return result


def setup(bot: BeattieBot) -> None:
    bot.add_cog(RPG(bot))
