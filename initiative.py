"""
Docstring
"""
import logging
from collections import OrderedDict

from random import randint
from opsdroid.matchers import match_regex

from .matchers import match_gm, match_active_player
from .characters import get_character
from .picard import load_from_memory, save_new_to_memory, update_memory

@match_regex('roll initiative', case_sensitive=False)
@match_gm
async def create_initiative(opsdroid, config, message):
    """
    Roll initiative for everyone in the list of characters and store a list of those rolls.
    """

    # chars = config['chars'].keys()
    chars = await load_from_memory(opsdroid, message.room, 'chars')
    inits = {} #OrderedDict()
    for charname in chars:
        char = await get_character(charname, opsdroid, config, message)
        # TODO replace this with a character method to allow for custon initiative modifiers
        inits[charname] = randint(1, 20) + char.modifier('Dex')

    inits = OrderedDict(sorted(inits.items(), key=lambda t: t[1], reverse=True))
    await message.respond('\n'.join(
        [f'{charname} rolled {inits[charname]}' for charname in inits])) #init_order)

    await save_new_to_memory(opsdroid, message.room, 'initiatives', inits)
    await update_memory(opsdroid, message.room, 'active_player', {'name': next(iter(inits))})


async def get_initiatives(opsdroid, room):
    inits = await load_from_memory(opsdroid, room, 'initiatives')
    active_player = await load_from_memory(opsdroid, room, 'active_player')
    active_player = active_player['name']
    if inits:
        inits = OrderedDict(sorted(inits.items(), key=lambda t: t[1], reverse=True))
        top = next(iter(inits))
        while top != active_player:
            inits.move_to_end(top)
            top = next(iter(inits))
    return inits


@match_regex("!init order( !usemem (?P<memroom>\w+))?")
async def report_order(opsdroid, config, message):
    room  = message.regex.group('memroom')
    room = room if room else message.room
    inits = await get_initiatives(opsdroid, room)
    if inits:
        await message.respond('\n'.join(
            [f'{charname} ({inits[charname]})' for charname in inits])) #init_order)
    else:
        await message.respond("Looks like there isn't an initiative order yet!")

@match_regex("whose turn", case_sensitive=False)
async def get_active_player(opsdroid, config, message):
    """Retreive the character of the player who's turn it is currently"""

    # char = await opsdroid.memory.get('active_player')
    # char = inits.values()[0]
    inits = await get_initiatives(opsdroid, message.room)
    if inits:
        char = next(iter(inits))
        await message.respond(f"It's {char}'s turn")
    else:
        await message.respond("Looks like there isn't an initiative order yet!")


@match_regex('next player', case_sensitive=False)
@match_active_player
async def next_player(opsdroid, config, message):
    """
    Report the next player in the initiative order so they know it's their turn.
    """

    inits = await get_initiatives(opsdroid, message.room)
    current = next(iter(inits))
    inits.move_to_end(current)
    nextup = next(iter(inits))

    await save_new_to_memory(opsdroid, message.room, 'initiatives', inits)
    await update_memory(opsdroid, message.room, 'active_player', {'name': nextup})

    events = await load_from_memory(opsdroid, message.room, 'events')
    if nextup in events.keys():
        await message.respond(f"{events[nextup]}")
    else:
        await message.respond(f"Next up: {nextup}")


@match_regex(f'!init add (?P<name>\w+) (?P<initval>\d+)( !usemem (?P<memroom>\w+))?',
             case_sensitive=False)
@match_gm
async def add_character(opsdroid, config, message):
    match = message.regex.group
    charname = match('name')#.title()
    initval = int(match('initval'))
    room = match('memroom')
    room = room if room else message.room

    # Get current order from memory and determine current player
    inits = await get_initiatives(opsdroid, room)

    # Add new character to order
    inits[charname] = initval

    await save_new_to_memory(opsdroid, room, 'initiatives', inits)


@match_regex(f'!init event( !usemem (?P<memroom>\w+))? (?P<initval>\d+) (?P<name>\w+) (?P<text>.*)',
             case_sensitive=False)
@match_gm
async def add_event(opsdroid, config, message):
    match = message.regex.group
    event_name = match('name')
    event_text = match('text')
    initval = match('initval')
    room = match('memroom')
    room = room if room else message.room

    # Add event to order
    inits = await get_initiatives(opsdroid, room)
    inits[event_name] = int(initval)

    # Add to events description
    events = await load_from_memory(opsdroid, room, 'events')
    events[event_name] = event_text

    await save_new_to_memory(opsdroid, room, 'initiatives', inits)
    await save_new_to_memory(opsdroid, room, 'events', events)


@match_regex(f'!init remove (?P<name>\w+)( !usemem (?P<memroom>\w+))?', case_sensitive=False)
@match_gm
async def remove_item(opsdroid, config, message):
    match = message.regex.group
    name = match('name')#.title()
    room = match('memroom')
    room = room if room else message.room

    await remove_from_initiative(name, opsdroid, room)


async def remove_from_initiative(name, opsdroid, room):
    inits = await load_from_memory(opsdroid, room, 'initiatives')
    # try:
    inits.pop(name)
    # except KeyError:
    #     for k in inits.keys():
    #         if k.split()[0] == name:
    #             inits.pop(k)
    #             break

    await save_new_to_memory(opsdroid, room, 'initiatives', inits)
