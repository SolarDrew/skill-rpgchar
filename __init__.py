"""
Docstring
"""
import logging

from opsdroid.matchers import match_regex

# from .constants.regex_constants import *
from .combat import attack
from .characters import whoami, howami, Character #get_character, put_character
from .initiative import create_initiative
from .picard import intent_self_in_room, get_matrix_connector, load_from_memory, update_memory


def setup(opsdroid):
    logging.info("Loaded rpgchar module - ready to play Role-Playing Games!")


@match_regex(f'(you|we) (take|have) a long rest', case_sensitive=False)
async def long_rest(opsdroid, config, message):
    """
    Do all the long rest things.
    At the moment this consists solely of giving everyone their hit points back.
    """

    # with memory_in_room(message.room, opsdroid):
    #     chars = await opsdroid.memory.get('chars', {})
    chars = await load_from_memory(opsdroid, message.room, 'chars')
    for charname in chars.keys():
        # if charname.lower() == '_id':
        #     continue
        # char = await get_character(charname, opsdroid, config, message)
        # char = Character(**chars[charname])
        chars[charname]['current_hp'] = chars[charname]['max_hp']
        # await put_character(char, opsdroid, message.room)
    await update_memory(opsdroid, message.room, 'chars', chars)
    await messge.respond("Everyone is restored to full health.")


@match_regex('!toroom (?P<roomname>\w+) (?P<msg>.*)', case_sensitive=False)
async def to_room(opsdroid, config, message):
    """
    Relay a message to a specified room, as named in the config.
    """
    match = message.regex.group

    await message.respond(match('msg'), room=match('roomname'))
