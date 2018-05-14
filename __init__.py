"""
Docstring
"""
import logging

from opsdroid.matchers import match_regex

# from .constants.regex_constants import *
from .combat import attack
from .characters import whoami, howami, get_character, put_character
from .initiative import create_initiative


def setup(opsdroid):
    logging.info("Loaded rpgchar module - ready to play Role-Playing Games!")


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
