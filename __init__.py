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


@match_regex("!loadrooms")
async def ensure_rooms_presence(opsdroid, config, message):
    logging.debug(config)
    room_id = await intent_self_in_room(opsdroid, config['room'])
    logging.debug(room_id)

    conn = get_matrix_connector(opsdroid)
    # if not room_id in conn.room_ids.values():
    # Determine the name to store the room as in the connector
    roomname = config['name'].replace('-rpgchar', '')
    logging.debug(f'{config["name"]}, {roomname}')

    # Refresh the filter with new room info so the bot can get message from the room
    # roomname = 'dungeon-chat'
    conn.rooms[roomname] = config['room']
    logging.debug(conn.rooms)
    conn.room_ids[roomname] = room_id
    logging.debug(conn.room_ids)
    conn.filter_id = await conn.make_filter(conn.connection, conn.room_ids.values())

    await message.respond(f"Joined room {room_id}", room="main")

@match_regex(f'(you|we) (take|have) a long rest', case_sensitive=False)
async def long_rest(opsdroid, config, message):
    """
    Do all the long rest things.
    At the moment this consists solely of giving everyone their hit points back.
    """

    # with memory_in_room(message.room, opsdroid):
    #     chars = await opsdroid.memory.get('chars', {})
    chars = load_from_memory(opsdroid, message.room, 'chars')
    for charname in chars.keys():
        # if charname.lower() == '_id':
        #     continue
        # char = await get_character(charname, opsdroid, config, message)
        # char = Character(**chars[charname])
        chars[charname]['current_hp'] = char[charname]['max_hp']
        # await put_character(char, opsdroid, message.room)
        await update_memory(opsdroid, message.room, 'chars', chars)


@match_regex('tell the dm', case_sensitive=False)
async def tell_dm(opsdroid, config, message):
    """
    Relay a message to the private chat with the DM.
    Entirely for testing purposes at this point.
    """

    text = message.text.lower().replace('tell the dm', f'{message.user} says:')

    await message.respond(text, room='DM-private')
