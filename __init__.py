"""
Docstring
"""
import logging

from opsdroid.matchers import match_regex

# from .constants.regex_constants import *
from .combat import attack
from .characters import whoami, howami, get_character, put_character
from .initiative import create_initiative
from .picard import intent_self_in_room, get_matrix_connector


def setup(opsdroid):
    logging.info("Loaded rpgchar module - ready to play Role-Playing Games!")


@match_regex("!loadrooms")
async def ensure_rooms_presence(opsdroid, config, message):
    room_id = await intent_self_in_room(opsdroid, config['room'])

    conn = get_matrix_connector(opsdroid)
    if not room_id in conn.room_ids.vales():
        # Determine the name to store the room as in the connector
        roomname = config['name'].replace('-rpgchar', '')

        # Refresh the filter with new room info so the bot can get message from the room
        conn.rooms[roomname] = config['room']
        conn.room_ids[roomname] = room_id
        conn.filter_id = await conn.make_filter(conn.connection, conn.room_ids.values())

        await message.respond(f"Joined room {room_id}", room="main")

@match_regex(f'(you|we) (take|have) a long rest', case_sensitive=False)
async def long_rest(opsdroid, config, message):
    """
    Do all the long rest things.
    At the moment this consists solely of giving everyone their hit points back.
    """

    chars = await opsdroid.memory.get('chars', {})
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
