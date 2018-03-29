"""
Docstring
"""
import logging
import re
from functools import partial

from numpy.random import randint
import yaml
from opsdroid.matchers import match_regex

from .constants.regex_constants import *
from .combat import attack
from .characters import whoami, howami, get_character, put_character


def setup(opsdroid):
    logging.debug("Loaded rpgchar module - ready to play Role-Playing Games!")


@match_regex(f'(you|we) (take|have) a long rest', case_sensitive=False)
async def long_rest(opsdroid, config, message):
    """
    Do all the long rest things.
    At the moment this consists solely of giving everyone their hit points back.
    """

    chars = await opsdroid.memory.get('chars')
    for charname in chars.keys():
        if charname.lower() == '_id':
            continue
        char = await get_character(charname, opsdroid, config, message)
        char.current_hp = char.max_hp
        await put_character(char, opsdroid)


@match_regex('tell the dm', case_sensitive=False)
async def tell_dm(opsdroid, config, message):
    """
    Relay a message to the private chat with the DM.
    Entirely for testing purposes at this point.
    """

    text = message.text.lower().replace('tell the dm', f'{message.user} says:')

    await message.respond(text, room='DM-private')


@match_regex('roll initiative', case_sensitive=False)
async def create_initiative(opsdroid, config, message):
    """
    Roll initiative for everyone in the list of characters and store a list of those rolls.
    """

    chars = config['chars'].keys()
    inits = {}
    for charname in chars:
        if charname.lower() == '_id':
            continue
        char = await get_character(charname, opsdroid, config, message)
        inits[charname] = randint(1, 21) + char.modifier('Dex')

    for char in sorted(inits, key=inits.get, reverse=True):
        # for char, result in inits.items():
        await message.respond(f'{char} rolled {inits[char]}')

    await opsdroid.memory.put('inititives', inits)
