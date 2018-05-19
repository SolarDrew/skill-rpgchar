"""
Docstring
"""
import re
from functools import partial
from random import randint

from opsdroid.matchers import match_regex

from .constants.regex_constants import *
from .characters import get_character, put_character

MELEE_WEAPONS = ['sword', 'dagger']
RANGED_WEAPONS = ['bow', 'crossbow']


async def weapon_attack(attacker, defender, weapon, opsdroid, config, message):
    """
    Mechanical crunchy bits of actually making a weapon attack.
    Die rolls, damage, all that fun stuff
    """
    # Info
    atkr_name = attacker.name.split()[0] if ' ' in attacker.name else attacker.name
    def_name = defender.name.split()[0] if ' ' in defender.name else defender.name
    hitmiss = 'misses'

    # Make attack roll
    base_roll = randint(1, 20)
    if weapon in RANGED_WEAPONS:
        mod = attacker.modifier('Dex')
    else:
        mod = attacker.modifier('Str')
    atk_roll = [base_roll, attacker.proficiency, mod]
    atk_total = sum(atk_roll)
    if atk_total >= defender.AC or base_roll == 20 and base_roll != 1:
        hitmiss = 'hits'
        match = re.match("(?P<ndice>\d+)?(?:d(?P<dice>\d+))", weapon)
        ndice = match.group('ndice')
        ndice = int(ndice) if ndice else 1
        ndice = ndice * 2 if base_roll == 20 else ndice
        dice = int(match.group('dice'))

        rolls = list(map(partial(randint, 1), [dice]*ndice)) + [mod]
        total_damage = sum(rolls)

        await defender.take_damage(total_damage, opsdroid, config, message)
    else:
        total_damage = 0
    critmod = ' critically ' if base_roll in [1, 20] else ' '

    # Report basic result of the attack
    report = [f"{atkr_name}{critmod}{hitmiss} {def_name}! "]
    # Add the roll, modifiers and total
    report[0] += f"({' + '.join(str(n) for n in atk_roll)} = {sum(atk_roll)}) !"
    # Add damage roll, modifiers and total, if any
    if total_damage > 0:
        report.append(f"{def_name.title()} takes {total_damage} damage ")
        report[1] += f"({' + '.join(str(r) for r in rolls)}) !"

    return report, defender


@match_regex(f'{OBJECT} {ATK_VERB} {SUBJECT} with {POSSESSIVE} {WEAPON}', case_sensitive=False)
async def attack(opsdroid, config, message):
    """
    Detect when a character is attacking another character.
    Just handles the overall flow of the interaction, rolls are dealt with elsewhere.
    """
    match = message.regex.group

    # Get characters
    atkr_name = match('object')
    if atkr_name.upper() == 'I':
        atkr_name = message.user
    attacker = await get_character(atkr_name, opsdroid, config, message)
    def_name = match('subject')
    defender = await get_character(def_name, opsdroid, config, message)
    weapon = attacker.weapons[match('weapon')]

    atk_report, defender = await weapon_attack(attacker, defender, weapon, opsdroid, config, message)

    await put_character(defender, opsdroid)
    for msg in atk_report:
        await message.respond(msg)
