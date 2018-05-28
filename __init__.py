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
from .scenes import load_scene, get_info


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


@match_regex("!help", case_sensitive=False)
async def user_help(opsdroid, config, message):
    await message.respond(f"""Greetings, adventurers!

I'm the DMBot and I'm here to make {config['game_master']}'s life a little easier. I can automate weapon attacks, skill and ability checks, and initiative tracking. Here are some of the ways you can interact with me.

  - To find out your name, race and class: "who am I?"
  - To check your current hit point total: "how am I?"
  - To make a weapon attack: "I attack <target's name> with my <weapon>"
  - To make an ability check: "I make a <str/dex/con/int/wis/cha> check"
  - To make a skill check: "I make a <name of skill> check

For all these things to work you need to set your display name to your character's name. If you're using Riot, you can change it by typing "/devtools" and going to "Explore Room State" -> "m.room.member" -> "<your username>" -> "Edit", then changing the "displayname" entry to the name of your character.""")
