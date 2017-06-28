import discord
from discord.ext import commands


class Manage:
    def __init__(self, bot):
        self.config = bot.config

    async def __global_check(self, ctx):
        if await ctx.bot.is_owner(ctx.author) or ctx.guild is None:
            return True
        cog = ctx.command.cog_name
        guild_conf = await self.config.get(ctx.guild.id)
        blacklist = guild_conf.get('cog_blacklist', '')
        return blacklist is not None and f'{cog},' not in blacklist

    async def __global_check_once(self, ctx):
        member_conf = await self.config.get_member(ctx.guild.id, ctx.author.id)
        plonked = member_conf.get('plonked', False)
        return not plonked

    async def __local_check(self, ctx):
        return (await ctx.bot.is_owner(ctx.author)
                or ctx.author.permissions_in(ctx.channel).manage_guild)

    @commands.command()
    @commands.is_owner()
    async def reload(self, ctx, *, cog):
        cog = f'cogs.{cog.lower()}'
        try:
            ctx.bot.unload_extension(cog)
            ctx.bot.load_extension(cog)
        except ModuleNotFoundError:
            await ctx.send('Cog does not exist.')
        else:
            await ctx.send('Reload successful.')

    @commands.command()
    async def enable(self, ctx, cog):
        """Enable a cog in the guild."""
        if ctx.bot.get_cog(cog) is None:
            await ctx.send("That cog doesn't exist.")
            return
        guild_conf = await self.config.get(ctx.guild.id)
        blacklist = guild_conf.get('cog_blacklist', '')
        if f'{cog},' not in blacklist:
            await ctx.send('Cog is already enabled.')
            return
        blacklist = blacklist.replace(f'{cog},', '')
        await self.config.set(ctx.guild.id, cog_blacklist=blacklist)
        await ctx.send('Cog enabled for this guild.')

    @commands.command()
    async def disable(self, ctx, cog):
        """Disable a cog in the guild."""
        if ctx.bot.get_cog(cog) is None:
            await ctx.send("That cog doesn't exist.")
            return
        guild_conf = await self.config.get(ctx.guild.id)
        blacklist = guild_conf.get('cog_blacklist', '')
        if f'{cog},' in blacklist:
            await ctx.send('Cog is already disabled.')
            return
        blacklist += f'{cog},'
        await self.config.set(ctx.guild.id, cog_blacklist=blacklist)
        await ctx.send('Cog disabled for this guild.')

    @commands.command()
    async def prefix(self, ctx, prefix=''):
        """Set a custom prefix for this guild. Pass no prefix to reset."""
        await self.config.set(ctx.guild.id, prefix=prefix)
        await ctx.send('Guild prefix set.')

    @commands.command()
    async def greet(self, ctx, *, message=None):
        """Set the member greeting for this guild. Disables if no message.

        Include a {} in the message where you want to mention the newcomer"""
        message = message.replace('{}', '{member.mention}')
        await self.config.set(ctx.guild.id, welcome=message)
        await ctx.send('Welcome message set.')

    @commands.command()
    async def leave(self, ctx, *, message=None):
        """Set the member-left message for this guild. Disables if no message.

        Include a {} in the message where you want to mention the deserter"""
        await self.config.set(ctx.guild.id, farewell=message)
        await ctx.send('Leave message set.')

    @commands.command()
    async def plonk(self, ctx, member: discord.Member):
        """Disallow a member from using commands on this server."""
        await self.config.update_member(ctx.guild.id, member.id, plonked=True)
        await ctx.send('Member plonked.')

    @commands.command()
    async def unplonk(self, ctx, member: discord.Member):
        """Allow a member to use commands on this server."""
        await self.config.update_member(ctx.guild.id, member.id, plonked=False)
        await ctx.send('Member unplonked.')


def setup(bot):
    bot.add_cog(Manage(bot))