import time

from discord.ext import commands
import yaml

from utils import checks


class Default:
    def __init__(self, bot):
        self.bot = bot
        try:
            with open('cog_blacklist.yaml') as file:
                self.bot.cog_blacklist = yaml.load(file)
        except FileNotFoundError:
            self.bot.cog_blacklist = {}
        else:
            if self.bot.cog_blacklist is None:
                self.bot.cog_blacklist = {}

    def __global_check(self, ctx):
        if checks.is_owner_check(ctx):
            return True
        cog = ctx.command.cog_name
        return cog not in self.bot.cog_blacklist.get(ctx.guild.id, set())

    def _update_blacklist(self):
        with open('cog_blacklist.yaml', 'w') as file:
            yaml.dump(self.bot.cog_blacklist, file)

    @commands.command(hidden=True)
    @checks.is_owner()
    async def reload(self, ctx, *, cog):
        self.unload_extension(cog)
        self.load_extension(cog)
        await ctx.send('Reload successful.')

    @commands.command()
    @checks.is_owner()
    async def enable(self, ctx, cog):
        """Enable a cog in the guild."""
        if self.bot.get_cog(cog) is None:
            await ctx.send("That cog doesn't exist.")
        else:
            blacklist = self.bot.cog_blacklist.get(ctx.guild.id, set())
            try:
                blacklist.remove(cog)
            except KeyError:
                await ctx.send('Cog is already enabled.')
            else:
                self.bot.cog_blacklist[ctx.guild.id] = blacklist
                await ctx.send('Cog enabled for this guild.')
                self._update_blacklist()

    @commands.command()
    @checks.is_owner()
    async def disable(self, ctx, cog):
        """Disable a cog in the guild."""
        if self.bot.get_cog(cog) is None:
            try:
                self.bot.load_extension(cog)
            except ModuleNotFoundError:
                pass
        if self.bot.get_cog(cog) is None:
            await ctx.send("That cog doesn't exist.")
        else:
            blacklist = self.bot.cog_blacklist.get(ctx.guild.id, set())
            blacklist.add(cog)
            self.bot.cog_blacklist[ctx.guild.id] = blacklist
            await ctx.send('Cog disabled for this guild.')
            self._update_blacklist()

    @commands.command(aliases=['p'])
    async def ping(self, ctx):
        """Ping command, taken from somewhere idk"""
        msg = await ctx.send("Pong! :ping_pong:")

        before = time.monotonic()
        await (await self.bot.ws.ping())
        after = time.monotonic()
        ping_time = (after - before) * 1000

        await msg.edit(content=f'{msg.content} **{ping_time:.0f}ms**')


def setup(bot):
    bot.add_cog(Default(bot))
