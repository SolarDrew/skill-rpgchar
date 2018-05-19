"""
Docstring
"""
from collections import OrderedDict

from random import randint
from opsdroid.matchers import match_regex

from .characters import get_character

@match_regex('roll initiative', case_sensitive=False)
async def create_initiative(opsdroid, config, message):
    """
    Roll initiative for everyone in the list of characters and store a list of those rolls.
    """

    chars = config['chars'].keys()
    inits = {} #OrderedDict()
    for charname in chars:
        if charname.lower() == '_id':
            continue
        char = await get_character(charname, opsdroid, config, message)
        inits[charname] = randint(1, 20) + char.modifier('Dex')

    inits = OrderedDict(sorted(inits.items(), key=lambda t: t[1], reverse=True))
    # init_order = '\n'.join(
    #     [f'{char} rolled {inits[char]}' for char in inits]) #sorted(inits, key=inits.get, reverse=True)])
    await message.respond('\n'.join(
        [f'{charname} rolled {inits[charname]}' for charname in inits])) #init_order)

    await opsdroid.memory.put('initiatives', inits)
    # await set_active_player()


# async def set_active_player(char):
#     """Sets the current active player by storing that character in memory"""

#     await opsdroid.memory.put('active_player', char)


async def get_initiatives(opsdroid):
    inits = await opsdroid.memory.get('initiatives')
    if inits:
        try:
            inits.pop('_id')
        except KeyError:
            pass
        # inits = OrderedDict(sorted(inits.items(), key=lambda t: t[1], reverse=True))
        inits = OrderedDict(inits)

    return inits


@match_regex("!init order")
async def report_order(opsdroid, config, message):
    inits = await get_initiatives(opsdroid)
    await message.respond('\n'.join(
        [f'{charname} ({inits[charname]})' for charname in inits])) #init_order)


@match_regex("whose turn", case_sensitive=False)
async def get_active_player(opsdroid, config, message):
    """Retreive the character of the player who's turn it is currently"""

    # char = await opsdroid.memory.get('active_player')
    # char = inits.values()[0]
    inits = await get_initiatives(opsdroid)
    if inits:
        char = next(iter(inits))
        await message.respond(f"It's {char}'s turn")
    else:
        await message.respond("Looks like there isn't an initiative order yet!")


@match_regex('next player', case_sensitive=False)
async def next_player(opsdroid, config, message):
    """
    Report the next player in the initiative order so they know it's their turn.
    """

    inits = await get_initiatives(opsdroid)
    current = next(iter(inits))
    inits.move_to_end(current)
    nextup = next(iter(inits))

    await opsdroid.memory.put('initiatives', inits)

    await message.respond(f"Next up: {nextup}")


@match_regex(f'!init add (?P<name>\w+) (?P<initval>\d+)', case_sensitive=False)
async def add_character(opsdroid, config, message):
    match = message.regex.group
    charname = match('name').title()
    initval = int(match('initval'))
    # Get current order from memory and determine current player
    inits = await get_initiatives(opsdroid)
    active_char = next(iter(inits))

    # Add new character to order
    newchar = await get_character(charname, opsdroid, config, message)
    inits[newchar.name] = initval

    # Resort to ensure correct relative ordering
    inits = OrderedDict(sorted(inits.items(), key=lambda t: t[1], reverse=True))

    # Re-rotate the order to bring the active player back to the top
    top = next(iter(inits))
    while top != active_char:
        inits.move_to_end(top)
        top = next(iter(inits))
    await opsdroid.memory.put('initiatives', inits)


@match_regex(f'!init event (?P<initval>\d+) (?P<text>.*)', case_sensitive=False)
async def add_event(opsdroid, config, message):
    match = message.regex.group
    event_text = match('text')
    initval = match('initval')

    # Get current order from memory and determine current player
    inits = await get_initiatives(opsdroid)
    active_char = next(iter(inits))

    # Add event to order
    inits[event_text] = initval

    # Resort to ensure correct relative ordering
    inits = OrderedDict(sorted(inits.items(), key=lambda t: t[1], reverse=True))

    # Re-rotate the order to bring the active player back to the top
    top = next(iter(inits))
    while top != active_char:
        inits.move_to_end(top)
        top = next(iter(inits))
    await opsdroid.memory.put('initiatives', inits)


@match_regex(f'!init remove (?P<name>\w+)', case_sensitive=False)
async def remove_item(opsdroid, config, message):
    match = message.regex.group
    name = match('name').title()

    await remove_from_initiative(name, opsdroid)


async def remove_from_initiative(name, opsdroid):
    inits = await get_initiatives(opsdroid)
    try:
        inits.pop(name)
    except KeyError:
        for k in inits.keys():
            if k.split()[0] == name:
                inits.pop(k)

    await opsdroid.memory.put('initiatives', inits)
