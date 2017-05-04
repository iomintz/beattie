#!/usr/bin/env python
import asyncio
import logging
import sys

from discord.ext.commands import when_mentioned_or
import yaml

from bot import BeattieBot

try:
    import uvloop
except ImportError:
    pass
else:
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

with open('config/config.yaml') as file:
    config = yaml.load(file)

self_bot = 'self' in sys.argv

if self_bot:
    token = config['self']
    bot = BeattieBot('self>', self_bot=True)
else:
    token = config['token']
    if config['debug']:
        prefixes = [config['test_prefix']]
    else:
        prefixes = config['prefixes']
    bot = BeattieBot(when_mentioned_or(*prefixes))

extensions = ('cat', 'default', 'eddb', 'japanese', 'osu', 'nsfw', 'repl',
              'rpg', 'stats', 'wolfram', 'xkcd')

for extension in extensions:
    try:
        bot.load_extension(extension)
    except Exception as e:
        print(f'Failed to load extension {extension}\n{type(e).__name__}: {e}')

if self_bot:
    logger = logging.getLogger('discord')
    logger.setLevel(logging.DEBUG)
    handler = logging.FileHandler(
        filename='discord.log', encoding='utf-8', mode='w')
    handler.setFormatter(
        logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
    logger.addHandler(handler)
else:
        logger = logging.getLogger('discord')
        logger.setLevel(logging.CRITICAL)
bot.logger = logger


bot.run(token, bot=not self_bot)
